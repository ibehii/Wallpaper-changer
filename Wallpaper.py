# Github: https://github.com/beh185
# Telegram: https://T.me/dr_xz
# e-mail: BehnamH.dev@gmail.com
# ____________________________________________

# Notice : This script work on gnome 

# After set all wallpaper, do you want to exit or start from the beginning?
# True = start from the beginning , False = exit after set all wallpaper
import colorama

Again = False

#import part
from time import sleep
from os import system, listdir, getcwd , path
from colorama import Fore
from pathlib import Path

# clear screen
system('clear')

# ask for wallpaper path
wallpapers_path = input(Fore.YELLOW + "Enter the complete path of folder [if you want to use defult folder just press \"enter\"] : "+ Fore.RESET)

# pause between changing wallpaper in "second"
pause = int(input(Fore.YELLOW + 'set pause time between changeing Wallpaper → '+ Fore.RESET))

def wallpaper_changer(user_path, pause):
    # get all file in directory
    directory_dir_unqualified = listdir(user_path)
    directory_dir = []
    # check if files are suiteable for wallpaper. JUST png, jpg, jpeg, tiff, tif, gif are allow
    for qualified_file in directory_dir_unqualified: 
        if( 'png' in qualified_file or 'jpg' in qualified_file or 'jpeg' in qualified_file  or 'tiff' in qualified_file or 'tif' in qualified_file or 'gif' in qualified_file):
            directory_dir.append(qualified_file)
        else:
            print(Fore.RED + '"' + qualified_file + '"' + ' isn\'t image' + Fore.RESET)
    
    while True:
        for wallpaper_name in directory_dir:
            print(Fore.LIGHTCYAN_EX + 'Wallpaper will change to : ',wallpaper_name + Fore.RESET)
            # Setting wallpaper by terminal
            system(
                f'gsettings set org.gnome.desktop.background picture-uri "file://{user_path}{wallpaper_name}" ')
            print(Fore.GREEN + '- Wallpaper change successfully !' + Fore.RESET)
            sleep(1.5)
            system('clear')
            # Pause between changing wallpaper
            for i in range(pause):
                print(Fore.YELLOW + f'Wallpaper will change in {pause-i} sec' + Fore.RESET)
                sleep(1)
                system('clear')
        # checking, if user want start from beginning or not
        if Again == False:
            print(Fore.GREEN + 'All image set as wallpaper !'  + Fore.RESET)
            break
        elif Again == True:
            print(Fore.RED + 'Starting from the beginning ...' + Fore.RESET)
            sleep(2)
        else:
            print(Fore.RED + 'Please set \"Again\" variable with \"True\" and \"False\" ' + Fore.RESET)
            break
    # just for return sth :)
    return 'Done !'
    


# if user choose defult folder
if wallpapers_path == "":
    directory_pwd = __file__
    currect_script_name = Path(__file__).stem + '.py'
    directory_pwd = directory_pwd.replace(currect_script_name, '')
    directory_pwd = directory_pwd + "/photos/"
    if not path.exists(directory_pwd):
        print(Fore.RED +"Error : There is no folder named \"photos\" in the current directory\nplease create one" + Fore.RESET)
    else:
        wallpaper_changer(directory_pwd, pause)

# if user give path
else:
    if not path.exists(wallpapers_path):
        print(Fore.RED +"Error : The folder \"{user_path}\" does not exist!\nplease enter complete path of the folder correctly".format(user_path = wallpapers_path) + Fore.RESET)
    else:
        if wallpapers_path.endswith('/'):
            wallpaper_changer(wallpapers_path, pause)
        else:
            wallpapers_path = wallpapers_path + '/'
            wallpaper_changer(wallpapers_path, pause)