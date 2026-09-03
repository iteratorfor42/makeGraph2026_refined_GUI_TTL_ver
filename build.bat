@echo off
REM build.bat — makegraph.exe를 빌드한다 (dist\makegraph.exe 생성).
REM 더블클릭하면: 필요한 패키지를 설치하고 PyInstaller로 exe를 만든다.

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
echo makegraph.exe를 빌드합니다 (몇 분 걸릴 수 있습니다)...
python src\build_exe.py

echo.
if exist dist\makegraph.exe (
    echo 빌드 완료: dist\makegraph.exe
) else (
    echo [오류] dist\makegraph.exe가 생성되지 않았습니다. 위 로그를 확인하세요.
)

pause
