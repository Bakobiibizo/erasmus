#!/usr/bin/env python3
"""
Script to build the complete release package.
This combines the functionality of embed_erasmus.py and main.py to create
both the shell installer and Windows batch installer in a single command.
"""

import os
import sys
import base64
import json
import hashlib
from pathlib import Path
from .packager import ScriptPackager

def build_single_file():
    """Build a single-file executable from the project."""
    project_root = Path.cwd()
    version_path = project_root / 'version.json'
    
    # Check if version.json exists
    if not version_path.exists():
        print(f"Error: {version_path} not found")
        print("\nTo fix this error:")
        print("1. Make sure you're running this script from the project root directory")
        print("2. Create a version.json file with a 'version' field")
        print("   Example: {\"version\": \"0.1.0\"}")
        return None, None
    
    # Get version from version.json
    with open(version_path, 'r') as f:
        version_data = json.load(f)
        version = version_data.get('version', '0.0.0')
    
    print(f"Building single-file executable for version {version}")
    
    # Create version-specific directory
    release_dir = project_root / 'release'
    version_dir = release_dir / f'v{version}'
    version_dir.mkdir(parents=True, exist_ok=True)
    
    # Package the scripts
    packager = ScriptPackager(project_root)
    output_path = version_dir / f'erasmus_v{version}.py'
    
    try:
        packager.package_scripts(output_path)
        print(f"Successfully created single-file executable: {output_path}")
        return version, version_dir
    except Exception as e:
        print(f"Error packaging scripts: {e}", file=sys.stderr)
        return None, None

def embed_erasmus():
    """Embed the single-file executable into the installer script."""
    # First build the single file
    result = build_single_file()
    if not isinstance(result, tuple):
        return result
        
    version, version_dir = result
    
    # Define paths
    project_root = Path.cwd()
    single_file = version_dir / f'erasmus_v{version}.py'
    install_path = project_root / 'scripts' / 'install.sh'
    hash_file_path = version_dir / f'erasmus_v{version}.sha256'
    installer_path = version_dir / f'erasmus_v{version}.sh'
    
    # Check if required files exist
    if not single_file.exists():
        print(f"Error: {single_file} not found")
        return 1
    
    if not install_path.exists():
        print(f"Error: {install_path} not found")
        return 1
    
    # Read the installer script
    with open(install_path, 'r') as f:
        installer_content = f.read()
    
    # Read and encode the single file
    with open(single_file, 'rb') as f:
        script_content = f.read()
        # Calculate SHA-256 hash for verification
        script_hash = hashlib.sha256(script_content).hexdigest()
        encoded_content = base64.b64encode(script_content).decode('utf-8')
    
    print(f"Generated SHA-256 hash: {script_hash}")
    
    # Save the hash to a file
    with open(hash_file_path, 'w') as hash_file:
        hash_file.write(f"{script_hash}  erasmus_v{version}.sh\n")
    print(f"Saved hash to: {hash_file_path}")
    
    # Create the combined installer
    with open(installer_path, 'w') as f:
        # Write the installer script
        f.write(installer_content)
        
        # Add the marker line and hash information
        f.write("\n\n# __ERASMUS_EMBEDDED_BELOW__\n")
        f.write("# The content below this line is the base64-encoded erasmus.py file\n")
        f.write(f"# SHA256_HASH={script_hash}\n")
        
        # Add exit command to prevent the shell from trying to execute the base64 content
        f.write("exit 0\n\n")
        
        # Add the base64-encoded content with a comment character to prevent execution
        f.write("# BEGIN_BASE64_CONTENT\n")
        
        # Split the encoded content into lines
        encoded_lines = [encoded_content[i:i+76] for i in range(0, len(encoded_content), 76)]
        for line in encoded_lines:
            f.write(f"# {line}\n")
            
        f.write("# END_BASE64_CONTENT")
    
    # Make the installer executable
    os.chmod(installer_path, 0o755)
    
    print(f"Successfully created installer: {installer_path}")
    return version, version_dir

def convert_to_batch(version, version_dir):
    """Convert shell scripts to batch files for Windows."""
    # Define paths
    batch_path = version_dir / f'erasmus_v{version}.bat'
    shell_path = version_dir / f'erasmus_v{version}.sh'
    
    # Validate paths
    if not version_dir.exists():
        print(f"Error: Version directory not found: {version_dir}")
        return 1
        
    if not shell_path.exists():
        print(f"Error: Shell installer not found: {shell_path}")
        return 1
    
    print(f"Creating Windows batch installer: {batch_path}")
    
    # Create batch file
    with open(batch_path, 'w') as f:
        f.write("@echo off\n")
        f.write("setlocal enabledelayedexpansion\n\n")
        
        f.write(":detect_os\n")
        f.write('set "OS=Unknown"\n')
        f.write('for /f "tokens=* usebackq" %%i in (`ver`) do set "VER_OUT=%%i"\n')
        f.write('echo !VER_OUT! | findstr /i "Windows" >nul 2>&1 && (\n')
        f.write('    set "OS=Windows"\n')
        f.write('    goto :eof\n')
        f.write(')\n')
        f.write('echo !VER_OUT! | findstr /i "Darwin" >nul 2>&1 && (\n')
        f.write('    set "OS=macOS"\n')
        f.write('    goto :eof\n')
        f.write(')\n')
        f.write('echo !VER_OUT! | findstr /i "Linux" >nul 2>&1 && (\n')
        f.write('    set "OS=Linux"\n')
        f.write('    goto :eof\n')
        f.write(')\n')
        f.write('goto :eof\n\n')
        
        f.write(":check_python\n")
        f.write('set "PYTHON_CMD="\n')
        f.write('where python.exe >nul 2>&1 && set "PYTHON_CMD=python.exe"\n')
        f.write('if "!PYTHON_CMD!"=="" (\n')
        f.write('    where python3.exe >nul 2>&1 && set "PYTHON_CMD=python3.exe"\n')
        f.write(')\n')
        f.write('if "!PYTHON_CMD!"=="" (\n')
        f.write('    echo Error: Python is not installed!\n')
        f.write('    echo Please install Python 3.8+ before proceeding.\n')
        f.write('    exit /b 1\n')
        f.write(')\n\n')
        f.write('for /f "tokens=* usebackq" %%i in (`!PYTHON_CMD! -c "import sys; print(sys.version_info.major)"`) do set "MAJOR=%%i"\n')
        f.write('for /f "tokens=* usebackq" %%i in (`!PYTHON_CMD! -c "import sys; print(sys.version_info.minor)"`) do set "MINOR=%%i"\n\n')
        f.write('if "!MAJOR!" lss "3" (\n')
        f.write('    echo Error: Python 3.8+ is required.\n')
        f.write('    exit /b 1\n')
        f.write(') else if "!MAJOR!" equ "3" (\n')
        f.write('    if "!MINOR!" lss "8" (\n')
        f.write('        echo Error: Python 3.8+ is required.\n')
        f.write('        exit /b 1\n')
        f.write('    )\n')
        f.write(')\n')
        f.write('goto :eof\n\n')
        
        f.write(":check_prerequisites\n")
        f.write('call :detect_os\n')
        f.write('if "!OS!"=="Windows" (\n')
        f.write('    echo Checking Windows prerequisites...\n')
        f.write('    where winget.exe >nul 2>&1 || (\n')
        f.write('        echo Installing winget...\n')
        f.write('        powershell -Command "Add-AppxPackage -RegisterByFamilyName -MainPackage Microsoft.DesktopAppInstaller_8wekyb3d8bbwe"\n')
        f.write('        where winget.exe >nul 2>&1 || (\n')
        f.write('            echo Failed to install winget. Please install it manually from the Microsoft Store.\n')
        f.write('            exit /b 1\n')
        f.write('        )\n')
        f.write('    )\n')
        f.write(') else if "!OS!"=="macOS" (\n')
        f.write('    echo Checking macOS prerequisites...\n')
        f.write('    where brew.exe >nul 2>&1 || (\n')
        f.write('        echo Homebrew is required but not installed.\n')
        f.write('        echo Please install Homebrew first: https://brew.sh\n')
        f.write('        exit /b 1\n')
        f.write('    )\n')
        f.write(') else if "!OS!"=="Linux" (\n')
        f.write('    echo Checking Linux prerequisites...\n')
        f.write('    where curl.exe >nul 2>&1 || (\n')
        f.write('        echo Installing curl...\n')
        f.write('        where apt-get.exe >nul 2>&1 && (\n')
        f.write('            apt-get update && apt-get install -y curl\n')
        f.write('        ) || (\n')
        f.write('            where yum.exe >nul 2>&1 && (\n')
        f.write('                yum install -y curl\n')
        f.write('            ) || (\n')
        f.write('                echo Could not install curl. Please install it manually.\n')
        f.write('                exit /b 1\n')
        f.write('            )\n')
        f.write('        )\n')
        f.write('    )\n')
        f.write(')\n')
        f.write('goto :eof\n\n')
        
        f.write(":install_uv\n")
        f.write('echo Installing uv package manager...\n')
        f.write('if "!OS!"=="Windows" (\n')
        f.write('    winget install --id=astral-sh.uv -e\n')
        f.write(') else if "!OS!"=="macOS" (\n')
        f.write('    brew install uv\n')
        f.write(') else if "!OS!"=="Linux" (\n')
        f.write('    curl -LsSf https://astral.sh/uv/install.sh | sh\n')
        f.write(') else (\n')
        f.write('    echo Unsupported operating system: !OS!\n')
        f.write('    exit /b 1\n')
        f.write(')\n\n')
        f.write('where uv.exe >nul 2>&1 || (\n')
        f.write('    echo Failed to install uv package manager!\n')
        f.write('    exit /b 1\n')
        f.write(')\n\n')
        f.write('echo Installation complete!\n')
        f.write('echo You can now run: uv run erasmus.py\n')
        f.write('goto :eof\n\n')
        
        f.write(":setup_env\n")
        f.write('echo Creating environment files...\n\n')
        f.write(':: Create .env.example\n')
        f.write('(\n')
        f.write('echo IDE_ENV=\n')
        f.write('echo GIT_TOKEN=\n')
        f.write('echo OPENAI_API_KEY=\n')
        f.write(') > .env.example\n\n')
        f.write(':: Prompt for IDE environment\n')
        f.write('echo Please enter your IDE environment (cursor/windsurf):\n')
        f.write('set /p "IDE_ENV="\n\n')
        f.write(':: Create .env\n')
        f.write('(\n')
        f.write('echo IDE_ENV=!IDE_ENV!\n')
        f.write('echo GIT_TOKEN=\n')
        f.write('echo OPENAI_API_KEY=\n')
        f.write(') > .env\n\n')
        f.write('echo Environment files created successfully\n')
        f.write('goto :eof\n\n')
        
        f.write(":init_watcher\n")
        f.write('echo Initializing erasmus...\n\n')
        f.write(':: Extract erasmus.py from the embedded content\n')
        f.write('echo Extracting erasmus.py...\n\n')
        f.write(':: Find the SHA256 hash in this script\n')
        f.write('for /f "tokens=* usebackq" %%i in (`findstr /C:"# SHA256_HASH=" "%~f0"`) do set "EXPECTED_HASH=%%i"\n')
        f.write('set "EXPECTED_HASH=!EXPECTED_HASH:# SHA256_HASH=!"\n\n')
        f.write(':: Extract the base64 content between markers\n')
        f.write('powershell -Command "$content = Get-Content \'%~f0\' | Select-String -Pattern \\"# BEGIN_BASE64_CONTENT\\",\\"# END_BASE64_CONTENT\\" -Context 0,10000 | ForEach-Object { $_.Context.PostContext } | Where-Object { $_ -notmatch \\"BEGIN_BASE64_CONTENT|END_BASE64_CONTENT\\" } | ForEach-Object { $_ -replace \\"^# \\", \\"\\" }; $content | Set-Content -Encoding ASCII temp_base64.txt"\n\n')
        f.write(':: Decode the base64 content\n')
        f.write('powershell -Command "$content = Get-Content -Encoding ASCII temp_base64.txt; $content = $content -join \\"\\"; [System.IO.File]::WriteAllBytes(\\"erasmus.py\\", [System.Convert]::FromBase64String($content))"\n\n')
        f.write(':: Verify the SHA256 hash\n')
        f.write('powershell -Command "$hash = Get-FileHash -Algorithm SHA256 -Path erasmus.py | Select-Object -ExpandProperty Hash; if ($hash -eq \\"!EXPECTED_HASH!\\") { Write-Host \\"SHA256 hash verified: $hash\\" } else { Write-Host \\"Error: SHA256 hash verification failed!\\" -ForegroundColor Red; Write-Host \\"Expected: !EXPECTED_HASH!\\" -ForegroundColor Red; Write-Host \\"Actual: $hash\\" -ForegroundColor Red; exit 1 }"\n\n')
        f.write(':: Run the erasmus setup with IDE environment\n')
        f.write('echo Running erasmus setup...\n')
        f.write('uv run erasmus.py --setup !IDE_ENV!\n\n')
        f.write('echo Erasmus initialized successfully!\n')
        f.write('echo To run Erasmus:\n')
        f.write('echo     uv run erasmus.py\n')
        f.write('goto :eof\n\n')
        
        f.write(":main\n")
        f.write('call :detect_os\n')
        f.write('call :check_python\n')
        f.write('call :check_prerequisites\n')
        f.write('call :install_uv\n')
        f.write('call :setup_env\n')
        f.write('call :init_watcher\n')
        f.write('echo Installation complete!\n')
        f.write('echo Erasmus has been initialized with your IDE environment: !IDE_ENV!\n')
        f.write('exit /b %ERRORLEVEL%\n\n')
        
        f.write(":start\n")
        f.write('call :main\n')
        f.write('exit /b %ERRORLEVEL%\n')
    
    print(f"Successfully created batch installer: {batch_path}")
    return 0

def main():
    """Main function to build the complete release package."""
    try:
        print("Building complete release package...")
        
        # Step 1: Build single file and embed into installer
        result = embed_erasmus()
        if isinstance(result, tuple):
            version, version_dir = result
        else:
            print("Failed to create installer")
            return 1
        
        # Step 2: Convert to batch file
        result = convert_to_batch(version, version_dir)
        if result != 0:
            print("Failed to create Windows batch installer")
            return 1
        
        print("\nRelease package built successfully!")
        print(f"Single-file executable: {version_dir}/erasmus_v{version}.py")
        print(f"Shell installer: {version_dir}/erasmus_v{version}.sh")
        print(f"Windows installer: {version_dir}/erasmus_v{version}.bat")
        print(f"SHA256 hash file: {version_dir}/erasmus_v{version}.sha256")
        
        return 0
    except ImportError:
        print("Error: Required module not found.", file=sys.stderr)
        print("Please make sure all required modules are installed.", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error building release package: {e}", file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main()) 