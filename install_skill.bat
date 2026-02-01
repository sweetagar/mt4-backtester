@echo off
setlocal enabledelayedexpansion

echo ========================================
echo   MT4 Backtester Skill Installer
echo ========================================
echo.

:: Source = current directory (where script is run from)
set "SOURCE=%~dp0"

:: Destinations
set "CLAUDE_DEST=%USERPROFILE%\.claude\skills\mt4-backtester"
set "OPENCODE_DEST=%USERPROFILE%\.config\opencode\skills\mt4-backtester"

:: Files to copy
set "FILES=SKILL.md requirements.txt"
set "SCRIPT_FILES=scripts\mt4_runner.py scripts\parse_report.py"
set "REF_FILES=references\SOP_SPREAD_QC.md"

echo Select installation target:
echo   1. Claude Code only
echo   2. OpenCode only
echo   3. Both
echo.
set /p choice="Enter choice (1-3): "

if "%choice%"=="1" set "INSTALL_CLAUDE=1"
if "%choice%"=="2" set "INSTALL_OPENCODE=1"
if "%choice%"=="3" set "INSTALL_CLAUDE=1" & set "INSTALL_OPENCODE=1"

if not defined INSTALL_CLAUDE if not defined INSTALL_OPENCODE (
    echo Invalid choice. Exiting.
    pause
    exit /b 1
)

echo.
echo Check for existing installation...
set "OVERWRITE="
if defined INSTALL_CLAUDE (
    if exist "!CLAUDE_DEST!\SKILL.md" (
        set "OVERWRITE=1"
    )
)
if defined INSTALL_OPENCODE (
    if exist "!OPENCODE_DEST!\SKILL.md" (
        set "OVERWRITE=1"
    )
)

if defined OVERWRITE (
    echo.
    echo WARNING: Existing installation found.
    set /p confirm="Overwrite? (Y/N): "
    if /i not "!confirm!"=="Y" (
        echo Installation cancelled.
        pause
        exit /b 0
    )
)

:: Create directories and copy files
if defined INSTALL_CLAUDE (
    echo.
    echo Installing to Claude Code: !CLAUDE_DEST!
    if not exist "!CLAUDE_DEST!" mkdir "!CLAUDE_DEST!"
    if not exist "!CLAUDE_DEST!\scripts" mkdir "!CLAUDE_DEST!\scripts"
    if not exist "!CLAUDE_DEST!\references" mkdir "!CLAUDE_DEST!\references"

    for %%F in (%FILES%) do (
        copy /Y "!SOURCE!%%F" "!CLAUDE_DEST!\" >nul
        echo   Copied: %%F
    )
    for %%F in (%SCRIPT_FILES%) do (
        copy /Y "!SOURCE!%%F" "!CLAUDE_DEST!\scripts\" >nul
        echo   Copied: scripts\%%~nxF
    )
    for %%F in (%REF_FILES%) do (
        copy /Y "!SOURCE!%%F" "!CLAUDE_DEST!\references\" >nul
        echo   Copied: references\%%~nxF
    )
)

if defined INSTALL_OPENCODE (
    echo.
    echo Installing to OpenCode: !OPENCODE_DEST!
    if not exist "!OPENCODE_DEST!" mkdir "!OPENCODE_DEST!"
    if not exist "!OPENCODE_DEST!\scripts" mkdir "!OPENCODE_DEST!\scripts"
    if not exist "!OPENCODE_DEST!\references" mkdir "!OPENCODE_DEST!\references"

    for %%F in (%FILES%) do (
        copy /Y "!SOURCE!%%F" "!OPENCODE_DEST!\" >nul
        echo   Copied: %%F
    )
    for %%F in (%SCRIPT_FILES%) do (
        copy /Y "!SOURCE!%%F" "!OPENCODE_DEST!\scripts\" >nul
        echo   Copied: scripts\%%~nxF
    )
    for %%F in (%REF_FILES%) do (
        copy /Y "!SOURCE!%%F" "!OPENCODE_DEST!\references\" >nul
        echo   Copied: references\%%~nxF
    )
)

echo.
echo ========================================
echo   Setting up Python virtual environment...
echo ========================================
echo.

:: Check if python is available
where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH.
    echo Please install Python 3.7+ and add it to your PATH.
    pause
    exit /b 1
)

:: Setup venv for each installation
if defined INSTALL_CLAUDE (
    echo.
    echo Setting up venv for Claude Code...
    cd /d "!CLAUDE_DEST!"
    set "DO_VENV=1"
    if exist .venv (
        echo   .venv already exists.
        set /p VENV_CHOICE="Update packages? (Y/N): "
        if /i not "!VENV_CHOICE!"=="Y" (
            set "DO_VENV=0"
            echo   Skipping package update.
        )
    )
    if "!DO_VENV!"=="1" (
        if not exist .venv (
            echo   Creating .venv...
            python -m venv .venv
            if errorlevel 1 (
                echo   ERROR: Failed to create venv.
                cd /d "!SOURCE!"
                pause
                exit /b 1
            )
        )
        echo   Installing requirements...
        .venv\Scripts\pip install -r requirements.txt --quiet
        if errorlevel 1 (
            echo   WARNING: Some packages may have failed to install.
        ) else (
            echo   Requirements installed successfully!
        )
    )
)

if defined INSTALL_OPENCODE (
    echo.
    echo Setting up venv for OpenCode...
    cd /d "!OPENCODE_DEST!"
    set "DO_VENV=1"
    if exist .venv (
        echo   .venv already exists.
        set /p VENV_CHOICE="Update packages? (Y/N): "
        if /i not "!VENV_CHOICE!"=="Y" (
            set "DO_VENV=0"
            echo   Skipping package update.
        )
    )
    if "!DO_VENV!"=="1" (
        if not exist .venv (
            echo   Creating .venv...
            python -m venv .venv
            if errorlevel 1 (
                echo   ERROR: Failed to create venv.
                cd /d "!SOURCE!"
                pause
                exit /b 1
            )
        )
        echo   Installing requirements...
        .venv\Scripts\pip install -r requirements.txt --quiet
        if errorlevel 1 (
            echo   WARNING: Some packages may have failed to install.
        ) else (
            echo   Requirements installed successfully!
        )
    )
)

echo.
echo ========================================
echo   Installation Complete!
echo ========================================
echo.
if defined INSTALL_CLAUDE (
    echo Claude Code: !CLAUDE_DEST!
)
if defined INSTALL_OPENCODE (
    echo OpenCode:   !OPENCODE_DEST!
)
echo.
echo Skill is ready to use!
echo.
pause
