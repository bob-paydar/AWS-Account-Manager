[Setup]
AppId=BobPaydar.AWSAccountManager
AppName=AWS Account Manager
AppVersion=1.4.0
AppPublisher=Bob Paydar
DefaultDirName={localappdata}\Programs\AWSAccountManager
DefaultGroupName=AWS Account Manager
PrivilegesRequired=lowest
OutputDir=installer_output
OutputBaseFilename=AWSAccountManager_Setup_1.4.0
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\AWSAccountManager.exe
[Files]
Source: "dist\AWSAccountManager.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "AWS Setup Readme.txt"; DestDir: "{app}"; Flags: ignoreversion
[Tasks]
Name: desktopicon; Description: "Create a desktop shortcut"; Flags: unchecked
[Icons]
Name: "{group}\AWS Account Manager"; Filename: "{app}\AWSAccountManager.exe"
Name: "{autodesktop}\AWS Account Manager"; Filename: "{app}\AWSAccountManager.exe"; Tasks: desktopicon
[Run]
Filename: "{app}\AWSAccountManager.exe"; Description: "Launch AWS Account Manager"; Flags: nowait postinstall skipifsilent
