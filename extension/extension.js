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
const SUPPORTED_IMAGE_EXTENSIONS = new Set(['.jpg', '.jpeg', '.png', '.bmp', '.webp', '.svg', '.tiff']);

/**
 * Recursively or non-recursively enumerate image files in a directory.
 * Safely guards against circular symlinks, deep nesting, and limits file count for UI responsiveness.
 * Returns an array of absolute path strings.
 */
function scanLocalPhotos(dirPath, recursive = false) {
    const results = [];
    if (!dirPath || typeof dirPath !== 'string') return results;

    let expandedPath = dirPath.trim();
    if (expandedPath.length === 0) return results;
    if (expandedPath.startsWith('~')) {
        expandedPath = `${GLib.get_home_dir()}${expandedPath.substring(1)}`;
    }

    const dir = Gio.File.new_for_path(expandedPath);
    try {
        if (!dir.query_exists(null)) return results;
    } catch (e) {
        return results;
    }

    const visitedDirs = new Set();
    const MAX_DEPTH = 6;
    const MAX_FILES = 5000;

    function _scan(directory, depth) {
        if (depth > MAX_DEPTH || results.length >= MAX_FILES) return;

        let dirPathStr;
        try {
            dirPathStr = directory.get_path();
        } catch (e) {
            return;
        }
        if (!dirPathStr || visitedDirs.has(dirPathStr)) return;
        visitedDirs.add(dirPathStr);

        let enumerator = null;
        try {
            enumerator = directory.enumerate_children(
                'standard::name,standard::type,standard::is-symlink',
                Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,
                null
            );
        } catch (e) {
            return;
        }

        try {
            let info;
            while ((info = enumerator.next_file(null)) !== null) {
                if (results.length >= MAX_FILES) break;

                const name = info.get_name();
                if (!name || name.startsWith('.')) continue;

                const child = directory.get_child(name);
                const fileType = info.get_file_type();
                const isSymlink = info.get_is_symlink();

                if (fileType === Gio.FileType.REGULAR) {
                    const lowerName = name.toLowerCase();
                    const dotIndex = lowerName.lastIndexOf('.');
                    if (dotIndex >= 0) {
                        const ext = lowerName.substring(dotIndex);
                        if (SUPPORTED_IMAGE_EXTENSIONS.has(ext)) {
                            const childPath = child.get_path();
                            if (childPath) results.push(childPath);
                        }
                    }
                } else if (recursive && fileType === Gio.FileType.DIRECTORY && !isSymlink) {
                    _scan(child, depth + 1);
                }
            }
        } catch (e) {
            // Protect against directory read errors
        } finally {
            try {
                if (enumerator) enumerator.close(null);
            } catch (e) {}
        }
    }

    _scan(dir, 0);
    results.sort();
    return results;
}

let _localPhotosCache = { dir: '', recursive: false, timestamp: 0, photos: [] };

function getLocalPhotos(dirPath, recursive = false, forceRefresh = false) {
    const now = Date.now();
    if (!forceRefresh &&
        _localPhotosCache.dir === dirPath &&
        _localPhotosCache.recursive === recursive &&
        (now - _localPhotosCache.timestamp) < 5000) {
        return _localPhotosCache.photos;
    }
    const photos = scanLocalPhotos(dirPath, recursive);
    _localPhotosCache = { dir: dirPath, recursive, timestamp: now, photos };
    return photos;
}

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
        try {
            this._settings = extension.getSettings('org.gnome.shell.extensions.wchanger');
        } catch (e) {
            logError(e, '[wchanger-extension] Failed to load extension schema');
            this._settings = null;
        }

        try {
            this._bgSettings = new Gio.Settings({ schema_id: GNOME_BG_SCHEMA });
        } catch (e) {
            logError(e, '[wchanger-extension] Failed to load GNOME background settings');
            this._bgSettings = null;
        }

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
        if (this._settings) {
            this._intervalChangedId = this._settings.connect('changed::rotation-interval', () => {
                if (this._getBooleanSetting('rotator-enabled', false)) {
                    this._startRotatorTimer();
                }
            });

            this._rotatorEnabledChangedId = this._settings.connect('changed::rotator-enabled', () => {
                const enabled = this._getBooleanSetting('rotator-enabled', false);
                if (this._serviceSwitch && this._serviceSwitch.state !== enabled) {
                    this._serviceSwitch.setToggleState(enabled);
                }
                if (enabled) {
                    this._startRotatorTimer();
                } else {
                    this._stopRotatorTimer();
                }
            });

            this._wallpaperSourceChangedId = this._settings.connect('changed::wallpaper-source', () => {
                const isLocal = this._getStringSetting('wallpaper-source', 'local') === 'local';
                if (this._useLocalSourceSwitch && this._useLocalSourceSwitch.state !== isLocal) {
                    this._useLocalSourceSwitch.setToggleState(isLocal);
                }
            });
        }

        // Listen for external wallpaper changes to keep history in sync (both light and dark modes)
        if (this._bgSettings) {
            this._bgChangedId = this._bgSettings.connect('changed::picture-uri', () => {
                this._syncCurrentBackground();
            });
            this._bgDarkChangedId = this._bgSettings.connect('changed::picture-uri-dark', () => {
                this._syncCurrentBackground();
            });
        }
    }

    _gettext(str) {
        if (this._extension && typeof this._extension.gettext === 'function') {
            try {
                return this._extension.gettext(str);
            } catch (e) {}
        }
        if (typeof _ === 'function') {
            try {
                return _(str);
            } catch (e) {}
        }
        return str;
    }

    _getStringSetting(key, fallback = '') {
        try {
            if (this._settings?.settings_schema?.has_key(key)) {
                return this._settings.get_string(key);
            }
        } catch (e) {}
        return fallback;
    }

    _setStringSetting(key, val) {
        try {
            if (this._settings?.settings_schema?.has_key(key)) {
                this._settings.set_string(key, val);
            }
        } catch (e) {}
    }

    _getBooleanSetting(key, fallback = false) {
        try {
            if (this._settings?.settings_schema?.has_key(key)) {
                return this._settings.get_boolean(key);
            }
        } catch (e) {}
        return fallback;
    }

    _setBooleanSetting(key, val) {
        try {
            if (this._settings?.settings_schema?.has_key(key)) {
                this._settings.set_boolean(key, Boolean(val));
            }
        } catch (e) {}
    }

    _getIntSetting(key, fallback = 300) {
        try {
            if (this._settings?.settings_schema?.has_key(key)) {
                return this._settings.get_int(key);
            }
        } catch (e) {}
        return fallback;
    }

    destroy() {
        if (this._rotatorTimerId) {
            GLib.Source.remove(this._rotatorTimerId);
            this._rotatorTimerId = null;
        }
        if (this._intervalChangedId && this._settings) {
            this._settings.disconnect(this._intervalChangedId);
            this._intervalChangedId = null;
        }
        if (this._rotatorEnabledChangedId && this._settings) {
            this._settings.disconnect(this._rotatorEnabledChangedId);
            this._rotatorEnabledChangedId = null;
        }
        if (this._wallpaperSourceChangedId && this._settings) {
            this._settings.disconnect(this._wallpaperSourceChangedId);
            this._wallpaperSourceChangedId = null;
        }
        if (this._bgChangedId && this._bgSettings) {
            this._bgSettings.disconnect(this._bgChangedId);
            this._bgChangedId = null;
        }
        if (this._bgDarkChangedId && this._bgSettings) {
            this._bgSettings.disconnect(this._bgDarkChangedId);
            this._bgDarkChangedId = null;
        }
        this._bgSettings = null;
        this._settings = null;
        this._wallhavenMenuItems = null;
        super.destroy();
    }

    _syncCurrentBackground() {
        try {
            let uri = this._bgSettings ? this._bgSettings.get_string('picture-uri') : '';
            if (!uri && this._bgSettings) {
                uri = this._bgSettings.get_string('picture-uri-dark');
            }
            if (uri) {
                let path = uri.startsWith('file://') ? uri.replace('file://', '') : uri;
                try {
                    path = decodeURIComponent(path);
                } catch (e) {
                    // Fallback to raw string if malformed URI encoding
                }
                this._historyManager.recordWallpaper(path);
            }
            this._updateNavButtons();
        } catch (e) {
            logError(e, '[wchanger-extension] Error syncing background');
        }
    }

    _applyWallpaper(filePath) {
        if (!filePath) return;
        try {
            const file = Gio.File.new_for_path(filePath);
            if (!file.query_exists(null)) {
                Main.notify('Anahita Wallpaper Changer', _('Wallpaper file not found: ') + filePath);
                return;
            }
            const fileUri = file.get_uri();
            if (this._bgSettings) {
                this._bgSettings.set_string('picture-uri', fileUri);
                this._bgSettings.set_string('picture-uri-dark', fileUri);
            }
            this._updateNavButtons();
        } catch (e) {
            logError(e, `[wchanger-extension] Failed to apply wallpaper: ${filePath}`);
        }
    }

    _buildMenu() {
        // Section 1: Navigation Controls (Previous, Next, Favorite)
        this._prevItem = new PopupMenu.PopupImageMenuItem(this._gettext('Previous'), 'media-skip-backward-symbolic');
        this._prevItem.connect('activate', () => {
            const prevWallpaper = this._historyManager.getPrevious();
            if (prevWallpaper) {
                this._applyWallpaper(prevWallpaper);
            }
        });
        this.menu.addMenuItem(this._prevItem);

        this._nextItem = new PopupMenu.PopupImageMenuItem(this._gettext('Next Wallpaper'), 'media-skip-forward-symbolic');
        this._nextItem.connect('activate', () => {
            if (this._historyManager.canGoForward()) {
                const nextWallpaper = this._historyManager.getNext();
                this._applyWallpaper(nextWallpaper);
            } else {
                this._triggerWchangerRotation();
            }
        });
        this.menu.addMenuItem(this._nextItem);

        this._favItem = new PopupMenu.PopupImageMenuItem(this._gettext('Add to Favorites'), 'starred-symbolic');
        this._favItem.connect('activate', () => {
            this._favoriteCurrentWallpaper();
        });
        this.menu.addMenuItem(this._favItem);

        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        // Section 2: Local Photos
        const localSubMenu = new PopupMenu.PopupSubMenuMenuItem(this._gettext('Local Photos'), true);
        if (localSubMenu.icon) {
            localSubMenu.icon.icon_name = 'folder-pictures-symbolic';
        }

        const isLocalActive = this._getStringSetting('wallpaper-source', 'local') === 'local';
        this._useLocalSourceSwitch = new PopupMenu.PopupSwitchMenuItem(this._gettext('Use as Active Source'), isLocalActive);
        this._useLocalSourceSwitch.connect('toggled', (item, state) => {
            this._setStringSetting('wallpaper-source', state ? 'local' : 'online');
        });
        localSubMenu.menu.addMenuItem(this._useLocalSourceSwitch);

        const openLocalDirItem = new PopupMenu.PopupImageMenuItem(this._gettext('Open Photos Folder'), 'folder-open-symbolic');
        openLocalDirItem.connect('activate', () => {
            const localDir = this._getLocalPhotosDirectory();
            runCommandAsync(['xdg-open', localDir]);
        });
        localSubMenu.menu.addMenuItem(openLocalDirItem);

        this._localPhotoCountLabel = new PopupMenu.PopupMenuItem('', { reactive: false });
        localSubMenu.menu.addMenuItem(this._localPhotoCountLabel);

        // Update photo count and switch state when submenu opens
        localSubMenu.menu.connect('open-state-changed', (menu, isOpen) => {
            if (isOpen) {
                const localDir = this._getLocalPhotosDirectory();
                const recursive = this._getBooleanSetting('recursive-scan', true);
                const photos = getLocalPhotos(localDir, recursive);
                const countText = photos.length > 0
                    ? `${photos.length} ${this._gettext('photos found')}`
                    : this._gettext('No photos found');
                const homeDir = GLib.get_home_dir();
                const displayDir = localDir.startsWith(homeDir)
                    ? `~${localDir.substring(homeDir.length)}`
                    : localDir;
                this._localPhotoCountLabel.label.set_text(`${displayDir} (${countText})`);

                const isLocal = this._getStringSetting('wallpaper-source', 'local') === 'local';
                if (this._useLocalSourceSwitch.state !== isLocal) {
                    this._useLocalSourceSwitch.setToggleState(isLocal);
                }
            }
        });

        this.menu.addMenuItem(localSubMenu);

        // Section 3: Online Sources Submenu
        const sourcesSubMenu = new PopupMenu.PopupSubMenuMenuItem(this._gettext('Online Providers'), true);
        if (sourcesSubMenu.icon) {
            sourcesSubMenu.icon.icon_name = 'applications-internet-symbolic';
        }

        const providers = [
            { label: this._gettext('Wallhaven'), key: 'wallhaven', icon: 'image-x-generic-symbolic' },
            { label: this._gettext('Bing Daily Photo'), key: 'bing', icon: 'camera-photo-symbolic' },
            { label: this._gettext('Lorem Picsum (Random)'), key: 'picsum', icon: 'insert-image-symbolic' },
            { label: this._gettext('LoremFlickr (Nature)'), key: 'loremflickr', icon: 'emblem-photos-symbolic' },
        ];
        providers.forEach(p => {
            const item = new PopupMenu.PopupImageMenuItem(p.label, p.icon);
            item.connect('activate', () => {
                this._setStringSetting('wallpaper-source', 'online');
                this._setStringSetting('default-provider', p.key);
                const multiMon = this._getBooleanSetting('enable-multi-monitor', false);
                const args = ['--online', p.key, '--no-repetition'];
                if (p.key === 'wallhaven') {
                    const category = (this._getStringSetting('wallhaven-category', 'nature') || '').trim();
                    if (category.length > 0) {
                        args.push('-C', category);
                    }
                }
                if (multiMon) args.push('-m');
                this._runWchangerCommand(args);
            });
            sourcesSubMenu.menu.addMenuItem(item);
        });
        this.menu.addMenuItem(sourcesSubMenu);

        // Section 3b: Wallhaven Categories Submenu
        const wallhavenSubMenu = new PopupMenu.PopupSubMenuMenuItem(this._gettext('Wallhaven Categories'), true);
        if (wallhavenSubMenu.icon) {
            wallhavenSubMenu.icon.icon_name = 'view-grid-symbolic';
        }

        const wallhavenCategories = [
            { key: 'nature', label: this._gettext('Nature & Landscapes') },
            { key: 'space', label: this._gettext('Space & Astronomy') },
            { key: 'anime', label: this._gettext('Anime Artwork') },
            { key: 'cyberpunk', label: this._gettext('Cyberpunk & Sci-Fi') },
            { key: 'city', label: this._gettext('City & Architecture') },
            { key: 'cars', label: this._gettext('Cars & Vehicles') },
            { key: 'gaming', label: this._gettext('Gaming & Fantasy') },
            { key: 'minimalism', label: this._gettext('Minimalism') },
            { key: 'general', label: this._gettext('General Photography') },
            { key: 'all', label: this._gettext('All (Random)') },
        ];

        this._wallhavenMenuItems = [];
        wallhavenCategories.forEach(cat => {
            const item = new PopupMenu.PopupMenuItem(cat.label);
            item._categoryKey = cat.key;
            item.connect('activate', () => {
                this._setStringSetting('wallpaper-source', 'online');
                this._setStringSetting('default-provider', 'wallhaven');
                this._setStringSetting('wallhaven-category', cat.key);
                const multiMon = this._getBooleanSetting('enable-multi-monitor', false);
                const args = ['--online', 'wallhaven', '-C', cat.key, '--no-repetition'];
                if (multiMon) args.push('-m');
                this._runWchangerCommand(args);
            });
            this._wallhavenMenuItems.push(item);
            wallhavenSubMenu.menu.addMenuItem(item);
        });

        const updateWallhavenMenuOrnaments = () => {
            const currentCat = (this._getStringSetting('wallhaven-category', 'nature') || 'nature').toLowerCase().trim();
            for (const item of this._wallhavenMenuItems) {
                const isSelected = (item._categoryKey === currentCat);
                if (typeof item.setOrnament === 'function') {
                    const checkOrnament = PopupMenu.Ornament?.CHECK ?? 2;
                    const noneOrnament = PopupMenu.Ornament?.NONE ?? 0;
                    item.setOrnament(isSelected ? checkOrnament : noneOrnament);
                }
            }
        };

        // Initialize checkmarks immediately
        updateWallhavenMenuOrnaments();

        wallhavenSubMenu.menu.connect('open-state-changed', (menu, isOpen) => {
            if (isOpen) {
                updateWallhavenMenuOrnaments();
            }
        });

        this.menu.addMenuItem(wallhavenSubMenu);

        // Section 3c: Multi-Monitor Quick Action
        const multiMonItem = new PopupMenu.PopupImageMenuItem(this._gettext('Rotate Multi-Monitor'), 'video-display-symbolic');
        multiMonItem.connect('activate', () => {
            const source = this._getStringSetting('wallpaper-source', 'local');
            if (source === 'local') {
                const localDir = this._getLocalPhotosDirectory();
                const recursive = this._getBooleanSetting('recursive-scan', true);
                const args = ['-m', '--no-repetition'];
                if (recursive) args.push('-R');
                args.push(localDir);
                this._runWchangerCommand(args);
            } else {
                const defaultProvider = this._getStringSetting('default-provider', 'wallhaven') || 'wallhaven';
                const args = ['--online', defaultProvider, '-m', '--no-repetition'];
                if (defaultProvider === 'wallhaven') {
                    const category = (this._getStringSetting('wallhaven-category', 'nature') || '').trim();
                    if (category.length > 0) {
                        args.push('-C', category);
                    }
                }
                this._runWchangerCommand(args);
            }
        });
        this.menu.addMenuItem(multiMonItem);

        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        // Section 4: Automatic Background Rotator Switch
        this._serviceSwitch = new PopupMenu.PopupSwitchMenuItem(this._gettext('Background Rotator'), false);
        const rotatorIcon = new St.Icon({
            icon_name: 'view-refresh-symbolic',
            style_class: 'popup-menu-icon',
        });
        this._serviceSwitch.insert_child_at_index(rotatorIcon, 0);

        this._serviceSwitch.connect('toggled', (item, state) => {
            this._setBooleanSetting('rotator-enabled', state);
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
        const openFavsItem = new PopupMenu.PopupImageMenuItem(this._gettext('Open Favorites Folder'), 'folder-open-symbolic');
        openFavsItem.connect('activate', () => {
            const favDir = this._getFavoritesDirectory();
            runCommandAsync(['xdg-open', favDir]);
        });
        this.menu.addMenuItem(openFavsItem);

        const prefsItem = new PopupMenu.PopupImageMenuItem(this._gettext('Extension Settings…'), 'preferences-system-symbolic');
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
        const enabled = this._getBooleanSetting('rotator-enabled', false);
        this._serviceSwitch.setToggleState(enabled);
        if (enabled) {
            this._startRotatorTimer();
        }
        this._checkSystemdServiceState();
    }

    _startRotatorTimer() {
        this._stopRotatorTimer();
        let intervalSec = this._getIntSetting('rotation-interval', 300);
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
        const source = this._getStringSetting('wallpaper-source', 'local');
        if (source === 'local') {
            this._applyRandomLocalPhoto();
            return;
        }

        const multiMon = this._getBooleanSetting('enable-multi-monitor', false);
        const defaultProvider = this._getStringSetting('default-provider', 'wallhaven') || 'wallhaven';
        const args = ['--online', defaultProvider, '--no-repetition'];
        if (multiMon) {
            args.push('-m');
        }
        if (defaultProvider === 'wallhaven') {
            const category = (this._getStringSetting('wallhaven-category', 'nature') || '').trim();
            if (category.length > 0) {
                args.push('-C', category);
            }
        }
        this._runWchangerCommand(args);
    }

    _runWchangerCommand(args) {
        const customPath = this._getStringSetting('custom-wchanger-path', '');
        const baseCmd = getWchangerCommand(customPath);
        if (!baseCmd) {
            Main.notify(
                'Anahita Wallpaper Changer',
                this._gettext('“wchanger” command not found. Please install via “pip install .” or configure path in settings.')
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
                    this._gettext('Failed to rotate wallpaper. Please verify image path or online connection.')
                );
            }
        });
    }

    _getFavoritesDirectory() {
        let customPath = this._getStringSetting('favorites-directory', '');
        if (!customPath || customPath.trim().length === 0) {
            const pics = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_PICTURES) || `${GLib.get_home_dir()}/Pictures`;
            customPath = `${pics}/Wallpapers/Favorites`;
        }
        if (customPath.startsWith('~')) {
            customPath = `${GLib.get_home_dir()}${customPath.substring(1)}`;
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

    _getLocalPhotosDirectory() {
        let customPath = this._getStringSetting('wallpapers-directory', '');
        if (!customPath || customPath.trim().length === 0) {
            const pics = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_PICTURES) || `${GLib.get_home_dir()}/Pictures`;
            customPath = `${pics}/Wallpapers`;
        }
        // Expand ~ if present
        if (customPath.startsWith('~')) {
            customPath = `${GLib.get_home_dir()}${customPath.substring(1)}`;
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

    _applyRandomLocalPhoto() {
        const localDir = this._getLocalPhotosDirectory();
        const recursive = this._getBooleanSetting('recursive-scan', true);
        const photos = getLocalPhotos(localDir, recursive, true);

        if (photos.length === 0) {
            Main.notify(
                'Anahita Wallpaper Changer',
                `${this._gettext('No photos found in local folder:')} ${localDir}`
            );
            return;
        }

        // Pick a random photo, avoiding the current wallpaper if possible
        const currentPath = this._historyManager.getCurrent();
        let candidates = photos;
        if (photos.length > 1 && currentPath) {
            candidates = photos.filter(p => p !== currentPath);
            if (candidates.length === 0) candidates = photos;
        }

        const randomIndex = Math.floor(Math.random() * candidates.length);
        const chosen = candidates[randomIndex];
        this._applyWallpaper(chosen);
    }

    _favoriteCurrentWallpaper() {
        const currentPath = this._historyManager.getCurrent();
        if (!currentPath) {
            Main.notify('Anahita Wallpaper Changer', this._gettext('No active wallpaper found to favorite.'));
            return;
        }

        const sourceFile = Gio.File.new_for_path(currentPath);
        if (!sourceFile.query_exists(null)) {
            Main.notify('Anahita Wallpaper Changer', this._gettext('Active wallpaper file not accessible.'));
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
                        `${this._gettext('Saved to Favorites:')} ${baseName}`
                    );
                } catch (e) {
                    logError(e, '[wchanger-extension] Failed to copy wallpaper to favorites');
                    Main.notify('Anahita Wallpaper Changer', this._gettext('Failed to save to favorites.'));
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
                                this._setBooleanSetting('rotator-enabled', true);
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
        try {
            this.initTranslations();
        } catch (e) {}
        try {
            this._settings = this.getSettings('org.gnome.shell.extensions.wchanger');
        } catch (e) {
            logError(e, '[wchanger-extension] Failed to load extension settings');
            this._settings = null;
        }
        this._indicator = null;

        // Respect show-indicator setting
        if (this._settings) {
            this._showIndicatorChangedId = this._settings.connect('changed::show-indicator', () => {
                this._updateIndicatorVisibility();
            });
        }

        this._updateIndicatorVisibility();
    }

    _updateIndicatorVisibility() {
        let show = true;
        try {
            if (this._settings?.settings_schema?.has_key('show-indicator')) {
                show = this._settings.get_boolean('show-indicator');
            }
        } catch (e) {}
        if (show && !this._indicator) {
            this._indicator = new WchangerIndicator(this);
            Main.panel.addToStatusArea(this.uuid, this._indicator);
        } else if (!show && this._indicator) {
            this._indicator.destroy();
            this._indicator = null;
        }
    }

    disable() {
        if (this._showIndicatorChangedId && this._settings) {
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
