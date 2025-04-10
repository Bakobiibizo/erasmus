@echo off
setlocal enabledelayedexpansion

:detect_os
set "OS=Unknown"
for /f "tokens=* usebackq" %%i in (`ver`) do set "VER_OUT=%%i"
echo !VER_OUT! | findstr /i "Windows" >nul 2>&1 && (
    set "OS=Windows"
    goto :eof
)
echo !VER_OUT! | findstr /i "Darwin" >nul 2>&1 && (
    set "OS=macOS"
    goto :eof
)
echo !VER_OUT! | findstr /i "Linux" >nul 2>&1 && (
    set "OS=Linux"
    goto :eof
)
goto :eof

:check_python
set "PYTHON_CMD="
where python.exe >nul 2>&1 && set "PYTHON_CMD=python.exe"
if "!PYTHON_CMD!"=="" (
    where python3.exe >nul 2>&1 && set "PYTHON_CMD=python3.exe"
)
if "!PYTHON_CMD!"=="" (
    echo Error: Python is not installed!
    echo Please install Python 3.8+ before proceeding.
    exit /b 1
)

for /f "tokens=* usebackq" %%i in (`!PYTHON_CMD! -c "import sys; print(sys.version_info.major)"`) do set "MAJOR=%%i"
for /f "tokens=* usebackq" %%i in (`!PYTHON_CMD! -c "import sys; print(sys.version_info.minor)"`) do set "MINOR=%%i"

if "!MAJOR!" lss "3" (
    echo Error: Python 3.8+ is required.
    exit /b 1
) else if "!MAJOR!" equ "3" (
    if "!MINOR!" lss "8" (
        echo Error: Python 3.8+ is required.
        exit /b 1
    )
)
goto :eof

:check_prerequisites
call :detect_os
if "!OS!"=="Windows" (
    echo Checking Windows prerequisites...
    where winget.exe >nul 2>&1 || (
        echo Installing winget...
        powershell -Command "Add-AppxPackage -RegisterByFamilyName -MainPackage Microsoft.DesktopAppInstaller_8wekyb3d8bbwe"
        where winget.exe >nul 2>&1 || (
            echo Failed to install winget. Please install it manually from the Microsoft Store.
            exit /b 1
        )
    )
) else if "!OS!"=="macOS" (
    echo Checking macOS prerequisites...
    where brew.exe >nul 2>&1 || (
        echo Homebrew is required but not installed.
        echo Please install Homebrew first: https://brew.sh
        exit /b 1
    )
) else if "!OS!"=="Linux" (
    echo Checking Linux prerequisites...
    where curl.exe >nul 2>&1 || (
        echo Installing curl...
        where apt-get.exe >nul 2>&1 && (
            apt-get update && apt-get install -y curl
        ) || (
            where yum.exe >nul 2>&1 && (
                yum install -y curl
            ) || (
                echo Could not install curl. Please install it manually.
                exit /b 1
            )
        )
    )
)
goto :eof

:install_uv
echo Installing uv package manager...
if "!OS!"=="Windows" (
    winget install --id=astral-sh.uv -e
) else if "!OS!"=="macOS" (
    brew install uv
) else if "!OS!"=="Linux" (
    curl -LsSf https://astral.sh/uv/install.sh | sh
) else (
    echo Unsupported operating system: !OS!
    exit /b 1
)

where uv.exe >nul 2>&1 || (
    echo Failed to install uv package manager!
    exit /b 1
)

echo Installation complete!
echo You can now run: uv run erasmus.py
goto :eof

:setup_env
echo Creating environment files...

:: Create .env.example
(
echo IDE_ENV=
echo GIT_TOKEN=
echo OPENAI_API_KEY=
) > .env.example

:: Prompt for IDE environment
echo Please enter your IDE environment (cursor/windsurf):
set /p "IDE_ENV="

:: Create .env
(
echo IDE_ENV=!IDE_ENV!
echo GIT_TOKEN=
echo OPENAI_API_KEY=
) > .env

echo Environment files created successfully
goto :eof

:init_watcher
echo Initializing erasmus...

:: Extract erasmus.py from the embedded content
echo Extracting erasmus.py...

:: Find the SHA256 hash in this script
for /f "tokens=* usebackq" %%i in (`findstr /C:"# SHA256_HASH=" "%~f0"`) do set "EXPECTED_HASH=%%i"
set "EXPECTED_HASH=!EXPECTED_HASH:# SHA256_HASH=!"

:: Extract the base64 content between markers
powershell -Command "$content = Get-Content '%~f0' | Select-String -Pattern \"# BEGIN_BASE64_CONTENT\",\"# END_BASE64_CONTENT\" -Context 0,10000 | ForEach-Object { $_.Context.PostContext } | Where-Object { $_ -notmatch \"BEGIN_BASE64_CONTENT|END_BASE64_CONTENT\" } | ForEach-Object { $_ -replace \"^# \", \"\" }; $content | Set-Content -Encoding ASCII temp_base64.txt"

:: Decode the base64 content
powershell -Command "$content = Get-Content -Encoding ASCII temp_base64.txt; $content = $content -join \"\"; [System.IO.File]::WriteAllBytes(\"erasmus.py\", [System.Convert]::FromBase64String($content))"

:: Verify the SHA256 hash
powershell -Command "$hash = Get-FileHash -Algorithm SHA256 -Path erasmus.py | Select-Object -ExpandProperty Hash; if ($hash -eq \"!EXPECTED_HASH!\") { Write-Host \"SHA256 hash verified: $hash\" } else { Write-Host \"Error: SHA256 hash verification failed!\" -ForegroundColor Red; Write-Host \"Expected: !EXPECTED_HASH!\" -ForegroundColor Red; Write-Host \"Actual: $hash\" -ForegroundColor Red; exit 1 }"

:: Run the erasmus setup with IDE environment
echo Running erasmus setup...
uv run erasmus.py --setup !IDE_ENV!

echo Erasmus initialized successfully!
echo To run Erasmus:
echo     uv run erasmus.py
goto :eof

:main
call :detect_os
call :check_python
call :check_prerequisites
call :install_uv
call :setup_env
call :init_watcher
echo Installation complete!
echo Erasmus has been initialized with your IDE environment: !IDE_ENV!
exit /b %ERRORLEVEL%

:start
call :main
exit /b %ERRORLEVEL%
