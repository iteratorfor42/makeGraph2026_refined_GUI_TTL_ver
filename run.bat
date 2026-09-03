@echo off
REM run.bat — MakeGraph 앱을 소스에서 바로 실행한다 (exe를 만들지 않음).
REM 더블클릭하면: 필요한 패키지를 설치하고 GUI 창을 띄운다.

cd /d "%~dp0"
echo 필요한 패키지를 확인/설치합니다...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [오류] pip install에 실패했습니다. Python이 설치되어 있는지 확인하세요.
    pause
    exit /b 1
)

echo.
echo MakeGraph를 실행합니다...
python src\gui.py

pause
