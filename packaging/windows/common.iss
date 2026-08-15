; ============================================================
; common.iss — Pénzügyi Napló Windows telepítő, KÖZÖS logika
; ============================================================
; Ezt a fájlt SOHA ne fordítsd le közvetlenül!
; Mindig a variant fájlokon (installer-stable.iss / installer-preview.iss)
; keresztül fordítsd, mert azok állítják be az AppVariant #define-t,
; ami előtt ez a fájl included.
;
; Ha a telepítő logikáján (wizard, [Files], [Code] stb.) változtatsz,
; ide nyúlj — NEM a variant fájlokba. A variant fájlok csak a
; stable/preview közti különbségeket paraméterezik.
; ============================================================

#ifndef AppVariant
  #error "AppVariant nincs definiálva. Ezt a fájlt csak installer-stable.iss vagy installer-preview.iss include-olhatja."
#endif

; ------------------------------------------------------------
; Verzió — egyetlen forrásból, mindkét variant ugyanazt használja
; ------------------------------------------------------------
#define MyAppVersion "0.2.0"
#define MyAppPublisher "Szaboger Corp"
#define MyAppURL "https://szabogergely26.github.io/"
#define MyAppExeName "PenzugyiNaplo.exe"

; ------------------------------------------------------------
; Variant-specifikus értékek
; ------------------------------------------------------------
#if AppVariant == "preview"
  #define MyAppName "Pénzügyi Napló (Előzetes)"
  #define MyAppId "{{5D3770AB-AF07-4438-9799-54E16852D49A}"
  #define MyAppAssocExt ".mypp"
  #define MyOutputBaseFilename "PenzugyiNaplo_Preview_Setup"
  #define MySetupIconFile "C:\Users\szabo\Projektek\penzugyi-naplo\icons\app_icon_preview.ico"
  #define MyBackgroundImage "installer_background_fullscreen_picture_preview_1920x1200.bmp"
  #define MyDefaultDirName "{autopf}\Pénzügyi Napló Preview"
#else
  #define MyAppName "Pénzügyi Napló"
  #define MyAppId "{{7FE739A9-AE9A-407C-A09F-7A3B1D69284A}"
  #define MyAppAssocExt ".myp"
  #define MyOutputBaseFilename "PenzugyiNaplo_Setup"
  #define MySetupIconFile "C:\Users\szabo\Projektek\penzugyi-naplo\icons\app_icon_main.ico"
  #define MyBackgroundImage "installer_background_fullscreen_picture_1920x1200.bmp"
  #define MyDefaultDirName "{autopf}\Pénzügyi Napló"
#endif

#define MyAppAssocName MyAppName + " File"
#define MyAppAssocKey StringChange(MyAppAssocName, " ", "") + MyAppAssocExt

[Setup]
; NOTE: Az AppId a két variant között KÜLÖNBÖZŐ kell legyen,
; hogy stable és preview egymás mellett, egymástól függetlenül
; telepíthető/eltávolítható legyen.
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={#MyDefaultDirName}
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
ChangesAssociations=yes
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=C:\Users\szabo\Projektek\penzugyi-naplo\license.txt
OutputDir=C:\Users\szabo\Projektek\penzugyi-naplo\windows
OutputBaseFilename={#MyOutputBaseFilename}
SetupIconFile={#MySetupIconFile}
SolidCompression=yes
WizardStyle=modern windows11

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "hungarian"; MessagesFile: "compiler:Languages\Hungarian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "C:\Users\szabo\Projektek\penzugyi-naplo\dist\PenzugyiNaplo\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\szabo\Projektek\penzugyi-naplo\dist\PenzugyiNaplo\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTE: Don't use "Flags: ignoreversion" on any shared system files
Source: "C:\Users\szabo\Projektek\penzugyi-naplo\packaging\windows\pictures\{#MyBackgroundImage}"; DestDir: "{tmp}"; Flags: dontcopy

[Registry]
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocExt}\OpenWithProgids"; ValueType: string; ValueName: "{#MyAppAssocKey}"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocKey}"; ValueType: string; ValueName: ""; ValueData: "{#MyAppAssocName}"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocKey}\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocKey}\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
function GetSystemMetrics(nIndex: Integer): Integer;
  external 'GetSystemMetrics@user32.dll stdcall';

const
  SM_CXSCREEN = 0;
  SM_CYSCREEN = 1;

var
  BackForm: TSetupForm;
  BackImage: TBitmapImage;


  procedure InitializeWizard();
var
  ScreenW, ScreenH: Integer;
begin
  ScreenW := GetSystemMetrics(SM_CXSCREEN);
  ScreenH := GetSystemMetrics(SM_CYSCREEN);

  { A kép kicsomagolása egy ideiglenes mappába }
  ExtractTemporaryFile('{#MyBackgroundImage}');

  { Teljes képernyős háttér-ablak létrehozása, a tényleges felbontáshoz igazítva }
  BackForm := CreateCustomForm(ScreenW, ScreenH, False, False);
  BackForm.BorderStyle := bsNone;
  BackForm.Left := 0;
  BackForm.Top := 0;

  { A háttérkép ráhúzása a teljes ablakra }
  BackImage := TBitmapImage.Create(BackForm);
  BackImage.Parent := BackForm;
  BackImage.Left := 0;
  BackImage.Top := 0;
  { Szándékosan a képernyő TELJES méretéhez igazítjuk (nem ClientWidth/Height-hez),
    mert ha a formnak bármilyen apró keret/margó eltérése van, a ClientWidth/Height
    kisebb lehet a képernyőnél, és a kép nem éri el a jobb/alsó szélt. }
  BackImage.Width := ScreenW;
  BackImage.Height := ScreenH;
  BackImage.Stretch := True;
  BackImage.Bitmap.LoadFromFile(ExpandConstant('{tmp}\{#MyBackgroundImage}'));



  { Megjelenítjük a hátteret }
  BackForm.Show;

  { A Wizard-ablakot középre igazítjuk a háttér fölé.
    Szándékosan ScreenW/ScreenH-t használjuk itt is (nem BackForm.Width/Height-et),
    hogy ugyanabból a forrásból számoljunk, mint a BackImage méretezésénél —
    így a kép és a Wizard pozíciója nem tud elcsúszni egymáshoz képest. }
  WizardForm.Left := BackForm.Left + (ScreenW - WizardForm.Width) div 2;
  WizardForm.Top := BackForm.Top + (ScreenH - WizardForm.Height) div 2;
end;

procedure DeinitializeSetup();
begin
  if Assigned(BackForm) then
    BackForm.Free;
end;
