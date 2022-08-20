# Github: https://github.com/beh185
# Telegram: https://T.me/dr_xz
# e-mail: BehnamH.dev@gmail.com
# ____________________________________________

# Notice : This script work on gnome and cinnamon

# After set all wallpaper, do you want to exit or start from the beginning?
# True = start from the beginning , False = exit after set all wallpaper
Again = False

# Set this "True" if you are using dark-theme
dark_theme = True

#import part
from time import sleep
from os import system, listdir, getcwd , path
from pathlib import Path
import platform
import subprocess

class colors:
    red = '\033[31m'
    green = '\033[32m'
    purple = '\033[35m'
    cyan = '\033[36m'
    yellow = '\033[93m'
    lightblue = '\033[94m'
    reset = '\033[0m'


# what de user is using
user_de = subprocess.check_output('echo $XDG_CURRENT_DESKTOP', shell=True)
user_de = str(user_de, 'UTF-8').replace('\n', '')

# check if user is using gnome or cinnamon
if (user_de == 'GNOME' or user_de == 'CINNAMON'):
    # clear screen
    system('clear')
else:
    exit(colors.red +f'This script is not support in {user_de}. Use gnome or cinnamon‌ !' + colors.reset )
# ask for wallpaper path
wallpapers_path = input(colors.yellow + "Enter the complete path of folder with picture [if you want to use default folder just press \"enter\"] : " + colors.reset) 

# pause between changing wallpaper in "second"
pause = int(input(colors.yellow + 'set pause time between changing Wallpaper → '+ colors.reset ))

def wallpaper_changer(user_path, pause):
    # get all file in directory
    directory_dir_unqualified = listdir(user_path)
    directory_dir = []
    # check if files are suitable for wallpaper. JUST png, jpg, jpeg, tiff, tif, gif, svg are allow
    for qualified_file in directory_dir_unqualified: 
        if( 'png' in qualified_file or 'jpg' in qualified_file or 'jpeg' in qualified_file  or 'tiff' in qualified_file or 'tif' in qualified_file or 'gif' in qualified_file or 'svg' in qualified_file ):
            directory_dir.append(qualified_file)
        else:
            print(colors.red + '"' + qualified_file + '"' + ' isn\'t image' + colors.reset)
    
    while True:
        for wallpaper_name in directory_dir:
            print(colors.lightblue + 'Wallpaper will change to : ',wallpaper_name + colors.reset)
            # Setting wallpaper for gnome
            if (user_de == 'GNOME'):
                if(dark_theme == False):
                    system(
                        f'gsettings set org.gnome.desktop.background picture-uri "file://{user_path}{wallpaper_name}" ')
            
                elif(dark_theme == True):
                    system(
                        f'gsettings set org.gnome.desktop.background picture-uri-dark "file://{user_path}{wallpaper_name}" ')
                else:
                    print(colors.red+ 'Please set \"dark_theme\" variable with \"True\" and \"False\" ' + colors.reset)
                    break
            elif(user_de == 'CINNAMON'):
                system(f'gsettings set org.cinnamon.desktop.background picture-uri  file://{user_path}{wallpaper_name}"')
            print(colors.green + '- Wallpaper change successfully !' + colors.reset)
            sleep(1.5)
            system('clear')
            # Pause between changing wallpaper
            for i in range(pause):
                print(colors.green + f'Wallpaper will change in {pause-i} sec' + colors.reset)
                sleep(1)
                system('clear')
        # checking, if user want start from beginning or not
        if Again == False:
            print(colors.green+ 'All image set as wallpaper !'  + colors.reset)
            break
        elif Again == True:
            print(colors.red + 'Starting from the beginning ...' + colors.reset)
            sleep(2)
        else:
            print(colors.red + 'Please set \"Again\" variable with \"True\" and \"False\" ' + colors.reset)
            break
    # just for return sth :)
    return 'Done !'
    


# if user choose default folder
if wallpapers_path == "":
    directory_pwd = __file__
    current_script_name = Path(__file__).stem + '.py'
    directory_pwd = directory_pwd.replace(current_script_name, '')
    directory_pwd = directory_pwd + "/photos/"
    if not path.exists(directory_pwd):
        print(colors.red +"Error : There is no folder named \"photos\" in the current directory\nplease create one" + colors.reset)
    else:
        wallpaper_changer(directory_pwd, pause)

# if user give path
else:
    if not path.exists(wallpapers_path):
        print(colors.red +"Error : The folder \"{user_path}\" does not exist!\nplease enter complete path of the folder correctly".format(user_path = wallpapers_path) + colors.reset)
    else:
        if wallpapers_path.endswith('/'):
            wallpaper_changer(wallpapers_path, pause)
        else:
            wallpapers_path = wallpapers_path + '/'
            wallpaper_changer(wallpapers_path, pause)