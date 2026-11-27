import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import GObject from 'gi://GObject';
import St from 'gi://St';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';
import { Extension, gettext as _ } from 'resource:///org/gnome/shell/extensions/extension.js';

const GNOME_BG_SCHEMA = 'org.gnome.desktop.background';
const MAX_HISTORY_ITEMS = 50;
const SUPPORTED_IMAGE_EXTENSIONS = new Set(['.jpg', '.jpeg', '.png', '.bmp', '.webp', '.svg', '.tiff']);
const DBUS_BUS_NAME = 'io.github.ibehii.Wchanger';
const DBUS_OBJECT_PATH = '/io/github/ibehii/Wchanger';
const DBUS_INTERFACE_NAME = 'io.github.ibehii.Wchanger';

function getLocalPhotos(dirPath, recursive = false) {
    const path = dirPath?.replace(/^~/, GLib.get_home_dir()).trim();
    if (!path || !GLib.file_test(path, GLib.FileTest.IS_DIR))
        return [];

    const dir = Gio.File.new_for_path(path);
    const photos = [];
    const enumerator = dir.enumerate_children(
        'standard::name,standard::type',
        Gio.FileQueryInfoFlags.NONE,
        null
    );

    try {
        let info;
        while ((info = enumerator.next_file(null))) {
            const name = info.get_name();
            if (name.startsWith('.'))
                continue;
            const childPath = dir.get_child(name).get_path();
            const type = info.get_file_type();
            if (type === Gio.FileType.REGULAR) {
                const ext = name.slice(name.lastIndexOf('.')).toLowerCase();
                if (SUPPORTED_IMAGE_EXTENSIONS.has(ext))
                    photos.push(childPath);
            } else if (recursive && type === Gio.FileType.DIRECTORY) {
                photos.push(...getLocalPhotos(childPath, true));
            }
        }
    } finally {
        enumerator.close(null);
    }

    return photos;
}

function resolveDirectory(customPath, defaultSubdir) {
    let dir = customPath?.trim();
    if (!dir) {
        const pics = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_PICTURES) || `${GLib.get_home_dir()}/Pictures`;
        dir = `${pics}/${defaultSubdir}`;
    }
    if (dir.startsWith('~'))
        dir = `${GLib.get_home_dir()}${dir.slice(1)}`;

    GLib.mkdir_with_parents(dir, 0o755);
    return dir;
}

function openFolder(path) {
    Gio.AppInfo.launch_default_for_uri(Gio.File.new_for_path(path).get_uri(), null);
}

class HistoryManager {
    constructor() {
        this._historyFile = `${GLib.get_user_cache_dir()}/wchanger/history.json`;
        this._history = [];
        this._currentIndex = -1;
        this._load();
    }

    _load() {
        const file = Gio.File.new_for_path(this._historyFile);
        if (!file.query_exists(null))
            return;

        file.load_contents_async(null, (fileObj, res) => {
            const [ok, contents] = fileObj.load_contents_finish(res);
            if (!ok)
                return;
            try {
                const data = JSON.parse(new TextDecoder().decode(contents));
                if (Array.isArray(data.items)) {
                    this._history = data.items;
                    this._currentIndex = typeof data.currentIndex === 'number'
                        ? data.currentIndex
                        : this._history.length - 1;
                }
            } catch (e) {
                if (!(e instanceof SyntaxError))
                    throw e;
            }
        });
    }

    _save() {
        GLib.mkdir_with_parents(GLib.path_get_dirname(this._historyFile), 0o755);
        const file = Gio.File.new_for_path(this._historyFile);
        const data = JSON.stringify({
            items: this._history.slice(-MAX_HISTORY_ITEMS),
            currentIndex: this._currentIndex,
        });
        file.replace_contents_bytes_async(
            new GLib.Bytes(new TextEncoder().encode(data)),
            null,
            false,
            Gio.FileCreateFlags.REPLACE_DESTINATION,
            null,
            null
        );
    }

    recordWallpaper(filePath) {
        if (!filePath || this.getCurrent() === filePath)
            return;

        if (this._history.at(-1) !== filePath) {
            this._history.push(filePath);
            if (this._history.length > MAX_HISTORY_ITEMS)
                this._history.shift();
        }
        this._currentIndex = this._history.length - 1;
        this._save();
    }

    canGoBack() {
        return this._currentIndex > 0;
    }

    canGoForward() {
        return this._currentIndex < this._history.length - 1;
    }

    getPrevious() {
        if (!this.canGoBack())
            return null;
        this._currentIndex--;
        this._save();
        return this._history[this._currentIndex];
    }

    getNext() {
        if (!this.canGoForward())
            return null;
        this._currentIndex++;
        this._save();
        return this._history[this._currentIndex];
    }

    getCurrent() {
        return this._history[this._currentIndex] ?? null;
    }
}

class WchangerIndicator extends PanelMenu.Button {
    static {
        GObject.registerClass(this);
    }

    constructor(extension) {
        super(0.0, 'Anahita Wallpaper Changer');
        this._extension = extension;
        this._settings = extension.getSettings();
        this._bgSettings = new Gio.Settings({ schema_id: GNOME_BG_SCHEMA });
        this._historyManager = new HistoryManager();

        this._rotatorTimerId = null;
        this._rotationCancellable = null;

        this._icon = new St.Icon({
            icon_name: 'preferences-desktop-wallpaper-symbolic',
            style_class: 'system-status-icon wchanger-indicator-icon',
        });
        this.add_child(this._icon);

        this._buildMenu();
        this._syncCurrentBackground();
        this._initRotator();

        this._settings.connectObject(
            'changed::rotation-interval', () => {
                if (this._settings.get_boolean('rotator-enabled'))
                    this._startRotatorTimer();
            },
            'changed::rotator-enabled', () => {
                const enabled = this._settings.get_boolean('rotator-enabled');
                if (this._serviceSwitch.state !== enabled)
                    this._serviceSwitch.setToggleState(enabled);

                if (enabled) {
                    this._startRotatorTimer();
                    this._controlSystemdService('start');
                } else {
                    this._stopRotatorTimer();
                    this._cancelActiveRotation();
                    this._controlSystemdService('stop');
                }
            },
            'changed::wallpaper-source', () => {
                const isLocal = this._settings.get_string('wallpaper-source') === 'local';
                if (this._useLocalSourceSwitch.state !== isLocal)
                    this._useLocalSourceSwitch.setToggleState(isLocal);
                this._updateCategoryVisibility();
                this._updateProviderOrnaments();
            },
            'changed::default-provider', () => {
                this._updateCategoryVisibility();
                this._updateProviderOrnaments();
            },
            'changed::wallhaven-category', () => this._updateWallhavenOrnaments(),
            'changed::unsplash-category', () => this._updateUnsplashOrnaments(),
            this
        );

        this._bgSettings.connectObject(
            'changed::picture-uri', () => this._syncCurrentBackground(),
            'changed::picture-uri-dark', () => this._syncCurrentBackground(),
            this
        );
    }

    _buildMenu() {
        this._prevItem = new PopupMenu.PopupImageMenuItem(_('Previous'), 'media-skip-backward-symbolic');
        this._prevItem.connectObject('activate', () => {
            const prev = this._historyManager.getPrevious();
            if (prev)
                this._applyWallpaper(prev);
        }, this);
        this.menu.addMenuItem(this._prevItem);

        this._nextItem = new PopupMenu.PopupImageMenuItem(_('Next Wallpaper'), 'media-skip-forward-symbolic');
        this._nextItem.connectObject('activate', () => {
            this._ensureRotatorEnabled();
            if (this._historyManager.canGoForward()) {
                const next = this._historyManager.getNext();
                if (next)
                    this._applyWallpaper(next);
            } else {
                this._triggerWchangerRotation();
            }
        }, this);
        this.menu.addMenuItem(this._nextItem);

        this._favItem = new PopupMenu.PopupImageMenuItem(_('Add to Favorites'), 'starred-symbolic');
        this._favItem.connectObject('activate', () => this._favoriteCurrentWallpaper(), this);
        this.menu.addMenuItem(this._favItem);

        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        const localSubMenu = new PopupMenu.PopupSubMenuMenuItem(_('Local Photos'), true);
        if (localSubMenu.icon)
            localSubMenu.icon.icon_name = 'folder-pictures-symbolic';

        this._useLocalSourceSwitch = new PopupMenu.PopupSwitchMenuItem(_('Use as Active Source'), this._settings.get_string('wallpaper-source') === 'local');
        this._useLocalSourceSwitch.connectObject('toggled', (item, state) => {
            this._settings.set_string('wallpaper-source', state ? 'local' : 'online');
            if (state)
                this._ensureRotatorEnabled();
        }, this);
        localSubMenu.menu.addMenuItem(this._useLocalSourceSwitch);

        const openLocalDirItem = new PopupMenu.PopupImageMenuItem(_('Open Photos Folder'), 'folder-open-symbolic');
        openLocalDirItem.connectObject('activate', () => openFolder(this._getLocalPhotosDirectory()), this);
        localSubMenu.menu.addMenuItem(openLocalDirItem);

        this._localPhotoCountLabel = new PopupMenu.PopupMenuItem('', { reactive: false });
        localSubMenu.menu.addMenuItem(this._localPhotoCountLabel);

        localSubMenu.menu.connectObject('open-state-changed', (menu, isOpen) => {
            if (!isOpen)
                return;
            const localDir = this._getLocalPhotosDirectory();
            const photos = getLocalPhotos(localDir, this._settings.get_boolean('recursive-scan'));
            const countText = photos.length > 0 ? `${photos.length} ${_('photos found')}` : _('No photos found');
            const home = GLib.get_home_dir();
            const displayDir = localDir.startsWith(home) ? `~${localDir.slice(home.length)}` : localDir;
            this._localPhotoCountLabel.label.set_text(`${displayDir} (${countText})`);

            const isLocal = this._settings.get_string('wallpaper-source') === 'local';
            if (this._useLocalSourceSwitch.state !== isLocal)
                this._useLocalSourceSwitch.setToggleState(isLocal);
        }, this);
        this.menu.addMenuItem(localSubMenu);

        const sourcesSubMenu = new PopupMenu.PopupSubMenuMenuItem(_('Online Providers'), true);
        if (sourcesSubMenu.icon)
            sourcesSubMenu.icon.icon_name = 'applications-internet-symbolic';

        const providers = [
            { label: _('Wallhaven'), key: 'wallhaven', icon: 'image-x-generic-symbolic' },
            { label: _('Unsplash'), key: 'unsplash', icon: 'camera-photo-symbolic' },
            { label: _('Bing Daily Photo'), key: 'bing', icon: 'camera-photo-symbolic' },
            { label: _('Lorem Picsum (Random)'), key: 'picsum', icon: 'insert-image-symbolic' },
            { label: _('LoremFlickr (Nature)'), key: 'loremflickr', icon: 'emblem-photos-symbolic' },
        ];

        this._providerMenuItems = [];
        for (const p of providers) {
            const item = new PopupMenu.PopupImageMenuItem(p.label, p.icon);
            item._providerKey = p.key;
            item.connectObject('activate', () => {
                this._settings.set_string('wallpaper-source', 'online');
                this._settings.set_string('default-provider', p.key);
                this._updateProviderOrnaments();

                if (p.key === 'unsplash' && !this._settings.get_string('unsplash-access-key').trim()) {
                    Main.notify('Anahita Wallpaper Changer', _('Unsplash requires an API Access Key. Please configure your key in Extension Settings or see the Setup Guide.'));
                    Gio.AppInfo.launch_default_for_uri('https://github.com/ibehii/Wallpaper-changer#unsplash-setup-guide', null);
                    return;
                }

                this._ensureRotatorEnabled();
                this._rotateOnline(p.key);
            }, this);
            this._providerMenuItems.push(item);
            sourcesSubMenu.menu.addMenuItem(item);
        }

        sourcesSubMenu.menu.connectObject('open-state-changed', (menu, isOpen) => {
            if (isOpen)
                this._updateProviderOrnaments();
        }, this);
        this.menu.addMenuItem(sourcesSubMenu);

        this._wallhavenSubMenu = new PopupMenu.PopupSubMenuMenuItem(_('Wallhaven Categories'), true);
        if (this._wallhavenSubMenu.icon)
            this._wallhavenSubMenu.icon.icon_name = 'view-grid-symbolic';

        const wallhavenCategories = [
            { key: 'nature', label: _('Nature & Landscapes') },
            { key: 'space', label: _('Space & Astronomy') },
            { key: 'anime', label: _('Anime Artwork') },
            { key: 'cyberpunk', label: _('Cyberpunk & Sci-Fi') },
            { key: 'city', label: _('City & Architecture') },
            { key: 'cars', label: _('Cars & Vehicles') },
            { key: 'gaming', label: _('Gaming & Fantasy') },
            { key: 'minimalism', label: _('Minimalism') },
            { key: 'general', label: _('General Photography') },
            { key: 'all', label: _('All (Random)') },
        ];

        this._wallhavenMenuItems = [];
        for (const cat of wallhavenCategories) {
            const item = new PopupMenu.PopupMenuItem(cat.label);
            item._categoryKey = cat.key;
            item.connectObject('activate', () => {
                this._settings.set_string('wallpaper-source', 'online');
                this._settings.set_string('default-provider', 'wallhaven');
                this._settings.set_string('wallhaven-category', cat.key);
                this._ensureRotatorEnabled();
                this._rotateOnline('wallhaven');
            }, this);
            this._wallhavenMenuItems.push(item);
            this._wallhavenSubMenu.menu.addMenuItem(item);
        }

        this._wallhavenSubMenu.menu.connectObject('open-state-changed', (menu, isOpen) => {
            if (isOpen)
                this._updateWallhavenOrnaments();
        }, this);
        this.menu.addMenuItem(this._wallhavenSubMenu);

        this._unsplashSubMenu = new PopupMenu.PopupSubMenuMenuItem(_('Unsplash Categories'), true);
        if (this._unsplashSubMenu.icon)
            this._unsplashSubMenu.icon.icon_name = 'view-grid-symbolic';

        const unsplashCategories = [
            { key: 'nature', label: _('Nature & Landscapes') },
            { key: 'wallpapers', label: _('Desktop Wallpapers') },
            { key: 'travel', label: _('Travel & Exploration') },
            { key: 'architecture', label: _('Architecture & Interiors') },
            { key: 'space', label: _('Space & Astronomy') },
            { key: 'minimalism', label: _('Minimalism') },
            { key: 'animals', label: _('Animals & Wildlife') },
            { key: 'textures', label: _('Textures & Patterns') },
            { key: 'city', label: _('Street & City') },
            { key: 'technology', label: _('Technology & Cyber') },
            { key: 'all', label: _('All (Random)') },
        ];

        this._unsplashMenuItems = [];
        for (const cat of unsplashCategories) {
            const item = new PopupMenu.PopupMenuItem(cat.label);
            item._categoryKey = cat.key;
            item.connectObject('activate', () => {
                const key = this._settings.get_string('unsplash-access-key').trim();
                this._settings.set_string('wallpaper-source', 'online');
                this._settings.set_string('default-provider', 'unsplash');
                this._settings.set_string('unsplash-category', cat.key);

                if (!key) {
                    Main.notify('Anahita Wallpaper Changer', _('Unsplash requires an API Access Key. Please configure your key in Extension Settings or see the Setup Guide.'));
                    Gio.AppInfo.launch_default_for_uri('https://github.com/ibehii/Wallpaper-changer#unsplash-setup-guide', null);
                    return;
                }

                this._ensureRotatorEnabled();
                this._rotateOnline('unsplash');
            }, this);
            this._unsplashMenuItems.push(item);
            this._unsplashSubMenu.menu.addMenuItem(item);
        }

        this._unsplashSubMenu.menu.connectObject('open-state-changed', (menu, isOpen) => {
            if (isOpen)
                this._updateUnsplashOrnaments();
        }, this);
        this.menu.addMenuItem(this._unsplashSubMenu);

        this._unsplashGuideItem = new PopupMenu.PopupImageMenuItem(
            _('Unsplash Setup Guide (README.md)'),
            'help-browser-symbolic'
        );
        this._unsplashGuideItem.connectObject('activate', () => {
            Gio.AppInfo.launch_default_for_uri('https://github.com/ibehii/Wallpaper-changer#unsplash-setup-guide', null);
        }, this);
        this.menu.addMenuItem(this._unsplashGuideItem);

        const multiMonItem = new PopupMenu.PopupImageMenuItem(_('Rotate Multi-Monitor'), 'video-display-symbolic');
        multiMonItem.connectObject('activate', () => {
            this._ensureRotatorEnabled();
            if (this._settings.get_string('wallpaper-source') === 'local') {
                const localDir = this._getLocalPhotosDirectory();
                const photos = getLocalPhotos(localDir, this._settings.get_boolean('recursive-scan'));
                if (photos.length === 0) {
                    Main.notify('Anahita Wallpaper Changer', `${_('No photos found in local folder:')} ${localDir}`);
                    return;
                }
                const chosen = photos[Math.floor(Math.random() * photos.length)];
                this._applyWallpaper(chosen);
            } else {
                this._rotateOnline(this._settings.get_string('default-provider'), true);
            }
        }, this);
        this.menu.addMenuItem(multiMonItem);

        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        this._serviceSwitch = new PopupMenu.PopupSwitchMenuItem(_('Background Rotator'), false);
        const rotatorIcon = new St.Icon({
            icon_name: 'view-refresh-symbolic',
            style_class: 'popup-menu-icon',
        });
        this._serviceSwitch.insert_child_at_index(rotatorIcon, 0);
        this._serviceSwitch.connectObject('toggled', (item, state) => {
            if (this._settings.get_boolean('rotator-enabled') !== state)
                this._settings.set_boolean('rotator-enabled', state);
        }, this);
        this.menu.addMenuItem(this._serviceSwitch);

        const openFavsItem = new PopupMenu.PopupImageMenuItem(_('Open Favorites Folder'), 'folder-open-symbolic');
        openFavsItem.connectObject('activate', () => openFolder(this._getFavoritesDirectory()), this);
        this.menu.addMenuItem(openFavsItem);

        const prefsItem = new PopupMenu.PopupImageMenuItem(_('Extension Settings…'), 'preferences-system-symbolic');
        prefsItem.connectObject('activate', () => {
            this._extension.openPreferences();
        }, this);
        this.menu.addMenuItem(prefsItem);

        this.menu.connectObject('open-state-changed', (menu, isOpen) => {
            if (isOpen)
                this._updateNavButtons();
        }, this);

        this._updateCategoryVisibility();
        this._updateProviderOrnaments();
        this._updateWallhavenOrnaments();
        this._updateUnsplashOrnaments();
    }

    _updateOrnaments(items, activeKey, prop) {
        for (const item of items) {
            item.setOrnament(item[prop] === activeKey
                ? PopupMenu.Ornament.CHECK
                : PopupMenu.Ornament.NONE);
        }
    }

    _updateProviderOrnaments() {
        const active = this._settings.get_string('wallpaper-source') === 'online'
            ? this._settings.get_string('default-provider')
            : null;
        this._updateOrnaments(this._providerMenuItems, active, '_providerKey');
    }

    _updateWallhavenOrnaments() {
        this._updateOrnaments(
            this._wallhavenMenuItems,
            this._settings.get_string('wallhaven-category'),
            '_categoryKey'
        );
    }

    _updateUnsplashOrnaments() {
        this._updateOrnaments(
            this._unsplashMenuItems,
            this._settings.get_string('unsplash-category'),
            '_categoryKey'
        );
    }

    _updateCategoryVisibility() {
        const isOnline = this._settings.get_string('wallpaper-source') === 'online';
        const provider = this._settings.get_string('default-provider');

        this._wallhavenSubMenu.visible = isOnline && provider === 'wallhaven';
        this._unsplashSubMenu.visible = isOnline && provider === 'unsplash';
        this._unsplashGuideItem.visible = isOnline && provider === 'unsplash';
    }

    _ensureRotatorEnabled() {
        if (!this._settings.get_boolean('rotator-enabled'))
            this._settings.set_boolean('rotator-enabled', true);
    }

    _initRotator() {
        const enabled = this._settings.get_boolean('rotator-enabled');
        this._serviceSwitch.setToggleState(enabled);
        if (enabled)
            this._startRotatorTimer();
    }

    _startRotatorTimer() {
        this._stopRotatorTimer();
        let intervalSec = this._settings.get_int('rotation-interval');
        if (intervalSec < 30)
            intervalSec = 300;

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
        if (this._settings.get_string('wallpaper-source') === 'local') {
            this._applyRandomLocalPhoto();
            return;
        }

        this._rotateOnline(this._settings.get_string('default-provider'));
    }

    _rotateOnline(provider, multiMonitor = this._settings.get_boolean('enable-multi-monitor')) {
        let category = '';
        let unsplashKey = '';

        if (provider === 'wallhaven') {
            category = this._settings.get_string('wallhaven-category').trim();
        } else if (provider === 'unsplash') {
            unsplashKey = this._settings.get_string('unsplash-access-key').trim();
            if (!unsplashKey) {
                Main.notify('Anahita Wallpaper Changer', _('Unsplash requires an API Access Key. Please configure your key in Extension Settings or see the Setup Guide.'));
                return;
            }
            const cat = this._settings.get_string('unsplash-category').trim();
            if (cat && cat !== 'all')
                category = cat;
        }

        this._callWchangerDbus(provider, category, unsplashKey, multiMonitor);
    }

    _cancelActiveRotation() {
        if (this._rotationCancellable) {
            this._rotationCancellable.cancel();
            this._rotationCancellable = null;
        }
    }

    _callWchangerDbus(provider, category, unsplashKey, multiMonitor) {
        this._cancelActiveRotation();

        const cancellable = new Gio.Cancellable();
        this._rotationCancellable = cancellable;

        Gio.DBus.session.call(
            DBUS_BUS_NAME,
            DBUS_OBJECT_PATH,
            DBUS_INTERFACE_NAME,
            'RotateOnline',
            new GLib.Variant('(sssb)', [provider, category, unsplashKey, multiMonitor]),
            new GLib.VariantType('(bs)'),
            Gio.DBusCallFlags.NONE,
            30000,
            cancellable,
            (conn, res) => {
                if (this._rotationCancellable !== cancellable)
                    return;
                this._rotationCancellable = null;

                try {
                    const reply = conn.call_finish(res);
                    const [success, message] = reply.deep_unpack();

                    if (success) {
                        this._syncCurrentBackground();
                        return;
                    }

                    const isUnsplash = provider === 'unsplash';
                    const err = (message || '').toLowerCase();

                    if (isUnsplash && (err.includes('access key') || !unsplashKey)) {
                        Main.notify('Anahita Wallpaper Changer', _('Unsplash requires an API Access Key. Please configure your key in Extension Settings or see the Setup Guide.'));
                    } else if (isUnsplash && (err.includes('401') || err.includes('unauthorized'))) {
                        Main.notify('Anahita Wallpaper Changer', _('Unsplash API authentication failed (HTTP 401). Your Access Key is invalid or expired.'));
                    } else if (isUnsplash && (err.includes('403') || err.includes('rate limit'))) {
                        Main.notify('Anahita Wallpaper Changer', _('Unsplash hourly rate limit exceeded (HTTP 403). Free tier is limited to 50 requests/hour.'));
                    } else {
                        Main.notify('Anahita Wallpaper Changer', _('Failed to rotate wallpaper. Please verify image path or online connection.'));
                    }
                } catch (e) {
                    if (e.matches(Gio.IOErrorEnum, Gio.IOErrorEnum.CANCELLED))
                        return;

                    const msg = (e.message || '').toLowerCase();
                    if (msg.includes('serviceunknown') || msg.includes('namehasnoowner')) {
                        Main.notify('Anahita Wallpaper Changer', _('D-Bus service not available. Run “wchanger --install-dbus” to enable it.'));
                    } else {
                        Main.notify('Anahita Wallpaper Changer', _('Failed to rotate wallpaper. Please verify image path or online connection.'));
                    }
                }
            }
        );
    }

    _updateNavButtons() {
        this._prevItem?.setSensitive(this._historyManager.canGoBack());
    }

    _syncCurrentBackground() {
        const uri = this._bgSettings.get_string('picture-uri') ||
            this._bgSettings.get_string('picture-uri-dark');

        if (uri?.startsWith('file://')) {
            const [path] = GLib.filename_from_uri(uri);
            if (path)
                this._historyManager.recordWallpaper(path);
        }
        this._updateNavButtons();
    }

    _applyWallpaper(filePath) {
        if (!filePath)
            return;

        const file = Gio.File.new_for_path(filePath);
        if (!file.query_exists(null)) {
            Main.notify('Anahita Wallpaper Changer', `${_('Wallpaper file not found:')} ${filePath}`);
            return;
        }

        const uri = file.get_uri();
        this._bgSettings.set_string('picture-uri', uri);
        this._bgSettings.set_string('picture-uri-dark', uri);
        this._updateNavButtons();
    }

    _getFavoritesDirectory() {
        return resolveDirectory(this._settings.get_string('favorites-directory'), 'Wallpapers/Favorites');
    }

    _getLocalPhotosDirectory() {
        return resolveDirectory(this._settings.get_string('wallpapers-directory'), 'Wallpapers');
    }

    _applyRandomLocalPhoto() {
        const localDir = this._getLocalPhotosDirectory();
        const recursive = this._settings.get_boolean('recursive-scan');
        const photos = getLocalPhotos(localDir, recursive);

        if (photos.length === 0) {
            Main.notify('Anahita Wallpaper Changer', `${_('No photos found in local folder:')} ${localDir}`);
            return;
        }

        const current = this._historyManager.getCurrent();
        let candidates = photos.length > 1 && current
            ? photos.filter(p => p !== current)
            : photos;
        if (candidates.length === 0)
            candidates = photos;

        const chosen = candidates[Math.floor(Math.random() * candidates.length)];
        this._applyWallpaper(chosen);
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
                    Main.notify('Anahita Wallpaper Changer', `${_('Saved to Favorites:')} ${baseName}`);
                } catch {
                    Main.notify('Anahita Wallpaper Changer', _('Failed to save to favorites.'));
                }
            }
        );
    }

    _controlSystemdService(action) {
        const method = action === 'start' ? 'StartUnit' : 'StopUnit';
        Gio.DBus.session.call(
            'org.freedesktop.systemd1',
            '/org/freedesktop/systemd1',
            'org.freedesktop.systemd1.Manager',
            method,
            new GLib.Variant('(ss)', ['wallpaper-changer.service', 'replace']),
            new GLib.VariantType('(o)'),
            Gio.DBusCallFlags.NONE,
            -1,
            null,
            null
        );
    }

    destroy() {
        this._stopRotatorTimer();
        this._cancelActiveRotation();
        this.disconnectObject();

        this._settings?.disconnectObject(this);
        this._settings = null;
        this._bgSettings?.disconnectObject(this);
        this._bgSettings = null;

        super.destroy();
    }
}

export default class WchangerExtension extends Extension {
    enable() {
        this._settings = this.getSettings();
        this._indicator = null;

        this._settings.connectObject(
            'changed::show-indicator', () => this._syncIndicator(),
            this
        );

        this._syncIndicator();
    }

    _syncIndicator() {
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
        this._settings?.disconnectObject(this);
        this._settings = null;

        if (this._indicator) {
            this._indicator.destroy();
            this._indicator = null;
        }
    }
}
