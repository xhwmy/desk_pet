@echo off
setlocal
cd /d "%~dp0"
python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo Install build tools first: python -m pip install -r requirements-build.txt
    exit /b 1
)
python -m PyInstaller --noconfirm --clean --onefile --windowed ^
    --name Chiyan-DesktopPet ^
    --icon "%CD%\assets\chiyan.ico" ^
    --add-data "%CD%\assets\spritesheet.png;assets" ^
    --add-data "%CD%\assets\actions;assets/actions" ^
    --distpath dist --workpath build --specpath build app.py
if errorlevel 1 exit /b 1
echo Built: %~dp0dist\Chiyan-DesktopPet.exe
