import Adw from 'gi://Adw';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Gtk from 'gi://Gtk';
import { ExtensionPreferences, gettext as _ } from 'resource:///org/gnome/Shell/Extensions/js/extensions/prefs.js';

function openFolderChooser(window, title, currentPath, onSelected) {
    const dialog = new Gtk.FileDialog({ title });
    if (currentPath) {
        const path = currentPath.replace(/^~/, GLib.get_home_dir());
        const file = Gio.File.new_for_path(path);
        if (file.query_exists(null))
            dialog.set_initial_folder(file);
    }
    dialog.select_folder(window, null, (dialogObj, res) => {
        try {
            const folder = dialogObj.select_folder_finish(res);
            if (folder)
                onSelected(folder.get_path());
        } catch (e) {
            if (!e.matches(Gio.IOErrorEnum, Gio.IOErrorEnum.CANCELLED))
                throw e;
        }
    });
}

function bindCombo(row, settings, key, choices) {
    row.selected = Math.max(0, choices.indexOf(settings.get_string(key)));
    row.connect('notify::selected', () => {
        const val = choices[row.selected];
        if (val && settings.get_string(key) !== val)
            settings.set_string(key, val);
    });
    settings.connect(`changed::${key}`, () => {
        const current = settings.get_string(key);
        const idx = choices.indexOf(current);
        if (idx >= 0 && row.selected !== idx)
            row.selected = idx;
    });
}

function addCategoryRows(settings, key, title, subtitle, customTitle, categories) {
    const current = settings.get_string(key) || 'nature';
    const comboRow = new Adw.ComboRow({
        title,
        subtitle,
        model: Gtk.StringList.new(categories.map(c => c.name)),
        selected: Math.max(0, categories.findIndex(c => c.id === current)),
    });

    const customRow = new Adw.EntryRow({
        title: customTitle,
        text: current,
        show_apply_button: true,
    });

    comboRow.connect('notify::selected', () => {
        const chosen = categories[comboRow.selected]?.id;
        if (chosen && settings.get_string(key) !== chosen) {
            settings.set_string(key, chosen);
            customRow.set_text(chosen);
        }
    });

    customRow.connect('apply', () => {
        const val = customRow.get_text().trim().toLowerCase();
        if (val && settings.get_string(key) !== val) {
            settings.set_string(key, val);
            const idx = categories.findIndex(c => c.id === val);
            if (idx >= 0)
                comboRow.set_selected(idx);
        }
    });

    settings.connect(`changed::${key}`, () => {
        const cat = settings.get_string(key) || 'nature';
        if (customRow.get_text() !== cat)
            customRow.set_text(cat);
        const idx = categories.findIndex(c => c.id === cat);
        if (idx >= 0 && comboRow.selected !== idx)
            comboRow.selected = idx;
    });

    return [comboRow, customRow];
}

export default class WchangerPreferences extends ExtensionPreferences {
    fillPreferencesWindow(window) {
        const settings = this.getSettings();

        const page = new Adw.PreferencesPage({
            title: _('General'),
            icon_name: 'preferences-desktop-wallpaper-symbolic',
        });
        window.add(page);

        const appearanceGroup = new Adw.PreferencesGroup({
            title: _('Appearance'),
            description: _('Configure panel icon and indicators in the GNOME top bar.'),
        });
        page.add(appearanceGroup);

        const showIndicatorRow = new Adw.SwitchRow({
            title: _('Show Indicator in Top Bar'),
            subtitle: _('Toggle visibility of the wallpaper rotator menu icon in the panel.'),
        });
        settings.bind('show-indicator', showIndicatorRow, 'active', Gio.SettingsBindFlags.DEFAULT);
        appearanceGroup.add(showIndicatorRow);

        const multiMonitorRow = new Adw.SwitchRow({
            title: _('Multi-Monitor Spanning'),
            subtitle: _('Assign different wallpapers across connected monitors.'),
        });
        settings.bind('enable-multi-monitor', multiMonitorRow, 'active', Gio.SettingsBindFlags.DEFAULT);
        appearanceGroup.add(multiMonitorRow);

        const favoritesGroup = new Adw.PreferencesGroup({
            title: _('Favorites'),
            description: _('Manage where favorited wallpapers are stored.'),
        });
        page.add(favoritesGroup);

        const defaultFavDir = `${GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_PICTURES) || `${GLib.get_home_dir()}/Pictures`}/Wallpapers/Favorites`;
        const favoritesPathRow = new Adw.EntryRow({
            title: _('Favorites Folder Path'),
            text: settings.get_string('favorites-directory') || defaultFavDir,
            show_apply_button: true,
        });
        favoritesPathRow.connect('apply', () => {
            const raw = favoritesPathRow.get_text().trim();
            settings.set_string('favorites-directory', raw || defaultFavDir);
        });

        const browseFavsBtn = new Gtk.Button({
            icon_name: 'folder-open-symbolic',
            valign: Gtk.Align.CENTER,
            has_frame: false,
            tooltip_text: _('Browse for folder'),
        });
        browseFavsBtn.connect('clicked', () => {
            const current = settings.get_string('favorites-directory') || defaultFavDir;
            openFolderChooser(window, _('Select Favorites Folder'), current, chosen => {
                favoritesPathRow.set_text(chosen);
                settings.set_string('favorites-directory', chosen);
            });
        });
        favoritesPathRow.add_suffix(browseFavsBtn);
        favoritesGroup.add(favoritesPathRow);

        const localPhotosGroup = new Adw.PreferencesGroup({
            title: _('Local Photos'),
            description: _('Rotate wallpapers from a folder on your computer.'),
        });
        page.add(localPhotosGroup);

        const defaultWallDir = `${GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_PICTURES) || `${GLib.get_home_dir()}/Pictures`}/Wallpapers`;
        const wallpapersPathRow = new Adw.EntryRow({
            title: _('Local Photos Folder'),
            text: settings.get_string('wallpapers-directory') || defaultWallDir,
            show_apply_button: true,
        });
        wallpapersPathRow.connect('apply', () => {
            const raw = wallpapersPathRow.get_text().trim();
            settings.set_string('wallpapers-directory', raw || defaultWallDir);
        });

        const browseWallpapersBtn = new Gtk.Button({
            icon_name: 'folder-open-symbolic',
            valign: Gtk.Align.CENTER,
            has_frame: false,
            tooltip_text: _('Browse for folder'),
        });
        browseWallpapersBtn.connect('clicked', () => {
            const current = settings.get_string('wallpapers-directory') || defaultWallDir;
            openFolderChooser(window, _('Select Local Photos Folder'), current, chosen => {
                wallpapersPathRow.set_text(chosen);
                settings.set_string('wallpapers-directory', chosen);
            });
        });
        wallpapersPathRow.add_suffix(browseWallpapersBtn);
        localPhotosGroup.add(wallpapersPathRow);

        const sourceChoices = ['local', 'online'];
        const sourceRow = new Adw.ComboRow({
            title: _('Wallpaper Source'),
            subtitle: _('Choose whether the Background Rotator uses local photos or an online provider.'),
            model: Gtk.StringList.new([_('Local Folder'), _('Online Provider')]),
        });
        bindCombo(sourceRow, settings, 'wallpaper-source', sourceChoices);
        localPhotosGroup.add(sourceRow);

        const recursiveRow = new Adw.SwitchRow({
            title: _('Scan Subfolders'),
            subtitle: _('Search for images recursively in subdirectories of the local photos folder.'),
        });
        settings.bind('recursive-scan', recursiveRow, 'active', Gio.SettingsBindFlags.DEFAULT);
        localPhotosGroup.add(recursiveRow);

        const onlineGroup = new Adw.PreferencesGroup({
            title: _('Online Source'),
            description: _('Default provider and category when rotating online images.'),
        });
        page.add(onlineGroup);

        const providers = ['wallhaven', 'unsplash', 'bing', 'picsum', 'loremflickr'];
        const providerNames = [_('Wallhaven'), _('Unsplash (API Key Required)'), _('Bing Daily Photo'), _('Lorem Picsum (Random)'), _('LoremFlickr (Nature)')];
        const providerRow = new Adw.ComboRow({
            title: _('Default Online Provider'),
            subtitle: _('Online provider used for wallpaper rotation.'),
            model: Gtk.StringList.new(providerNames),
        });
        bindCombo(providerRow, settings, 'default-provider', providers);

        const wallhavenCategories = [
            { id: 'nature', name: _('Nature & Landscapes') },
            { id: 'space', name: _('Space & Astronomy') },
            { id: 'anime', name: _('Anime Artwork') },
            { id: 'cyberpunk', name: _('Cyberpunk & Sci-Fi') },
            { id: 'city', name: _('City & Architecture') },
            { id: 'cars', name: _('Cars & Vehicles') },
            { id: 'gaming', name: _('Gaming & Fantasy') },
            { id: 'minimalism', name: _('Minimalism') },
            { id: 'general', name: _('General Photography') },
            { id: 'all', name: _('All (Random)') },
        ];
        const [categoryRow, customCatRow] = addCategoryRows(
            settings,
            'wallhaven-category',
            _('Wallhaven Category'),
            _('Select image category or theme when Wallhaven is used.'),
            _('Custom Wallhaven Tag / Keyword'),
            wallhavenCategories
        );

        const unsplashKeyRow = new Adw.PasswordEntryRow({
            title: _('Unsplash Access Key'),
        });
        settings.bind('unsplash-access-key', unsplashKeyRow, 'text', Gio.SettingsBindFlags.DEFAULT);

        const unsplashGuideRow = new Adw.ActionRow({
            title: _('Unsplash Setup & API Key Guide'),
            subtitle: _('Click to view the tutorial in README.md on getting a free API key.'),
            activatable: true,
        });
        const openGuide = () => {
            Gio.AppInfo.launch_default_for_uri('https://github.com/ibehii/Wallpaper-changer#unsplash-setup-guide', null);
        };
        const openGuideButton = new Gtk.Button({
            icon_name: 'emblem-default-symbolic',
            valign: Gtk.Align.CENTER,
            tooltip_text: _('Open tutorial in browser'),
        });
        openGuideButton.connect('clicked', openGuide);
        unsplashGuideRow.add_suffix(openGuideButton);
        unsplashGuideRow.connect('activated', openGuide);

        const unsplashCategories = [
            { id: 'nature', name: _('Nature & Landscapes') },
            { id: 'wallpapers', name: _('Desktop Wallpapers') },
            { id: 'travel', name: _('Travel & Exploration') },
            { id: 'architecture', name: _('Architecture & Interiors') },
            { id: 'space', name: _('Space & Astronomy') },
            { id: 'minimalism', name: _('Minimalism') },
            { id: 'animals', name: _('Animals & Wildlife') },
            { id: 'textures', name: _('Textures & Patterns') },
            { id: 'city', name: _('Street & City') },
            { id: 'technology', name: _('Technology & Cyber') },
            { id: 'all', name: _('All (Random)') },
        ];
        const [unsplashCategoryRow, unsplashCustomCatRow] = addCategoryRows(
            settings,
            'unsplash-category',
            _('Unsplash Category'),
            _('Select curated photo category or theme when Unsplash is used.'),
            _('Custom Unsplash Search Query'),
            unsplashCategories
        );

        const updateProviderSensitivity = provider => {
            const isWallhaven = provider === 'wallhaven';
            categoryRow.set_visible(isWallhaven);
            customCatRow.set_visible(isWallhaven);

            const isUnsplash = provider === 'unsplash';
            unsplashKeyRow.set_visible(isUnsplash);
            unsplashGuideRow.set_visible(isUnsplash);
            unsplashCategoryRow.set_visible(isUnsplash);
            unsplashCustomCatRow.set_visible(isUnsplash);
        };
        updateProviderSensitivity(settings.get_string('default-provider'));

        providerRow.connect('notify::selected', () => {
            const prov = providers[providerRow.selected];
            if (prov)
                updateProviderSensitivity(prov);
        });

        settings.connect('changed::default-provider', () => {
            updateProviderSensitivity(settings.get_string('default-provider'));
        });

        onlineGroup.add(providerRow);
        onlineGroup.add(categoryRow);
        onlineGroup.add(customCatRow);
        onlineGroup.add(unsplashKeyRow);
        onlineGroup.add(unsplashGuideRow);
        onlineGroup.add(unsplashCategoryRow);
        onlineGroup.add(unsplashCustomCatRow);

        const rotatorGroup = new Adw.PreferencesGroup({
            title: _('Background Rotator'),
            description: _('Configure periodic automatic wallpaper changes.'),
        });
        page.add(rotatorGroup);

        const rotatorEnabledRow = new Adw.SwitchRow({
            title: _('Enable Background Rotator'),
            subtitle: _('Rotate wallpapers automatically at the configured time interval.'),
        });
        settings.bind('rotator-enabled', rotatorEnabledRow, 'active', Gio.SettingsBindFlags.DEFAULT);
        rotatorGroup.add(rotatorEnabledRow);

        const currentIntervalSec = settings.get_int('rotation-interval');
        const intervalAdjustment = new Gtk.Adjustment({
            lower: 1,
            upper: 1440,
            step_increment: 1,
            page_increment: 5,
            value: Math.max(1, Math.round(currentIntervalSec / 60)),
        });

        const intervalRow = new Adw.SpinRow({
            title: _('Rotation Interval (minutes)'),
            subtitle: _('Time in minutes between automatic rotations (default: 5 min).'),
            adjustment: intervalAdjustment,
        });
        intervalRow.connect('notify::value', () => {
            const minutes = Math.max(1, Math.round(intervalRow.get_value()));
            settings.set_int('rotation-interval', minutes * 60);
        });
        rotatorGroup.add(intervalRow);
    }
}
