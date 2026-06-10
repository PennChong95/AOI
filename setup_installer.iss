; AOI复判系统V4.1 - Inno Setup Installer Script
#define MyAppName "AOI复判系统V4.1"
#define MyAppVersion "4.1.0"
#define MyAppPublisher "AOI Quality Team"
#define MyAppExeName "main.exe"

[Setup]
AppId={{A0E5F3D8-1234-5678-9ABC-DEF012345678}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={pf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=installer_output
OutputBaseFilename=AOI复判系统V4.1_Setup
SetupIconFile=app_icon.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "快捷方式"; Flags: checkedonce

[Files]
Source: "dist\main\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
Name: "{commonappdata}\InspectionReview"; Permissions: users-modify
Name: "{app}\data\layouts"; Permissions: users-modify

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app_icon.ico"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\app_icon.ico"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动 AOI 复判系统 V4"; Flags: nowait postinstall skipifsilent
