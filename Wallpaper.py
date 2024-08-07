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
from os import system, listdir, getcwd , path
from pathlib import Path
import platform
import subprocess

# ======== # checking for compatible operating system # ======== #
user_desktop: str = str(subprocess.check_output('echo $XDG_CURRENT_DESKTOP', shell=True), 'utf-8').replace('\n', '')
exit(Fore.RED + f'This script only works on linux distribution with {Style.BRIGHT} Gnome and Cinnamon' + Fore.RESET) if platform.platform().lower() == 'linux' and user_desktop.lower() in ['gnome', 'cinnamon'] else system('clear')

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
def cli():
    pass

@click.command()
@click.option('--pause', '-p', type=int ,required=True, prompt=f'{Fore.GREEN}[+] - Please set pause duration between changing wallpaper {Fore.RESET}', help="amount of secondes between changing wallpaper")
@click.option('--repetition', '-r', type=bool, is_flag=bool, default = True, show_default=True, help='By setting it false, program will exit after it set all wallpaper')
@click.option('--theme', '-t', type=click.Choice(['dark', 'light'], case_sensitive=False), default = None, help='By default the script will change the wallpaper in both dark and light theme.\nBy specify the theme changes will apply on specif theme')
@click.argument('photo_path', type=click.Path(exists=True, file_okay=False, executable=False, dir_okay=True, resolve_path=True))
def gnome(pause, photo_path, repetition, theme) -> None:
    '''Changes wallpaper on gnome'''
    photos: list[str] = file_validator(photo_path)
    while True:
        for photo in photos: 
            if(theme != None):
                system(f'gsettings set org.gnome.desktop.background picture-uri-dark "file://{photo}"') if theme == 'dark' else system(f'gsettings set org.gnome.desktop.background picture-uri-dark "file://{photo}"')
            else:
                system(f'gsettings set org.gnome.desktop.background picture-uri-dark "file://{photo}" && gsettings set org.gnome.desktop.background picture-uri-dark "file://{photo}"')
            sleep(pause)
        else:
            exit() if repetition == False else ...

@click.command()
@click.option('--pause', '-p', type=(int, float) ,required=True, prompt=f'{Fore.GREEN}[+] - Please set pause duration between changing wallpaper {Fore.RESET}', help="amount of secondes between changing wallpaper")
@click.option('--repetition', '-r', type=bool, is_flag=bool, default = True, show_default=True, help='By setting it false, program will exit after it set all wallpaper')
@click.argument('photo_path', type=click.Path(exists=True, file_okay=False, executable=False, dir_okay=True, resolve_path=True))
def cinnamon(pause, photo_path, repetition) -> None:
    '''Changes wallpaper on cinnamon'''
    photos: list[str] = file_validator(photo_path)
    while True:
        for photo in photos: 
            system(f'gsettings set org.cinnamon.desktop.background picture-uri  file://{photo}"')
            sleep(pause)
        else:
            exit() if repetition == False else ...
            
# ======== # adding subcommand to cli# ======== #
cli.add_command(gnome)
cli.add_command(cinnamon)

if __name__ == '__main__':
    cli()