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
 * Resolves the executable path/argv for wchanger across PATH, ~/.local/bin, /usr/local/bin, etc.
 */
function getWchangerCommand(customPath = '') {
    if (customPath && customPath.trim().length > 0) {
        return [customPath.trim()];
    }

    if (GLib.find_program_in_path('wchanger')) {
        return ['wchanger'];
    }

    const home = GLib.get_home_dir();
    const candidatePaths = [
        `${home}/.local/bin/wchanger`,
        '/usr/local/bin/wchanger',
        '/usr/bin/wchanger',
        '/bin/wchanger',
    ];

    for (const p of candidatePaths) {
        if (GLib.file_test(p, GLib.FileTest.IS_EXECUTABLE)) {
            return [p];
        }
    }

    // Fallback: check if dev repository script exists
    const repoCandidate = `${home}/Dev/Wallpaper-changer/wchanger.py`;
    if (GLib.file_test(repoCandidate, GLib.FileTest.EXISTS)) {
        const pythonBin = GLib.find_program_in_path('python3') || 'python3';
        return [pythonBin, repoCandidate];
    }

    return null;
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

        // Automatic Background Rotator timer state
        this._rotatorTimerId = null;
        this._initRotator();

        // Listen for settings changes
        this._intervalChangedId = this._settings.connect('changed::rotation-interval', () => {
            if (this._settings.get_boolean('rotator-enabled')) {
                this._startRotatorTimer();
            }
        });

        this._rotatorEnabledChangedId = this._settings.connect('changed::rotator-enabled', () => {
            const enabled = this._settings.get_boolean('rotator-enabled');
            if (this._serviceSwitch && this._serviceSwitch.state !== enabled) {
                this._serviceSwitch.setToggleState(enabled);
            }
            if (enabled) {
                this._startRotatorTimer();
            } else {
                this._stopRotatorTimer();
            }
        });

        // Listen for external wallpaper changes to keep history in sync (both light and dark modes)
        this._bgChangedId = this._bgSettings.connect('changed::picture-uri', () => {
            this._syncCurrentBackground();
        });
        this._bgDarkChangedId = this._bgSettings.connect('changed::picture-uri-dark', () => {
            this._syncCurrentBackground();
        });
    }

    destroy() {
        if (this._rotatorTimerId) {
            GLib.Source.remove(this._rotatorTimerId);
            this._rotatorTimerId = null;
        }
        if (this._intervalChangedId) {
            this._settings.disconnect(this._intervalChangedId);
            this._intervalChangedId = null;
        }
        if (this._rotatorEnabledChangedId) {
            this._settings.disconnect(this._rotatorEnabledChangedId);
            this._rotatorEnabledChangedId = null;
        }
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
        this._prevItem = new PopupMenu.PopupImageMenuItem(_('Previous'), 'media-skip-backward-symbolic');
        this._prevItem.connect('activate', () => {
            const prevWallpaper = this._historyManager.getPrevious();
            if (prevWallpaper) {
                this._applyWallpaper(prevWallpaper);
            }
        });
        this.menu.addMenuItem(this._prevItem);

        this._nextItem = new PopupMenu.PopupImageMenuItem(_('Next Wallpaper'), 'media-skip-forward-symbolic');
        this._nextItem.connect('activate', () => {
            if (this._historyManager.canGoForward()) {
                const nextWallpaper = this._historyManager.getNext();
                this._applyWallpaper(nextWallpaper);
            } else {
                this._triggerWchangerRotation();
            }
        });
        this.menu.addMenuItem(this._nextItem);

        this._favItem = new PopupMenu.PopupImageMenuItem(_('Add to Favorites'), 'starred-symbolic');
        this._favItem.connect('activate', () => {
            this._favoriteCurrentWallpaper();
        });
        this.menu.addMenuItem(this._favItem);

        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        // Section 2: Online Sources Submenu
        const sourcesSubMenu = new PopupMenu.PopupSubMenuMenuItem(_('Online Providers'), true);
        if (sourcesSubMenu.icon) {
            sourcesSubMenu.icon.icon_name = 'applications-internet-symbolic';
        }

        const providers = [
            { label: _('Bing Daily Photo'), key: 'bing', icon: 'camera-photo-symbolic' },
            { label: _('Wallhaven Toplist'), key: 'wallhaven', icon: 'image-x-generic-symbolic' },
            { label: _('Lorem Picsum (Random)'), key: 'picsum', icon: 'insert-image-symbolic' },
            { label: _('LoremFlickr (Nature)'), key: 'loremflickr', icon: 'emblem-photos-symbolic' },
        ];
        providers.forEach(p => {
            const item = new PopupMenu.PopupImageMenuItem(p.label, p.icon);
            item.connect('activate', () => {
                const multiMon = this._settings.get_boolean('enable-multi-monitor');
                const args = ['--online', p.key, '--no-repetition'];
                if (multiMon) args.push('-m');
                this._runWchangerCommand(args);
            });
            sourcesSubMenu.menu.addMenuItem(item);
        });
        this.menu.addMenuItem(sourcesSubMenu);

        // Section 3: Multi-Monitor Quick Action
        const multiMonItem = new PopupMenu.PopupImageMenuItem(_('Rotate Multi-Monitor'), 'video-display-symbolic');
        multiMonItem.connect('activate', () => {
            this._runWchangerCommand(['-m', '--no-repetition']);
        });
        this.menu.addMenuItem(multiMonItem);

        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        // Section 4: Automatic Background Rotator Switch
        this._serviceSwitch = new PopupMenu.PopupSwitchMenuItem(_('Background Rotator'), false);
        const rotatorIcon = new St.Icon({
            icon_name: 'view-refresh-symbolic',
            style_class: 'popup-menu-icon',
        });
        this._serviceSwitch.insert_child_at_index(rotatorIcon, 0);

        this._serviceSwitch.connect('toggled', (item, state) => {
            this._settings.set_boolean('rotator-enabled', state);
            if (state) {
                this._startRotatorTimer();
                this._triggerWchangerRotation();
                this._controlSystemdService('start');
            } else {
                this._stopRotatorTimer();
                this._controlSystemdService('stop');
            }
        });
        this.menu.addMenuItem(this._serviceSwitch);

        // Section 5: Folder & Settings shortcuts
        const openFavsItem = new PopupMenu.PopupImageMenuItem(_('Open Favorites Folder'), 'folder-open-symbolic');
        openFavsItem.connect('activate', () => {
            const favDir = this._getFavoritesDirectory();
            runCommandAsync(['xdg-open', favDir]);
        });
        this.menu.addMenuItem(openFavsItem);

        const prefsItem = new PopupMenu.PopupImageMenuItem(_('Extension Settings…'), 'preferences-system-symbolic');
        prefsItem.connect('activate', () => {
            this._extension.openPreferences();
        });
        this.menu.addMenuItem(prefsItem);

        this.menu.connect('open-state-changed', (menu, isOpen) => {
            if (isOpen) {
                this._checkSystemdServiceState();
                this._updateNavButtons();
            }
        });
    }

    _updateNavButtons() {
        if (this._prevItem) {
            this._prevItem.setSensitive(this._historyManager.canGoBack());
        }
    }

    _initRotator() {
        const enabled = this._settings.get_boolean('rotator-enabled');
        this._serviceSwitch.setToggleState(enabled);
        if (enabled) {
            this._startRotatorTimer();
        }
        this._checkSystemdServiceState();
    }

    _startRotatorTimer() {
        this._stopRotatorTimer();
        let intervalSec = this._settings.get_int('rotation-interval');
        if (intervalSec < 30) {
            intervalSec = 300;
        }

        this._rotatorTimerId = GLib.timeout_add_seconds(
            GLib.PRIORITY_DEFAULT,
            intervalSec,
            () => {
                this._triggerWchangerRotation();
                return GLib.SOURCE_CONTINUE;
            }
        );
    }

    _stopRotatorTimer() {
        if (this._rotatorTimerId) {
            GLib.Source.remove(this._rotatorTimerId);
            this._rotatorTimerId = null;
        }
    }

    _triggerWchangerRotation() {
        const multiMon = this._settings.get_boolean('enable-multi-monitor');
        const args = ['--no-repetition'];
        if (multiMon) {
            args.push('-m');
        }
        this._runWchangerCommand(args);
    }

    _runWchangerCommand(args) {
        const customPath = this._settings.get_string('custom-wchanger-path');
        const baseCmd = getWchangerCommand(customPath);
        if (!baseCmd) {
            Main.notify(
                'Anahita Wallpaper Changer',
                _('“wchanger” command not found. Please install via “pip install .” or configure path in settings.')
            );
            return;
        }

        const fullArgv = [...baseCmd, ...args];
        runCommandAsync(fullArgv, (success) => {
            if (success) {
                this._syncCurrentBackground();
            } else {
                Main.notify(
                    'Anahita Wallpaper Changer',
                    _('Failed to rotate wallpaper. Please verify image path or online connection.')
                );
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
                        'Anahita Wallpaper Changer',
                        `${_('Saved to Favorites:')} ${baseName}`
                    );
                } catch (e) {
                    logError(e, '[wchanger-extension] Failed to copy wallpaper to favorites');
                    Main.notify('Anahita Wallpaper Changer', _('Failed to save to favorites.'));
                }
            }
        );
    }

    _checkSystemdServiceState() {
        if (!GLib.find_program_in_path('systemctl')) {
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
                            if (activeState === 'active') {
                                this._serviceSwitch.setToggleState(true);
                                this._settings.set_boolean('rotator-enabled', true);
                            }
                        }
                    } catch (e) {
                        // Ignore D-Bus lookup errors
                    }
                }
            );
        } catch (e) {
            // Ignore
        }
    }

    _controlSystemdService(action) {
        if (!GLib.find_program_in_path('systemctl')) {
            return;
        }
        // Non-blocking attempt to control systemd service if present
        runCommandAsync(['systemctl', '--user', action, 'wallpaper-changer.service']);
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
