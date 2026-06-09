[Setup]
AppName=KnowEdge Merger
AppVersion=5.0.0
AppPublisher=NWU Forensic Intelligence Division
AppPublisherURL=https://nwu.ac.za
DefaultDirName={autopf}\KnowEdge Merger
DefaultGroupName=KnowEdge Merger
AllowNoIcons=yes
OutputDir=installer\output
OutputBaseFilename=KnowEdgeMerger_v5.0.0_Setup
SetupIconFile=public\favicon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
MinVersion=10.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"

[Files]
Source: "dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "app.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "installer\launch.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "installer\install_deps.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "PLAYBOOK.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\KnowEdge Merger"; Filename: "{app}\launch.bat"; IconFilename: "{app}\favicon.ico"
Name: "{commondesktop}\KnowEdge Merger"; Filename: "{app}\launch.bat"; IconFilename: "{app}\favicon.ico"; Tasks: desktopicon
Name: "{group}\Uninstall KnowEdge Merger"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\install_deps.bat"; Description: "Install Python dependencies"; Flags: postinstall waituntilterminated shellexec
