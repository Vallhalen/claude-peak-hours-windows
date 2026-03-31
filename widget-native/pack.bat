@echo off
set MAKEAPPX="C:\Program Files (x86)\Windows Kits\10\bin\10.0.19041.0\x64\makeappx.exe"
set PUBLISH="%~dp0bin\Release\net9.0-windows10.0.22621.0\win-x64\publish"
set OUTPUT="%~dp0ClaudePeakWidget.msix"

copy /Y "%~dp0Package.appxmanifest" %PUBLISH%\AppxManifest.xml >nul
xcopy /Y /E /I "%~dp0Images" %PUBLISH%\Images >nul
if not exist %PUBLISH%\Public mkdir %PUBLISH%\Public

echo Creating MSIX package...
%MAKEAPPX% pack /o /d %PUBLISH% /p %OUTPUT%

if %ERRORLEVEL% EQU 0 (
    echo.
    echo SUCCESS: %OUTPUT%
) else (
    echo.
    echo FAILED with error %ERRORLEVEL%
)
pause
