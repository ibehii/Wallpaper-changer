# Awesome wallpaper changer 🖼️
![](https://skillicons.dev/icons?i=python,github,linux)
### Do you have a list wallpaper that you want to set them as your wallpaper?
**With this cli app you can set them as your wallpaper with custom pause duration**

https://user-images.githubusercontent.com/79264026/175102693-45906b72-f028-4bd0-8839-19421f9aa216.mp4

### ***⚠️ This script just work on linux distro that use gnome***

Simple explanation: You give the path of one folder that contains images in it, and the script sets all images as wallpaper with pause between it.

---

# installation
**1 - Clone the repo**
> git clone https://raw.githubusercontent.com/ibehii/Wallpaper-Changer

**2 - enter to directory**
> cd Wallpaper-Changer

**3 - install requirements**
> pip install -r requirements.txt

Your are done ✅

-----
## Execution
As you already know this program only works for gnome and cinnamon.

the simple way to run the program without passing [options](#options) is:\
**Gnome**
> python wchanger.py gnome

**cinnamon**
> python wchanger.py cinnamon

---
## options
options are extra features that you can pass to program.

**The pattern is like:**
> wchanger [gnome/cinnamon] --[option] [Path of the file with picture]

| options| accepted value | usage |
| --- | ---- |---- | 
| `-p` or `--pause`| **numbers(INTEGER)** | amount of delay between changing wallpaper (second)
| ```--repetition / --no-repetition``` | **Nothing** | By setting --no-repetition, program will exit after it set all wallpaper  [default:repetition]
| `-t` or ```--theme``` | **dark** or **light** | By default the script will change the wallpaper in both dark and light theme. By specify the theme changes will apply on specif theme (**Only for gnome**)
| `-o` or `--output` |  **console** or **log**  | choosing output of program between showing on the console or save them into log file 
| `--help`| Nothing | Show help message


## Arguments
Be aware that options and arguments are different\
**The pattern is like:**
> wchanger [gnome/cinnamon] --[option] [Path of the file with picture]
___ 
| Arguments| accepted value |usage |
| --- | ---- |---- | 
| photo_path | a valid directory with picture on it | set the picture inside it as wallpaper