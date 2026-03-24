; NSIS Installer Script for Yuki
; Requires NSIS 3.x — compile with: makensis installer.nsi

!include "MUI2.nsh"
!include "FileFunc.nsh"

;--------------------------------
; General
Name "Yuki"
OutFile "Yuki-Setup-1.0.0.exe"
Unicode True
InstallDir "$PROGRAMFILES64\Yuki"
InstallDirRegKey HKCU "Software\Yuki" "InstallDir"
RequestExecutionLevel admin
SetCompressor /SOLID lzma

;--------------------------------
; Variables
Var StartMenuFolder
Var DesktopShortcut
Var AutostartEnabled

;--------------------------------
; Interface Settings
!define MUI_ABORTWARNING
!define MUI_ICON "assets\icon.ico"
!define MUI_UNICON "assets\icon.ico"
!define MUI_WELCOMEPAGE_TITLE "Welcome to Yuki Setup"
!define MUI_WELCOMEPAGE_TEXT "Yuki is a professional-grade media downloader and MP3 editor.$\n$\nSupports YouTube, Spotify, TikTok, Instagram, SoundCloud, and more.$\n$\nClick Next to continue."
!define MUI_FINISHPAGE_RUN "$INSTDIR\Yuki.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Launch Yuki"
!define MUI_FINISHPAGE_LINK "Visit GitHub"
!define MUI_FINISHPAGE_LINK_LOCATION "https://github.com/lfl1337/Yuki"

;--------------------------------
; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "README.md"
!insertmacro MUI_PAGE_DIRECTORY

; Start Menu page
!define MUI_STARTMENUPAGE_REGISTRY_ROOT "HKCU"
!define MUI_STARTMENUPAGE_REGISTRY_KEY "Software\Yuki"
!define MUI_STARTMENUPAGE_REGISTRY_VALUENAME "StartMenuFolder"
!insertmacro MUI_PAGE_STARTMENU Application $StartMenuFolder

; Components page (desktop shortcut, autostart)
Page custom ComponentsPage ComponentsLeave

!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; Uninstaller pages
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

;--------------------------------
; Languages
!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "German"
!insertmacro MUI_LANGUAGE "French"
!insertmacro MUI_LANGUAGE "Spanish"
!insertmacro MUI_LANGUAGE "Italian"
!insertmacro MUI_LANGUAGE "Japanese"

;--------------------------------
; Components page (custom)
Var hDesktopCB
Var hAutoStartCB

Function ComponentsPage
    nsDialogs::Create 1018
    Pop $0

    ${NSD_CreateLabel} 0 0 100% 20u "Additional Options:"
    ${NSD_CreateCheckbox} 0 25u 100% 10u "Create Desktop Shortcut"
    Pop $hDesktopCB
    ${NSD_SetState} $hDesktopCB ${BST_CHECKED}

    ${NSD_CreateCheckbox} 0 40u 100% 10u "Start Yuki with Windows"
    Pop $hAutoStartCB

    nsDialogs::Show
FunctionEnd

Function ComponentsLeave
    ${NSD_GetState} $hDesktopCB $DesktopShortcut
    ${NSD_GetState} $hAutoStartCB $AutostartEnabled
FunctionEnd

;--------------------------------
; Installer Sections

Section "Yuki (required)" SecMain
    SectionIn RO

    SetOutPath "$INSTDIR"

    ; Copy the main executable
    File "dist\Yuki.exe"

    ; Write install dir to registry
    WriteRegStr HKCU "Software\Yuki" "InstallDir" "$INSTDIR"
    WriteRegStr HKCU "Software\Yuki" "Version" "1.0.0"

    ; Start Menu shortcuts
    !insertmacro MUI_STARTMENU_WRITE_BEGIN Application
        CreateDirectory "$SMPROGRAMS\$StartMenuFolder"
        CreateShortcut "$SMPROGRAMS\$StartMenuFolder\Yuki.lnk" "$INSTDIR\Yuki.exe"
        CreateShortcut "$SMPROGRAMS\$StartMenuFolder\Uninstall Yuki.lnk" "$INSTDIR\Uninstall.exe"
    !insertmacro MUI_STARTMENU_WRITE_END

    ; Desktop shortcut (optional)
    ${If} $DesktopShortcut == ${BST_CHECKED}
        CreateShortcut "$DESKTOP\Yuki.lnk" "$INSTDIR\Yuki.exe"
    ${EndIf}

    ; Autostart (optional)
    ${If} $AutostartEnabled == ${BST_CHECKED}
        WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "Yuki" '"$INSTDIR\Yuki.exe"'
    ${EndIf}

    ; Write uninstaller
    WriteUninstaller "$INSTDIR\Uninstall.exe"

    ; Add to Windows Add/Remove Programs
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Yuki" \
        "DisplayName" "Yuki"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Yuki" \
        "UninstallString" '"$INSTDIR\Uninstall.exe"'
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Yuki" \
        "DisplayVersion" "1.0.0"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Yuki" \
        "Publisher" "lfl1337"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Yuki" \
        "URLInfoAbout" "https://github.com/lfl1337/Yuki"
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Yuki" \
        "NoModify" 1
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Yuki" \
        "NoRepair" 1

    ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
    IntFmt $0 "0x%08X" $0
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Yuki" \
        "EstimatedSize" "$0"

SectionEnd

;--------------------------------
; Uninstaller

Section "Uninstall"

    ; Remove executable
    Delete "$INSTDIR\Yuki.exe"
    Delete "$INSTDIR\Uninstall.exe"
    RMDir "$INSTDIR"

    ; Remove registry entries
    DeleteRegKey HKCU "Software\Yuki"
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Yuki"
    DeleteRegValue HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "Yuki"

    ; Remove shortcuts
    !insertmacro MUI_STARTMENU_GETFOLDER Application $StartMenuFolder
    Delete "$SMPROGRAMS\$StartMenuFolder\Yuki.lnk"
    Delete "$SMPROGRAMS\$StartMenuFolder\Uninstall Yuki.lnk"
    RMDir "$SMPROGRAMS\$StartMenuFolder"
    Delete "$DESKTOP\Yuki.lnk"

SectionEnd
