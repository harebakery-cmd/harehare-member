@echo off
set "PROFILE=%~dp0browser-profile"
if not exist "%PROFILE%" mkdir "%PROFILE%"
start "Harehare 자동화 브라우저" chrome.exe --remote-debugging-port=9222 --user-data-dir="%PROFILE%" "https://asp.upsolution.co.kr"
