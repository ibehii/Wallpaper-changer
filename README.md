Remember the text below:

# Awesome Wallpaper Changer 🖼️
![](https://skillicons.dev/icons?i=python,github,linux)

Do you have a list of wallpapers that you want to set as your wallpaper? With this CLI app, you can set them as your wallpaper with a custom pause duration.

https://user-images.githubusercontent.com/79264026/175102693-45906b72-f028-4bd0-8839-19421f9aa216.mp4

### ⚠️ This script only works on Linux distros that use gnome.

#### Simple Explanation
Give the path of a folder containing images, and the script sets all the images as the wallpaper with a pause between each one.

## Installation
1. Clone the repo:
   ```
   git clone https://raw.githubusercontent.com/ibehii/Wallpaper-Changer
   ```

2. Enter the directory:
   ```
   cd Wallpaper-Changer
   ```

3. Install requirements:
   ```
   pip install -r requirements.txt
   ```

You're done! ✅

## Execution
This program only works for Gnome and Cinnamon desktop environments.

To run the program without passing options:
- **Gnome**
  ```
  python wchanger.py gnome
  ```
- **Cinnamon**
  ```
  python wchanger.py cinnamon
  ```

## Options
Options are extra features that you can pass to the program.

**Pattern:**
```
wchanger [gnome/cinnamon] --[option] [Path of the file with picture]
```

| Option                | Accepted Value   | Usage                                                                 |
| --------------------- | ----------------- | --------------------------------------------------------------------- |
| `-p` or `--pause`     | numbers (INTEGER) | Amount of delay between changing wallpaper (seconds)                  |
| `--repetition / --no-repetition` | Nothing       | By setting `--no-repetition`, the program will exit after setting all wallpapers (default: repetition) |
| `-t` or `--theme`     | dark or light     | By default, the script changes the wallpaper in both dark and light themes. By specifying the theme, changes will only apply to that specific theme (only for Gnome) |
| `-o` or `--output`    | console or log    | Choose the output of the program between showing it on the console or saving it into a log file |
| `--help`              | Nothing           | Show the help message                                                  |

## Arguments
Be aware that options and arguments are different.

**Pattern:**
```
wchanger [gnome/cinnamon] --[option] [Path of the file with picture]
```

| Argument   | Accepted Value                           | Usage                                             |
| ---------- | ----------------------------------------- | -------------------------------------------------- |
| photo_path | A valid directory containing pictures     | Set the picture as the wallpaper                   |