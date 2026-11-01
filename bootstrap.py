"""Check the local environment and launch/build using an isolated virtual environment."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import webbrowser

ROOT=Path(__file__).resolve().parent

def run(args):
    subprocess.run([str(a) for a in args],cwd=ROOT,check=True)

def main():
    if os.name!='nt': raise RuntimeError('These launch/build scripts target Windows 10/11.')
    if sys.version_info<(3,10): raise RuntimeError('Install Python 3.10 or later from python.org, including Tcl/Tk and pip.')
    try: import tkinter
    except ImportError: raise RuntimeError('Tcl/Tk is missing. Run the Python installer, select Modify, and enable Tcl/Tk and IDLE. It cannot be installed with pip.')
    mode=sys.argv[1] if len(sys.argv)>1 else 'run'
    env=ROOT/'.venv'; python=env/'Scripts/python.exe'
    if not python.exists(): run([sys.executable,'-m','venv',env])
    if subprocess.run([str(python),'-c','from PIL import Image, ImageTk'],capture_output=True).returncode:
        run([python,'-m','ensurepip','--upgrade'])
        run([python,'-m','pip','install','-r',ROOT/'requirements.txt'])
    if mode=='run':
        run([python,ROOT/'aws_manager.py']); return
    check=subprocess.run([str(python),'-c','import PyInstaller'],capture_output=True)
    if check.returncode:
        run([python,'-m','ensurepip','--upgrade'])
        run([python,'-m','pip','install','-r',ROOT/'requirements-build.txt'])
    run([python,'-m','PyInstaller','--noconfirm','--clean','--onefile','--windowed','--name','AWSAccountManager',ROOT/'aws_manager.py'])
    if mode=='installer':
        paths=[shutil.which('ISCC.exe')]
        for base in (os.environ.get('ProgramFiles(x86)',''),os.environ.get('ProgramFiles',''),os.environ.get('LOCALAPPDATA','')+'/Programs'):
            for version in ('6','7'): paths.append(str(Path(base)/('Inno Setup '+version)/'ISCC.exe'))
        compiler=next((p for p in paths if p and Path(p).is_file()),None)
        if not compiler:
            print('Inno Setup is required to build the installer.')
            if input('Install Inno Setup using winget now? [y/N]: ').strip().lower()=='y' and shutil.which('winget'):
                run(['winget','install','--id','JRSoftware.InnoSetup','--exact','--source','winget'])
                compiler=next((p for p in paths if p and Path(p).is_file()),None)
            if not compiler:
                webbrowser.open('https://jrsoftware.org/isdl.php')
                raise RuntimeError('Install Inno Setup, then run Create_Installer.bat again.')
        run([compiler,ROOT/'installer.iss'])
        print('Installer created in the installer_output folder.')
    else: print('EXE created: dist/AWSAccountManager.exe')

if __name__=='__main__':
    try: main()
    except (Exception,KeyboardInterrupt) as exc:
        print('\nFAILED:',exc); sys.exit(1)
