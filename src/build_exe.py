#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_exe.py
------------
gui.py(더블클릭으로 실행되는 GUI 앱)를 Windows 실행파일(makegraph.exe)로
패키징한다. 실행하면 창이 뜨고, 그 안에서 '파일 열기'로 .lst 또는 .ttl을
불러오는 방식이다 (Protege와 유사한 사용성).

반드시 Windows 환경에서 실행해야 한다 (PyInstaller는 크로스 컴파일을
지원하지 않으므로, Linux/Mac에서 실행하면 그 OS용 실행파일이 만들어진다).

사용법:
    python build_exe.py

결과:
    dist/makegraph.exe   (단일 파일, GUI 프로그램 — 콘솔창 없이 실행됨)

요구 사항:
    - Windows 10/11
    - Python 3.9 이상 (64bit 권장, tkinter 포함된 표준 배포판)
    - 인터넷 연결 (최초 1회, pyinstaller/rdflib 설치용)
"""

import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent          # src/
ROOT = HERE.parent                               # 저장소 루트
ENTRY_SCRIPT = HERE / "gui.py"
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"
SPEC_FILE = HERE / "makegraph.spec"


def run(cmd: list[str]) -> None:
    print(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def ensure_pyinstaller() -> None:
    try:
        import PyInstaller  # noqa: F401
        print("PyInstaller가 이미 설치되어 있습니다.")
    except ImportError:
        print("PyInstaller가 없습니다. 설치를 진행합니다...")
        run([sys.executable, "-m", "pip", "install", "--upgrade", "pyinstaller"])


def ensure_rdflib() -> None:
    try:
        import rdflib  # noqa: F401
        print("rdflib이 이미 설치되어 있습니다.")
    except ImportError:
        print(".ttl 파일 지원을 위해 rdflib을 설치합니다...")
        run([sys.executable, "-m", "pip", "install", "--upgrade", "rdflib"])


def clean_previous_build() -> None:
    for path in (DIST_DIR, BUILD_DIR, SPEC_FILE):
        if path.is_dir():
            shutil.rmtree(path)
            print(f"이전 빌드 삭제: {path}")
        elif path.is_file():
            path.unlink()
            print(f"이전 spec 삭제: {path}")


def build() -> None:
    if not ENTRY_SCRIPT.exists():
        print(f"오류: {ENTRY_SCRIPT} 파일을 찾을 수 없습니다.", file=sys.stderr)
        sys.exit(1)

    run([
        sys.executable, "-m", "PyInstaller",
        "--onefile",                 # 단일 exe 파일로 묶기
        "--windowed",                # GUI 프로그램 (콘솔창 띄우지 않음)
        "--name", "makegraph",
        "--distpath", str(DIST_DIR),
        "--workpath", str(BUILD_DIR),
        "--specpath", str(HERE),
        "--collect-all", "rdflib",   # rdflib의 플러그인/데이터 파일까지 포함
        str(ENTRY_SCRIPT),
    ])

    exe_path = DIST_DIR / "makegraph.exe"
    if exe_path.exists():
        print(f"\n빌드 완료: {exe_path}")
        print("사용법: makegraph.exe를 더블클릭해서 실행한 뒤,")
        print("        '파일 열기'로 .lst 또는 .ttl 파일을 불러오세요.")
        print("        (탐색기에서 .lst/.ttl 파일을 exe에 드래그해도 바로 열립니다.)")
    else:
        print("빌드는 종료되었지만 makegraph.exe를 찾지 못했습니다. "
              "위 PyInstaller 로그를 확인하세요.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    ensure_pyinstaller()
    ensure_rdflib()
    clean_previous_build()
    build()
