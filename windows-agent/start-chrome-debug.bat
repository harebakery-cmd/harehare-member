@echo off
set "PROFILE=%~dp0browser-profile"
if not exist "%PROFILE%" mkdir "%PROFILE%"
set "BROWSER=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if not exist "%BROWSER%" set "BROWSER=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
if not exist "%BROWSER%" set "BROWSER=%LocalAppData%\Google\Chrome\Application\chrome.exe"
if not exist "%BROWSER%" set "BROWSER=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
if not exist "%BROWSER%" (
  echo Chrome 또는 Edge를 찾지 못했습니다.
  pause
  exit /b 1
)
start "Harehare 자동화 브라우저" "%BROWSER%" --remote-debugging-port=9222 --user-data-dir="%PROFILE%" "https://asp.upsolution.co.kr"
