import Adw from 'gi://Adw';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Gtk from 'gi://Gtk';
import { ExtensionPreferences, gettext as _ } from 'resource:///org/gnome/Shell/Extensions/js/extensions/prefs.js';

function openFolderChooser(window, title, currentPath, onSelected) {
    try {
        if (Gtk.FileDialog) {
            const dialog = new Gtk.FileDialog({ title });
            if (currentPath) {
                let expandedPath = currentPath;
                if (expandedPath.startsWith('~')) {
                    expandedPath = `${GLib.get_home_dir()}${expandedPath.substring(1)}`;
                }
                try {
                    const initialFile = Gio.File.new_for_path(expandedPath);
                    if (initialFile.query_exists(null)) {
                        dialog.set_initial_folder(initialFile);
                    }
                } catch (e) {
                    // Ignore initial folder resolution error
                }
            }
            dialog.select_folder(window, null, (dlg, res) => {
                try {
                    const folder = dlg.select_folder_finish(res);
                    if (folder) {
                        onSelected(folder.get_path());
                    }
                } catch (e) {
                    // User cancelled or dismissed dialog
                }
            });
        } else if (Gtk.FileChooserNative) {
            const chooser = new Gtk.FileChooserNative({
                title,
                transient_for: window,
                action: Gtk.FileChooserAction.SELECT_FOLDER,
                accept_label: (typeof _ === 'function') ? _('Select') : 'Select',
                cancel_label: (typeof _ === 'function') ? _('Cancel') : 'Cancel',
            });
            chooser.connect('response', (dlg, response) => {
                try {
                    if (response === Gtk.ResponseType.ACCEPT) {
                        const chosen = dlg.get_file();
                        if (chosen) {
                            onSelected(chosen.get_path());
                        }
                    }
                } finally {
                    chooser.destroy();
                }
            });
            chooser.show();
        }
    } catch (err) {
        logError(err, '[wchanger-prefs] Error opening folder chooser');
    }
}

export default class WchangerPreferences extends ExtensionPreferences {
    fillPreferencesWindow(window) {
        try {
            this.initTranslations();
        } catch (e) {}

        const settings = this.getSettings('org.gnome.shell.extensions.wchanger');
        const hasKey = (key) => {
            try {
                return Boolean(settings?.settings_schema?.has_key(key));
            } catch (e) {
                return false;
            }
        };

        const page = new Adw.PreferencesPage({
            title: _('General'),
            icon_name: 'preferences-desktop-wallpaper-symbolic',
        });
        window.add(page);

        // Group 1: Appearance & Visibility
        const appearanceGroup = new Adw.PreferencesGroup({
            title: _('Appearance'),
            description: _('Configure panel icon and indicators in the GNOME top bar.'),
        });
        page.add(appearanceGroup);

        if (hasKey('show-indicator')) {
            const showIndicatorRow = new Adw.SwitchRow({
                title: _('Show Indicator in Top Bar'),
                subtitle: _('Toggle visibility of the wallpaper rotator menu icon in the panel.'),
            });
            settings.bind('show-indicator', showIndicatorRow, 'active', Gio.SettingsBindFlags.DEFAULT);
            appearanceGroup.add(showIndicatorRow);
        }

        if (hasKey('enable-multi-monitor')) {
            const multiMonitorRow = new Adw.SwitchRow({
                title: _('Multi-Monitor Spanning'),
                subtitle: _('Pass -m to wchanger to assign different wallpapers across monitors.'),
            });
            settings.bind('enable-multi-monitor', multiMonitorRow, 'active', Gio.SettingsBindFlags.DEFAULT);
            appearanceGroup.add(multiMonitorRow);
        }

        // Group 2: Favorites Storage
        const favoritesGroup = new Adw.PreferencesGroup({
            title: _('Favorites'),
            description: _('Manage where favorited wallpapers are stored.'),
        });
        page.add(favoritesGroup);

        const defaultFavDir = `${GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_PICTURES) || GLib.get_home_dir() + '/Pictures'}/Wallpapers/Favorites`;
        const currentFavDir = (hasKey('favorites-directory') ? settings.get_string('favorites-directory') : '') || defaultFavDir;

        const favoritesPathRow = new Adw.EntryRow({
            title: _('Favorites Folder Path'),
            text: currentFavDir,
            show_apply_button: true,
        });
        favoritesPathRow.connect('apply', (entry) => {
            const raw = entry.get_text().trim();
            if (hasKey('favorites-directory')) {
                settings.set_string('favorites-directory', raw.length > 0 ? raw : defaultFavDir);
            }
        });

        const browseFavsBtn = new Gtk.Button({
            icon_name: 'folder-open-symbolic',
            valign: Gtk.Align.CENTER,
            has_frame: false,
            tooltip_text: _('Browse for folder'),
        });
        browseFavsBtn.connect('clicked', () => {
            const cur = (hasKey('favorites-directory') ? settings.get_string('favorites-directory') : '') || defaultFavDir;
            openFolderChooser(window, _('Select Favorites Folder'), cur, (chosenPath) => {
                favoritesPathRow.set_text(chosenPath);
                if (hasKey('favorites-directory')) {
                    settings.set_string('favorites-directory', chosenPath);
                }
            });
        });
        favoritesPathRow.add_suffix(browseFavsBtn);
        favoritesGroup.add(favoritesPathRow);

        // Group 3: Local Photos
        const localPhotosGroup = new Adw.PreferencesGroup({
            title: _('Local Photos'),
            description: _('Rotate wallpapers from a folder on your computer.'),
        });
        page.add(localPhotosGroup);

        const defaultWallDir = `${GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_PICTURES) || GLib.get_home_dir() + '/Pictures'}/Wallpapers`;
        const currentWallDir = (hasKey('wallpapers-directory') ? settings.get_string('wallpapers-directory') : '') || defaultWallDir;

        const wallpapersPathRow = new Adw.EntryRow({
            title: _('Local Photos Folder'),
            text: currentWallDir,
            show_apply_button: true,
        });
        wallpapersPathRow.connect('apply', (entry) => {
            const raw = entry.get_text().trim();
            if (hasKey('wallpapers-directory')) {
                settings.set_string('wallpapers-directory', raw.length > 0 ? raw : defaultWallDir);
            }
        });

        const browseWallpapersBtn = new Gtk.Button({
            icon_name: 'folder-open-symbolic',
            valign: Gtk.Align.CENTER,
            has_frame: false,
            tooltip_text: _('Browse for folder'),
        });
        browseWallpapersBtn.connect('clicked', () => {
            const cur = (hasKey('wallpapers-directory') ? settings.get_string('wallpapers-directory') : '') || defaultWallDir;
            openFolderChooser(window, _('Select Local Photos Folder'), cur, (chosenPath) => {
                wallpapersPathRow.set_text(chosenPath);
                if (hasKey('wallpapers-directory')) {
                    settings.set_string('wallpapers-directory', chosenPath);
                }
            });
        });
        wallpapersPathRow.add_suffix(browseWallpapersBtn);
        localPhotosGroup.add(wallpapersPathRow);

        // Wallpaper Source selector (local vs online)
        if (hasKey('wallpaper-source')) {
            const sourceChoices = ['local', 'online'];
            const sourceNames = [_('Local Folder'), _('Online Provider')];
            const sourceStringList = Gtk.StringList.new(sourceNames);

            const currentSource = settings.get_string('wallpaper-source') || 'local';
            let currentSourceIndex = sourceChoices.indexOf(currentSource);
            if (currentSourceIndex < 0) {
                currentSourceIndex = 0;
            }

            const sourceRow = new Adw.ComboRow({
                title: _('Wallpaper Source'),
                subtitle: _('Choose whether the Background Rotator uses local photos or an online provider.'),
                model: sourceStringList,
                selected: currentSourceIndex,
            });
            sourceRow.connect('notify::selected', (widget) => {
                const selectedIdx = widget.selected;
                if (selectedIdx >= 0 && selectedIdx < sourceChoices.length) {
                    settings.set_string('wallpaper-source', sourceChoices[selectedIdx]);
                }
            });
            localPhotosGroup.add(sourceRow);
        }

        if (hasKey('recursive-scan')) {
            const recursiveRow = new Adw.SwitchRow({
                title: _('Scan Subfolders'),
                subtitle: _('Search for images recursively in subdirectories of the local photos folder.'),
            });
            settings.bind('recursive-scan', recursiveRow, 'active', Gio.SettingsBindFlags.DEFAULT);
            localPhotosGroup.add(recursiveRow);
        }

        // Group 4: Online Providers
        const onlineGroup = new Adw.PreferencesGroup({
            title: _('Online Source'),
            description: _('Default provider and category when rotating online images.'),
        });
        page.add(onlineGroup);

        const providers = ['wallhaven', 'bing', 'picsum', 'loremflickr'];
        const providerNames = [_('Wallhaven'), _('Bing Daily Photo'), _('Lorem Picsum (Random)'), _('LoremFlickr (Nature)')];
        const stringList = Gtk.StringList.new(providerNames);

        const currentProvider = (hasKey('default-provider') ? settings.get_string('default-provider') : '') || 'wallhaven';
        let currentIndex = providers.indexOf(currentProvider);
        if (currentIndex < 0) {
            currentIndex = 0;
        }

        const providerRow = new Adw.ComboRow({
            title: _('Default Online Provider'),
            subtitle: _('Online provider used for wallpaper rotation.'),
            model: stringList,
            selected: currentIndex,
        });

        // Wallhaven Categories
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
        const catNames = wallhavenCategories.map(c => c.name);
        const catStringList = Gtk.StringList.new(catNames);

        let categoryRow = null;
        let customCatRow = null;

        if (hasKey('wallhaven-category')) {
            const currentCategory = settings.get_string('wallhaven-category') || 'nature';
            let currentCatIndex = wallhavenCategories.findIndex(c => c.id === currentCategory);
            if (currentCatIndex < 0) {
                currentCatIndex = 0;
            }

            categoryRow = new Adw.ComboRow({
                title: _('Wallhaven Category'),
                subtitle: _('Select image category or theme when Wallhaven is used.'),
                model: catStringList,
                selected: currentCatIndex,
            });

            customCatRow = new Adw.EntryRow({
                title: _('Custom Wallhaven Tag / Keyword'),
                text: currentCategory,
                show_apply_button: true,
            });

            let updatingCategory = false;
            categoryRow.connect('notify::selected', (widget) => {
                if (updatingCategory) return;
                const selectedIdx = widget.selected;
                if (selectedIdx >= 0 && selectedIdx < wallhavenCategories.length) {
                    const chosenCat = wallhavenCategories[selectedIdx].id;
                    updatingCategory = true;
                    settings.set_string('wallhaven-category', chosenCat);
                    customCatRow.set_text(chosenCat);
                    updatingCategory = false;
                }
            });

            customCatRow.connect('apply', (entry) => {
                if (updatingCategory) return;
                const val = entry.get_text().trim().toLowerCase();
                if (val.length > 0) {
                    updatingCategory = true;
                    settings.set_string('wallhaven-category', val);
                    const idx = wallhavenCategories.findIndex(c => c.id === val);
                    if (idx >= 0) {
                        categoryRow.set_selected(idx);
                    }
                    updatingCategory = false;
                }
            });

            settings.connect('changed::wallhaven-category', () => {
                if (updatingCategory) return;
                updatingCategory = true;
                const newCat = settings.get_string('wallhaven-category') || 'nature';
                customCatRow.set_text(newCat);
                const idx = wallhavenCategories.findIndex(c => c.id === newCat);
                if (idx >= 0) {
                    categoryRow.set_selected(idx);
                }
                updatingCategory = false;
            });
        }

        const updateWallhavenSensitivity = (provider) => {
            const isWallhaven = (provider === 'wallhaven');
            if (categoryRow) categoryRow.set_sensitive(isWallhaven);
            if (customCatRow) customCatRow.set_sensitive(isWallhaven);
        };
        updateWallhavenSensitivity(currentProvider);

        providerRow.connect('notify::selected', (widget) => {
            const selectedIdx = widget.selected;
            if (selectedIdx >= 0 && selectedIdx < providers.length) {
                const prov = providers[selectedIdx];
                if (hasKey('default-provider')) {
                    settings.set_string('default-provider', prov);
                }
                updateWallhavenSensitivity(prov);
            }
        });

        onlineGroup.add(providerRow);
        if (categoryRow) onlineGroup.add(categoryRow);
        if (customCatRow) onlineGroup.add(customCatRow);

        // Group 5: Automatic Background Rotator
        const rotatorGroup = new Adw.PreferencesGroup({
            title: _('Background Rotator'),
            description: _('Configure periodic automatic wallpaper changes.'),
        });
        page.add(rotatorGroup);

        if (hasKey('rotator-enabled')) {
            const rotatorEnabledRow = new Adw.SwitchRow({
                title: _('Enable Background Rotator'),
                subtitle: _('Rotate wallpapers automatically at the configured time interval.'),
            });
            settings.bind('rotator-enabled', rotatorEnabledRow, 'active', Gio.SettingsBindFlags.DEFAULT);
            rotatorGroup.add(rotatorEnabledRow);
        }

        if (hasKey('rotation-interval')) {
            const currentIntervalSec = settings.get_int('rotation-interval') || 300;
            const currentIntervalMin = Math.max(1, Math.round(currentIntervalSec / 60));
            const intervalAdjustment = new Gtk.Adjustment({
                lower: 1,
                upper: 1440,
                step_increment: 1,
                page_increment: 5,
                value: currentIntervalMin,
            });

            const intervalRow = new Adw.SpinRow({
                title: _('Rotation Interval (minutes)'),
                subtitle: _('Time in minutes between automatic rotations (default: 5 min).'),
                adjustment: intervalAdjustment,
            });
            intervalRow.connect('notify::value', (widget) => {
                const minutes = Math.max(1, Math.round(widget.get_value()));
                settings.set_int('rotation-interval', minutes * 60);
            });
            rotatorGroup.add(intervalRow);
        }

        // Group 6: Advanced & Execution Paths
        const advancedGroup = new Adw.PreferencesGroup({
            title: _('Advanced'),
            description: _('Executable resolution and custom CLI overrides.'),
        });
        page.add(advancedGroup);

        if (hasKey('custom-wchanger-path')) {
            const currentCustomPath = settings.get_string('custom-wchanger-path') || '';
            const customPathRow = new Adw.EntryRow({
                title: _('Custom wchanger Executable Path'),
                text: currentCustomPath,
                show_apply_button: true,
            });
            customPathRow.connect('apply', (entry) => {
                const raw = entry.get_text().trim();
                settings.set_string('custom-wchanger-path', raw);
            });
            advancedGroup.add(customPathRow);
        }
    }
}
