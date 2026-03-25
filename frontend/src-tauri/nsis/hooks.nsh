; Yuki NSIS installer hooks
; Silently kill running Yuki processes before install/uninstall
; so the user is never prompted to close the app manually.

!macro NSIS_HOOK_PREINSTALL
  nsExec::Exec 'taskkill /f /im Yuki.exe'
  nsExec::Exec 'taskkill /f /im yuki-backend.exe'
  Sleep 2000
!macroend

!macro NSIS_HOOK_PREUNINSTALL
  nsExec::Exec 'taskkill /f /im Yuki.exe'
  nsExec::Exec 'taskkill /f /im yuki-backend.exe'
  Sleep 2000
!macroend
