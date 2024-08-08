# Github: https://github.com/ibehii
# Telegram: https://T.me/BZHNAM
# e-mail: behii@tutanota.com
# ____________________________________________

# Notice : This script only works on gnome and cinnamon

# ======== # import part # ======== #
from colorama import Fore, Style
import click
from PIL import Image
from time import sleep
from os import system, listdir , path
import platform
import subprocess
import logging
import sys

# ====== # logo # ====== #
logo: str = (Fore.YELLOW + ''' ██████╗██╗  ██╗ █████╗ ███╗   ██╗ ██████╗ ███████╗██████╗ 
██╔════╝██║  ██║██╔══██╗████╗  ██║██╔════╝ ██╔════╝██╔══██╗
██║     ███████║███████║██╔██╗ ██║██║  ███╗█████╗  ██████╔╝
██║     ██╔══██║██╔══██║██║╚██╗██║██║   ██║██╔══╝  ██╔══██╗
╚██████╗██║  ██║██║  ██║██║ ╚████║╚██████╔╝███████╗██║  ██║
 ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝'''+ Fore.MAGENTA + '\n- My telegram : t.me/BZHNAM -\n' + '- My github : https://github.com/ibehii -\n\n' + Fore.YELLOW + '------------ # v2.0.0 # ------------  \n' + Fore.RESET)

# ======== # checking for compatible operating system # ======== #
user_desktop: str = str(subprocess.check_output('echo $XDG_CURRENT_DESKTOP', shell=True), 'utf-8').replace('\n', '')
exit(Fore.RED + f'This script only works on linux distribution with {Style.BRIGHT} Gnome and Cinnamon' + Fore.RESET) if platform.platform().lower() == 'linux' and user_desktop.lower() in ['gnome', 'cinnamon'] else system('clear')

# ======= # setting up logger # ======== #
logging.basicConfig(level='INFO', format='%(asctime)s:%(levelname)s:%(message)s', filename='info.log')

def file_validator(photo_path) -> list[str]:
    '''Checking directory for valid image file'''
    valid_file: list = []
    
    for filename in listdir(photo_path):
        file_path = path.join(photo_path, filename)
        try:
            # ===== # checking image for broken byte or ... problem # ===== #
            Image.open(file_path).verify()
        except (OSError, IOError):
            continue
        else:
            valid_file.append(file_path)
    
    return valid_file

@click.group()             
def cli() -> None:
    ''' wchanger [gnome/cinnamon] --[option] [Path of the file with picture]\n
    Need help more? check https://github.com/ibehii/Wallpaper-Changer'''
    pass

@click.command()
@click.option('--pause', '-p', type=int ,required=True, prompt=f'{Fore.GREEN}[+] - Please set pause duration between changing wallpaper {Fore.RESET}', help="amount of secondes between changing wallpaper")
@click.option('--repetition/--no-repetition', is_flag=bool, default = True, show_default=True, help='By setting --no-repetition, program will exit after it set all wallpaper')
@click.option('--theme', '-t', type=click.Choice(['dark', 'light'], case_sensitive=False), default = None, help='By default the script will change the wallpaper in both dark and light theme.\nBy specify the theme changes will apply on specif theme')
@click.option('--output', '-o', type=click.Choice(['console', 'log'], case_sensitive=False), default='console', show_default=True, help='choosing output of program between showing on console or save into log file')
@click.argument('photo_path', type=click.Path(exists=True, file_okay=False, executable=False, dir_okay=True, resolve_path=True), default=path.join(sys.path[0], 'photos'))
def gnome(pause, photo_path, repetition, theme, output) -> None:
    '''Changes wallpaper on gnome'''
    print(logo)
    photos: list[str] = file_validator(photo_path)
    while True:
        for photo in photos: 
            if(theme != None):
                system(f'gsettings set org.gnome.desktop.background picture-uri-dark "file://{photo}"') if theme == 'dark' else system(f'gsettings set org.gnome.desktop.background picture-uri-dark "file://{photo}"')
                logging.info(f'Wallpaper changed on gnome to {photo} in {theme} theme.') if output == 'log' else print(Fore.MAGENTA + f'Wallpaper changed on gnome to {photo} in {theme} theme.' + Fore.RESET)
            else:
                system(f'gsettings set org.gnome.desktop.background picture-uri-dark "file://{photo}" && gsettings set org.gnome.desktop.background picture-uri-dark "file://{photo}"')
                logging.info(f'Wallpaper changed on gnome to {photo} in both dark and light theme.') if output == 'log' else print(Fore.MAGENTA + f'Wallpaper changed on gnome to {photo} in both dark and light theme.' + Fore.RESET)
            sleep(pause)
        else:
            logging.info('Program exited after setting all wallpaper ...') if output == 'log' else print(Fore.MAGENTA + f'Program exited after setting all wallpaper ...' + Fore.RESET)
            exit() if repetition == False else ...

@click.command()
@click.option('--pause', '-p', type=(int, float) ,required=True, prompt=f'{Fore.GREEN}[+] - Please set pause duration between changing wallpaper {Fore.RESET}', help="amount of secondes between changing wallpaper")
@click.option('--repetition', '-r', type=bool, is_flag=bool, default = True, show_default=True, help='By setting it false, program will exit after it set all wallpaper')
@click.option('--output', '-o', type=click.Choice(['console', 'log'], case_sensitive=False), default='console', show_default=True, help='choosing output of program between showing on console or save into log file')
@click.argument('photo_path', type=click.Path(exists=True, file_okay=False, executable=False, dir_okay=True, resolve_path=True), default=path.join(sys.path[0], 'photos'))
def cinnamon(pause, photo_path, repetition, output) -> None:
    '''Changes wallpaper on cinnamon'''
    print(logo)
    photos: list[str] = file_validator(photo_path)
    while True:
        for photo in photos:
            system(f'gsettings set org.cinnamon.desktop.background picture-uri  file://{photo}"')
            logging.info(f'Wallpaper changed on cinnamon to {photo}') if output == 'log' else print(Fore.MAGENTA + f'Wallpaper changed on cinnamon to {photo}' + Fore.RESET) 
            sleep(pause)
        else:
            logging.info('Program exited after setting all wallpaper ...') if output == 'log' else print(Fore.MAGENTA + f'Program exited after setting all wallpaper ...' + Fore.RESET)
            exit() if repetition == False else ...
            
# ======== # adding subcommand to cli# ======== #
cli.add_command(gnome)
cli.add_command(cinnamon)

if __name__ == '__main__':
    cli()
