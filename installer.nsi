; NSIS Installer Script for Yuki
; Requires NSIS 3.x — compile with: makensis installer.nsi

!include "MUI2.nsh"
!include "FileFunc.nsh"

;--------------------------------
; General
!define PRODUCT_VERSION "1.0.0"
Name "Yuki"
OutFile "Yuki_Setup_${PRODUCT_VERSION}.exe"
Unicode True
InstallDir "$PROGRAMFILES64\Yuki"
InstallDirRegKey HKCU "Software\Yuki" "InstallDir"
RequestExecutionLevel admin
SetCompressor /SOLID lzma

;--------------------------------
; Variables
Var StartMenuFolder

;--------------------------------
; Interface Settings
!define MUI_ABORTWARNING
!define MUI_ICON "assets\icon.ico"
!define MUI_UNICON "assets\icon.ico"
!define MUI_WELCOMEPAGE_TITLE "Welcome to Yuki Setup"
!define MUI_WELCOMEPAGE_TEXT "Yuki is a professional-grade media downloader and MP3 editor.$\n$\nSupports YouTube, Spotify, TikTok, Instagram, SoundCloud, and more.$\n$\nClick Next to continue."
!define MUI_FINISHPAGE_RUN "$INSTDIR\Yuki.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Launch Yuki now"
!define MUI_FINISHPAGE_LINK "Visit GitHub"
!define MUI_FINISHPAGE_LINK_LOCATION "https://github.com/lfl1337/Yuki"

;--------------------------------
; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY

; Start Menu page
!define MUI_STARTMENUPAGE_REGISTRY_ROOT "HKCU"
!define MUI_STARTMENUPAGE_REGISTRY_KEY "Software\Yuki"
!define MUI_STARTMENUPAGE_REGISTRY_VALUENAME "StartMenuFolder"
!insertmacro MUI_PAGE_STARTMENU Application $StartMenuFolder

; Components page
!insertmacro MUI_PAGE_COMPONENTS

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
; Installer Sections

Section "Yuki Media Suite" SecMain
    SectionIn RO

    SetOutPath "$INSTDIR"

    ; Copy all files from onedir build
    File /r "dist\Yuki\*.*"

    ; Write install dir to registry
    WriteRegStr HKCU "Software\Yuki" "InstallDir" "$INSTDIR"
    WriteRegStr HKCU "Software\Yuki" "Version" "${PRODUCT_VERSION}"

    ; Start Menu shortcuts
    !insertmacro MUI_STARTMENU_WRITE_BEGIN Application
        CreateDirectory "$SMPROGRAMS\$StartMenuFolder"
        CreateShortcut "$SMPROGRAMS\$StartMenuFolder\Yuki.lnk" "$INSTDIR\Yuki.exe"
        CreateShortcut "$SMPROGRAMS\$StartMenuFolder\Uninstall Yuki.lnk" "$INSTDIR\Uninstall.exe"
    !insertmacro MUI_STARTMENU_WRITE_END

    ; Write uninstaller
    WriteUninstaller "$INSTDIR\Uninstall.exe"

    ; Add to Windows Add/Remove Programs
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Yuki" \
        "DisplayName" "Yuki"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Yuki" \
        "UninstallString" '"$INSTDIR\Uninstall.exe"'
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Yuki" \
        "DisplayVersion" "${PRODUCT_VERSION}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Yuki" \
        "Publisher" "NINYM"
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

Section "Desktop Shortcut" SecDesktop
    CreateShortcut "$DESKTOP\Yuki.lnk" "$INSTDIR\Yuki.exe"
SectionEnd

Section "Start Menu Entry" SecStartMenu
    ; Already handled in SecMain via MUI_STARTMENU_WRITE_BEGIN
SectionEnd

Section /o "Launch at Windows Startup" SecAutostart
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "Yuki" '"$INSTDIR\Yuki.exe"'
SectionEnd

;--------------------------------
; Section descriptions
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
    !insertmacro MUI_DESCRIPTION_TEXT ${SecMain}      "Core Yuki application files (required)."
    !insertmacro MUI_DESCRIPTION_TEXT ${SecDesktop}   "Create a shortcut on the Desktop."
    !insertmacro MUI_DESCRIPTION_TEXT ${SecStartMenu} "Add Yuki to the Start Menu."
    !insertmacro MUI_DESCRIPTION_TEXT ${SecAutostart} "Start Yuki automatically when Windows starts."
!insertmacro MUI_FUNCTION_DESCRIPTION_END

;--------------------------------
; Uninstaller

Section "Uninstall"

    ; Ask about user data
    MessageBox MB_YESNO "Remove user data (settings and history)?" IDNO skip_data
        RMDir /r "$INSTDIR\data"
    skip_data:

    ; Remove all installed files
    RMDir /r "$INSTDIR"

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
