import Adw from 'gi://Adw';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Gtk from 'gi://Gtk';
import { ExtensionPreferences, gettext as _ } from 'resource:///org/gnome/Shell/Extensions/js/extensions/prefs.js';

export default class WchangerPreferences extends ExtensionPreferences {
    fillPreferencesWindow(window) {
        const settings = this.getSettings('org.gnome.shell.extensions.wchanger');

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

        const showIndicatorRow = new Adw.SwitchRow({
            title: _('Show Indicator in Top Bar'),
            subtitle: _('Toggle visibility of the wallpaper rotator menu icon in the panel.'),
        });
        settings.bind('show-indicator', showIndicatorRow, 'active', Gio.SettingsBindFlags.DEFAULT);
        appearanceGroup.add(showIndicatorRow);

        const multiMonitorRow = new Adw.SwitchRow({
            title: _('Multi-Monitor Spanning'),
            subtitle: _('Pass -m to wchanger to assign different wallpapers across monitors.'),
        });
        settings.bind('enable-multi-monitor', multiMonitorRow, 'active', Gio.SettingsBindFlags.DEFAULT);
        appearanceGroup.add(multiMonitorRow);

        // Group 2: Favorites Storage
        const favoritesGroup = new Adw.PreferencesGroup({
            title: _('Favorites'),
            description: _('Manage where favorited wallpapers are stored.'),
        });
        page.add(favoritesGroup);

        const defaultFavDir = `${GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_PICTURES) || GLib.get_home_dir() + '/Pictures'}/Wallpapers/Favorites`;
        const currentFavDir = settings.get_string('favorites-directory') || defaultFavDir;

        const favoritesPathRow = new Adw.EntryRow({
            title: _('Favorites Folder Path'),
            text: currentFavDir,
            show_apply_button: true,
        });
        favoritesPathRow.connect('apply', (entry) => {
            const raw = entry.get_text().trim();
            settings.set_string('favorites-directory', raw.length > 0 ? raw : defaultFavDir);
        });
        favoritesGroup.add(favoritesPathRow);

        // Group 3: Online Providers
        const onlineGroup = new Adw.PreferencesGroup({
            title: _('Online Source'),
            description: _('Default provider when rotating online images.'),
        });
        page.add(onlineGroup);

        const providers = ['wallhaven', 'bing', 'picsum', 'loremflickr'];
        const providerNames = [_('Wallhaven (Toplist)'), _('Bing Daily Photo'), _('Lorem Picsum (Random)'), _('LoremFlickr (Nature)')];
        const stringList = Gtk.StringList.new(providerNames);

        const currentProvider = settings.get_string('default-provider') || 'wallhaven';
        let currentIndex = providers.indexOf(currentProvider);
        if (currentIndex < 0) {
            currentIndex = 0;
        }

        const providerRow = new Adw.ComboRow({
            title: _('Default Online Provider'),
            subtitle: _('Provider triggered when clicking Next Online in the panel menu.'),
            model: stringList,
            selected: currentIndex,
        });
        providerRow.connect('notify::selected', (widget) => {
            const selectedIdx = widget.selected;
            if (selectedIdx >= 0 && selectedIdx < providers.length) {
                settings.set_string('default-provider', providers[selectedIdx]);
            }
        });
        onlineGroup.add(providerRow);
    }
}
