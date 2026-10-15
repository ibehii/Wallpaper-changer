import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import GObject from 'gi://GObject';
import St from 'gi://St';
import Clutter from 'gi://Clutter';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import { Extension, gettext as _ } from 'resource:///org/gnome/shell/extensions/extension.js';

const GNOME_BG_SCHEMA = 'org.gnome.desktop.background';
const MAX_HISTORY_ITEMS = 50;

/**
 * Execute an arbitrary command asynchronously with Gio.Subprocess
 */
function runCommandAsync(argv, onFinished = null) {
    try {
        const proc = new Gio.Subprocess({
            argv: argv,
            flags: Gio.SubprocessFlags.STDOUT_SILENCE | Gio.SubprocessFlags.STDERR_SILENCE,
        });
        proc.init(null);
        proc.wait_async(null, (procObj, res) => {
            try {
                procObj.wait_finish(res);
                if (onFinished) {
                    onFinished(procObj.get_successful());
                }
            } catch (err) {
                if (onFinished) {
                    onFinished(false);
                }
            }
        });
    } catch (e) {
        logError(e, `[wchanger-extension] Failed to launch subprocess: ${argv.join(' ')}`);
        if (onFinished) {
            onFinished(false);
        }
    }
}

/**
 * History & Favorite Store Manager
 * Persists history in ~/.cache/wchanger/history.json
 */
class HistoryManager {
    constructor() {
        this._cacheDir = `${GLib.get_user_cache_dir()}/wchanger`;
        this._historyFile = `${this._cacheDir}/history.json`;
        this._history = [];
        this._currentIndex = -1;
        this._ensureCacheDir();
        this._loadHistory();
    }

    _ensureCacheDir() {
        const dir = Gio.File.new_for_path(this._cacheDir);
        if (!dir.query_exists(null)) {
            try {
                dir.make_directory_with_parents(null);
            } catch (e) {
                // Ignore if already created
            }
        }
    }

    _loadHistory() {
        const file = Gio.File.new_for_path(this._historyFile);
        if (file.query_exists(null)) {
            try {
                const [ok, contents] = file.load_contents(null);
                if (ok) {
                    const data = JSON.parse(new TextDecoder().decode(contents));
                    if (Array.isArray(data.items)) {
                        this._history = data.items;
                        this._currentIndex = typeof data.currentIndex === 'number'
                            ? data.currentIndex
                            : this._history.length - 1;
                        return;
                    }
                }
            } catch (e) {
                // If corrupted, initialize fresh
            }
        }
        this._history = [];
        this._currentIndex = -1;
    }

    _saveHistory() {
        this._ensureCacheDir();
        try {
            const data = {
                items: this._history.slice(-MAX_HISTORY_ITEMS),
                currentIndex: this._currentIndex,
            };
            const file = Gio.File.new_for_path(this._historyFile);
            file.replace_contents(
                JSON.stringify(data, null, 2),
                null,
                false,
                Gio.FileCreateFlags.REPLACE_DESTINATION,
                null
            );
        } catch (e) {
            logError(e, '[wchanger-extension] Failed to write history.json');
        }
    }

    recordWallpaper(filePath) {
        if (!filePath) return;

        // If current position already matches the wallpaper, do nothing (prevents circular navigation bug)
        if (this._currentIndex >= 0 && this._currentIndex < this._history.length && this._history[this._currentIndex] === filePath) {
            return;
        }

        // Avoid duplicate consecutive entries
        if (this._history.length > 0 && this._history[this._history.length - 1] === filePath) {
            this._currentIndex = this._history.length - 1;
            this._saveHistory();
            return;
        }

        // If we backed up and now add a new wallpaper, append forward
        this._history.push(filePath);
        if (this._history.length > MAX_HISTORY_ITEMS) {
            this._history.shift();
        }
        this._currentIndex = this._history.length - 1;
        this._saveHistory();
    }

    canGoBack() {
        return this._currentIndex > 0;
    }

    canGoForward() {
        return this._currentIndex < this._history.length - 1;
    }

    getPrevious() {
        if (this.canGoBack()) {
            this._currentIndex--;
            this._saveHistory();
            return this._history[this._currentIndex];
        }
        return null;
    }

    getNext() {
        if (this.canGoForward()) {
            this._currentIndex++;
            this._saveHistory();
            return this._history[this._currentIndex];
        }
        return null;
    }

    getCurrent() {
        if (this._currentIndex >= 0 && this._currentIndex < this._history.length) {
            return this._history[this._currentIndex];
        }
        return null;
    }
}

/**
 * Panel Menu Indicator Component
 */
const WchangerIndicator = GObject.registerClass(
class WchangerIndicator extends PanelMenu.Button {
    _init(extension) {
        super._init(0.0, 'Anahita Wallpaper Changer');
        this._extension = extension;
        this._settings = extension.getSettings('org.gnome.shell.extensions.wchanger');
        this._bgSettings = new Gio.Settings({ schema_id: GNOME_BG_SCHEMA });
        this._historyManager = new HistoryManager();

        // Icon in top bar
        this._icon = new St.Icon({
            icon_name: 'preferences-desktop-wallpaper-symbolic',
            style_class: 'system-status-icon wchanger-indicator-icon',
        });
        this.add_child(this._icon);

        this._buildMenu();
        this._syncCurrentBackground();

        // Listen for external wallpaper changes to keep history in sync (both light and dark modes)
        this._bgChangedId = this._bgSettings.connect('changed::picture-uri', () => {
            this._syncCurrentBackground();
        });
        this._bgDarkChangedId = this._bgSettings.connect('changed::picture-uri-dark', () => {
            this._syncCurrentBackground();
        });
    }

    destroy() {
        if (this._bgChangedId) {
            this._bgSettings.disconnect(this._bgChangedId);
            this._bgChangedId = null;
        }
        if (this._bgDarkChangedId) {
            this._bgSettings.disconnect(this._bgDarkChangedId);
            this._bgDarkChangedId = null;
        }
        super.destroy();
    }

    _syncCurrentBackground() {
        let uri = this._bgSettings.get_string('picture-uri');
        if (!uri) {
            uri = this._bgSettings.get_string('picture-uri-dark');
        }
        if (uri) {
            let path = uri.startsWith('file://') ? decodeURIComponent(uri.replace('file://', '')) : uri;
            this._historyManager.recordWallpaper(path);
        }
        this._updateNavButtons();
    }

    _applyWallpaper(filePath) {
        if (!filePath) return;
        const file = Gio.File.new_for_path(filePath);
        if (!file.query_exists(null)) {
            Main.notify('Anahita Wallpaper Changer', _('Wallpaper file not found: ') + filePath);
            return;
        }
        const fileUri = file.get_uri();
        this._bgSettings.set_string('picture-uri', fileUri);
        this._bgSettings.set_string('picture-uri-dark', fileUri);
        this._updateNavButtons();
    }

    _buildMenu() {
        // Section 1: Navigation Controls (Previous, Next, Favorite)
        this._navBox = new St.BoxLayout({
            style_class: 'wchanger-nav-box',
            x_align: Clutter.ActorAlign.CENTER,
            y_align: Clutter.ActorAlign.CENTER,
        });

        // 1. Previous (Back)
        this._prevItem = new PopupMenu.PopupMenuItem('⏮  Previous');
        this._prevItem.connect('activate', () => {
            const prevWallpaper = this._historyManager.getPrevious();
            if (prevWallpaper) {
                this._applyWallpaper(prevWallpaper);
            }
        });
        this.menu.addMenuItem(this._prevItem);

        // 2. Next (Forward / Rotate)
        this._nextItem = new PopupMenu.PopupMenuItem('⏭  Next Wallpaper');
        this._nextItem.connect('activate', () => {
            if (this._historyManager.canGoForward()) {
                const nextWallpaper = this._historyManager.getNext();
                this._applyWallpaper(nextWallpaper);
            } else {
                this._triggerWchangerRotation();
            }
        });
        this.menu.addMenuItem(this._nextItem);

        // 3. Favorite Button
        this._favItem = new PopupMenu.PopupMenuItem('⭐  Add to Favorites');
        this._favItem.connect('activate', () => {
            this._favoriteCurrentWallpaper();
        });
        this.menu.addMenuItem(this._favItem);

        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        // Section 2: Online Sources Submenu
        const sourcesSubMenu = new PopupMenu.PopupSubMenuMenuItem('🌐  Online Providers');
        const providers = [
            { label: 'Bing Daily Photo', key: 'bing' },
            { label: 'Wallhaven Toplist', key: 'wallhaven' },
            { label: 'Lorem Picsum (Random)', key: 'picsum' },
            { label: 'LoremFlickr (Nature)', key: 'loremflickr' },
        ];
        providers.forEach(p => {
            const item = new PopupMenu.PopupMenuItem(p.label);
            item.connect('activate', () => {
                const multiMon = this._settings.get_boolean('enable-multi-monitor');
                const argv = ['wchanger', '--online', p.key, '--no-repetition'];
                if (multiMon) argv.push('-m');
                this._runWchangerCommand(argv);
            });
            sourcesSubMenu.menu.addMenuItem(item);
        });
        this.menu.addMenuItem(sourcesSubMenu);

        // Section 3: Multi-Monitor Quick Action
        const multiMonItem = new PopupMenu.PopupMenuItem('🖥️  Rotate Multi-Monitor');
        multiMonItem.connect('activate', () => {
            this._runWchangerCommand(['wchanger', '-m', '--no-repetition']);
        });
        this.menu.addMenuItem(multiMonItem);

        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        // Section 4: Systemd Background Service Switch
        this._serviceSwitch = new PopupMenu.PopupSwitchMenuItem('🔄  Background Rotator', false);
        this._checkServiceState();
        this._serviceSwitch.connect('toggled', (item, state) => {
            const action = state ? 'start' : 'stop';
            runCommandAsync(['systemctl', '--user', action, 'wallpaper-changer.service'], (success) => {
                if (!success) {
                    this._checkServiceState();
                }
            });
        });
        this.menu.addMenuItem(this._serviceSwitch);

        // Section 5: Folder & Settings shortcuts
        const openFavsItem = new PopupMenu.PopupMenuItem('📂  Open Favorites Folder');
        openFavsItem.connect('activate', () => {
            const favDir = this._getFavoritesDirectory();
            runCommandAsync(['xdg-open', favDir]);
        });
        this.menu.addMenuItem(openFavsItem);

        const prefsItem = new PopupMenu.PopupMenuItem('⚙️  Extension Settings...');
        prefsItem.connect('activate', () => {
            this._extension.openPreferences();
        });
        this.menu.addMenuItem(prefsItem);

        this.menu.connect('open-state-changed', (menu, isOpen) => {
            if (isOpen) {
                this._checkServiceState();
                this._updateNavButtons();
            }
        });
    }

    _updateNavButtons() {
        if (this._prevItem) {
            this._prevItem.setSensitive(this._historyManager.canGoBack());
        }
    }

    _triggerWchangerRotation() {
        const multiMon = this._settings.get_boolean('enable-multi-monitor');
        const argv = ['wchanger', '--no-repetition'];
        if (multiMon) {
            argv.push('-m');
        }
        this._runWchangerCommand(argv);
    }

    _runWchangerCommand(argv) {
        runCommandAsync(argv, (success) => {
            if (success) {
                this._syncCurrentBackground();
            }
        });
    }

    _getFavoritesDirectory() {
        let customPath = this._settings.get_string('favorites-directory');
        if (!customPath || customPath.trim().length === 0) {
            const pics = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_PICTURES) || `${GLib.get_home_dir()}/Pictures`;
            customPath = `${pics}/Wallpapers/Favorites`;
        }
        const dir = Gio.File.new_for_path(customPath);
        if (!dir.query_exists(null)) {
            try {
                dir.make_directory_with_parents(null);
            } catch (e) {
                // Ignore
            }
        }
        return customPath;
    }

    _favoriteCurrentWallpaper() {
        const currentPath = this._historyManager.getCurrent();
        if (!currentPath) {
            Main.notify('Anahita Wallpaper Changer', _('No active wallpaper found to favorite.'));
            return;
        }

        const sourceFile = Gio.File.new_for_path(currentPath);
        if (!sourceFile.query_exists(null)) {
            Main.notify('Anahita Wallpaper Changer', _('Active wallpaper file not accessible.'));
            return;
        }

        const favDir = this._getFavoritesDirectory();
        const baseName = sourceFile.get_basename();
        const destFile = Gio.File.new_for_path(`${favDir}/${baseName}`);

        sourceFile.copy_async(
            destFile,
            Gio.FileCopyFlags.OVERWRITE,
            GLib.PRIORITY_DEFAULT,
            null,
            null,
            (file, res) => {
                try {
                    file.copy_finish(res);
                    Main.notify(
                        '⭐ Anahita Wallpaper Changer',
                        `${_('Saved to Favorites:')} ${baseName}`
                    );
                } catch (e) {
                    logError(e, '[wchanger-extension] Failed to copy wallpaper to favorites');
                    Main.notify('Anahita Wallpaper Changer', _('Failed to save to favorites.'));
                }
            }
        );
    }

    _checkServiceState() {
        if (!GLib.find_program_in_path('systemctl')) {
            this._serviceSwitch.setToggleState(false);
            return;
        }

        try {
            Gio.DBus.session.call(
                'org.freedesktop.systemd1',
                '/org/freedesktop/systemd1',
                'org.freedesktop.systemd1.Manager',
                'ListUnitsByNames',
                new GLib.Variant('(as)', [['wallpaper-changer.service']]),
                new GLib.VariantType('(a(ssssssouso))'),
                Gio.DBusCallFlags.NONE,
                -1,
                null,
                (connection, res) => {
                    try {
                        const reply = connection.call_finish(res);
                        const [units] = reply.deepUnpack();
                        if (units && units.length > 0) {
                            const activeState = units[0][3];
                            this._serviceSwitch.setToggleState(activeState === 'active');
                        } else {
                            this._serviceSwitch.setToggleState(false);
                        }
                    } catch (e) {
                        this._serviceSwitch.setToggleState(false);
                    }
                }
            );
        } catch (e) {
            this._serviceSwitch.setToggleState(false);
        }
    }
});

export default class WchangerExtension extends Extension {
    enable() {
        this._settings = this.getSettings('org.gnome.shell.extensions.wchanger');
        this._indicator = null;

        // Respect show-indicator setting
        this._showIndicatorChangedId = this._settings.connect('changed::show-indicator', () => {
            this._updateIndicatorVisibility();
        });

        this._updateIndicatorVisibility();
    }

    _updateIndicatorVisibility() {
        const show = this._settings.get_boolean('show-indicator');
        if (show && !this._indicator) {
            this._indicator = new WchangerIndicator(this);
            Main.panel.addToStatusArea(this.uuid, this._indicator);
        } else if (!show && this._indicator) {
            this._indicator.destroy();
            this._indicator = null;
        }
    }

    disable() {
        if (this._showIndicatorChangedId) {
            this._settings.disconnect(this._showIndicatorChangedId);
            this._showIndicatorChangedId = null;
        }
        if (this._indicator) {
            this._indicator.destroy();
            this._indicator = null;
        }
        this._settings = null;
    }
}
