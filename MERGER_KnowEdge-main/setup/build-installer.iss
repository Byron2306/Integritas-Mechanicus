; KnowEdge Merger V4.3.2 — Windows Installer Build Script
; Documentation: https://jrsoftware.org/ishelp/

[Setup]
AppName=KnowEdge Merger
AppVersion=4.3.2
AppPublisher=NWU - North-West University
DefaultDirName={autopf}\KnowEdgeMerger
DefaultGroupName=KnowEdge Merger
OutputBaseFilename=KnowEdgeMerger-Setup-4.3.2
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\*"; DestDir: "{app}\dist"; Flags: ignoreversion recursesubdirs
Source: "..\app.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\install-mistral-vibe.ps1"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\KnowEdge Merger"; Filename: "{app}\start.bat"; IconFilename: "{app}\dist\favicon.ico"
Name: "{userdesktop}\KnowEdge Merger"; Filename: "{app}\start.bat"; Tasks: desktopicon

[Run]
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -NonInteractive -File ""{app}\install-mistral-vibe.ps1"""; StatusMsg: "Performing Threaded Installation (Mistral/Python)..."; Flags: runhidden waituntilterminated

[Code]
function InitializeSetup: Boolean;
var
  WinHttpReq: Variant;
begin
  Result := True;
  try
    WinHttpReq := CreateOleObject('WinHttp.WinHttpRequest.5.1');
    WinHttpReq.Open('GET', 'http://localhost:11434', False);
    WinHttpReq.Send;
    if WinHttpReq.Status = 200 then
    begin
        MsgBox('Ollama is already running on port 11434. Setup will proceed to check versions.', mbInformation, MB_OK);
    end;
  except
    // Port likely free or service not running
  end;
end;
