# -*- coding: utf-8 -*-
"""
gui.py
------
MakeGraph GUI — Protege처럼 프로그램을 먼저 실행한 뒤,
메뉴/버튼으로 .lst 또는 .ttl 온톨로지 파일을 불러와 
네트워크 그래프를 생성하고 브라우저로 보여준다.

빌드 시 이 파일을 진입점(entry point)으로 사용한다. 
[build_exe.py 참고]

지원 파일:
  - .lst : MakeGraph2022 온톨로지 스크립트 (makegraph.py의 parse_lst 사용)
  - .ttl : Turtle RDF/OWL 온톨로지 (ttl_loader.py의 load_ttl_as_parse_result 사용)
"""

from __future__ import annotations

import subprocess
import sys
import threading
import traceback
import webbrowser
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

import makegraph as mg

APP_TITLE = "MakeGraph — 온톨로지 네트워크 그래프 뷰어"

# PyInstaller로 묶인 실행파일에서는 sys.frozen == True.
# 이 경우 rdflib은 build_exe.py가 이미 exe 안에 포함시켰어야 하므로
# 여기서 pip install을 시도하지 않는다 (frozen exe에는 pip이 없음).
IS_FROZEN = getattr(sys, "frozen", False)


class MakeGraphApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("760x520")
        self.minsize(520, 360)

        self.current_path: Path | None = None
        self.last_html_path: Path | None = None

        self._build_menu()
        self._build_widgets()

    # -- UI 구성 -----------------------------------------------------------

    def _build_menu(self) -> None:
        menubar = tk.Menu(self)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="파일 열기 (.lst / .ttl)...",
                               command=self.open_file, accelerator="Ctrl+O")
        file_menu.add_command(label="브라우저에서 결과 다시 열기",
                               command=self.open_in_browser)
        file_menu.add_separator()
        file_menu.add_command(label="종료", command=self.destroy)
        menubar.add_cascade(label="파일", menu=file_menu)

        self.config(menu=menubar)
        self.bind("<Control-o>", lambda _e: self.open_file())

    def _build_widgets(self) -> None:
        top = tk.Frame(self, padx=12, pady=12)
        top.pack(fill="x")

        self.path_var = tk.StringVar(value="열린 파일 없음")
        tk.Label(top, textvariable=self.path_var, anchor="w",
                 fg="#555").pack(side="left", fill="x", expand=True)

        tk.Button(top, text="파일 열기...", width=14,
                  command=self.open_file).pack(side="right", padx=(6, 0))
        tk.Button(top, text="브라우저에서 보기", width=16,
                  command=self.open_in_browser).pack(side="right")

        self.log = scrolledtext.ScrolledText(
            self, wrap="word", height=22, state="disabled",
            font=("Consolas", 10))
        self.log.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self._log(
            "MakeGraph에 오신 것을 환영합니다.\n"
            "위의 '파일 열기' 버튼으로 .lst 또는 .ttl 온톨로지 파일을 불러오세요.\n"
        )

    # -- 로그 --------------------------------------------------------------

    def _log(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _clear_log(self) -> None:
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    # -- 파일 열기 -----------------------------------------------------------

    def open_file(self) -> None:
        path_str = filedialog.askopenfilename(
            title="온톨로지 파일 선택",
            filetypes=[
                ("지원 파일 (.lst, .ttl)", "*.lst *.ttl"),
                ("MakeGraph 스크립트", "*.lst"),
                ("Turtle 온톨로지", "*.ttl"),
                ("모든 파일", "*.*"),
            ],
        )
        if not path_str:
            return
        self.load_path(Path(path_str))

    def load_path(self, path: Path) -> None:
        if not path.exists():
            messagebox.showerror(APP_TITLE, f"파일을 찾을 수 없습니다:\n{path}")
            return

        suffix = path.suffix.lower()
        if suffix not in (".lst", ".ttl"):
            messagebox.showerror(
                APP_TITLE,
                f"지원하지 않는 파일 형식입니다: {suffix}\n(.lst 또는 .ttl만 지원)")
            return

        # TTL은 rdflib이 필요하다. 메인 스레드에서 미리 확인/설치를 처리한 뒤
        # (팝업은 메인 스레드에서만 안전하게 띄울 수 있음) 백그라운드로 넘긴다.
        if suffix == ".ttl" and not self._ensure_ttl_support():
            return

        self.current_path = path
        self.path_var.set(str(path))
        self._clear_log()
        self._log(f"불러오는 중: {path.name}")

        # UI가 멈추지 않도록 백그라운드 스레드에서 처리
        threading.Thread(target=self._process_file, args=(path,), daemon=True).start()

    def _ensure_ttl_support(self) -> bool:
        """rdflib을 가져올 수 있는지 확인한다. 없으면 설치를 제안한다."""
        try:
            import rdflib  # noqa: F401
            return True
        except ImportError:
            pass

        if IS_FROZEN:
            messagebox.showerror(
                APP_TITLE,
                "이 실행파일에는 TTL 지원 모듈(rdflib)이 포함되어 있지 않습니다.\n"
                "src/build_exe.py로 다시 빌드해주세요 "
                "(rdflib이 자동으로 설치·포함됩니다).")
            return False

        install = messagebox.askyesno(
            APP_TITLE,
            "TTL 파일을 열려면 'rdflib' 패키지가 필요합니다.\n"
            "지금 설치할까요?\n\n"
            f"명령: {Path(sys.executable).name} -m pip install rdflib")
        if not install:
            self._log("rdflib이 설치되어 있지 않아 TTL 파일을 열 수 없습니다. "
                       "터미널에서 'pip install rdflib'을 실행한 뒤 다시 시도하세요.")
            return False

        self._log("rdflib 설치 중... (잠시 기다려주세요)")
        self.update_idletasks()
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", "rdflib"],
                check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as exc:
            messagebox.showerror(
                APP_TITLE,
                "rdflib 설치에 실패했습니다. 터미널에서 직접 실행해보세요:\n\n"
                f"{sys.executable} -m pip install rdflib\n\n"
                f"오류 내용:\n{exc.stderr}")
            return False

        try:
            import rdflib  # noqa: F401
        except ImportError:
            messagebox.showerror(
                APP_TITLE, "설치는 완료됐지만 rdflib을 불러오지 못했습니다. "
                           "프로그램을 재시작해보세요.")
            return False

        self._log("rdflib 설치 완료.")
        return True

    def _process_file(self, path: Path) -> None:
        try:
            suffix = path.suffix.lower()

            if suffix == ".lst":
                text = path.read_text(encoding="utf-8")
                result = mg.parse_lst(text)

            elif suffix == ".ttl":
                import ttl_loader  # 이 시점엔 _ensure_ttl_support()로 이미 보장됨
                result = ttl_loader.load_ttl_as_parse_result(path)

            else:
                self.after(0, self._log, f"지원하지 않는 파일 형식입니다: {suffix} "
                                          f"(.lst 또는 .ttl만 지원)")
                return

            if not result.ok:
                self.after(0, self._log, f"{len(result.errors)}개의 오류가 발견되었습니다:")
                for e in result.errors:
                    self.after(0, self._log, f"  - {e}")
                html_out = mg.render_error_html(result.errors, mg.DEFAULT_VIS_CDN)
            else:
                self.after(0, self._log,
                           f"Class {len(result.classes)}개, "
                           f"Relation {len(result.relations)}개, "
                           f"Node {len(result.nodes)}개, "
                           f"Link {len(result.links)}개")
                html_out = mg.render_html(result, mg.DEFAULT_VIS_CDN)

            output_path = path.with_suffix(".html")
            output_path.write_text(html_out, encoding="utf-8")
            self.last_html_path = output_path

            self.after(0, self._log, f"생성 완료: {output_path}")
            self.after(0, self.open_in_browser)

        except Exception as exc:  # noqa: BLE001
            self.after(0, self._log, f"오류 발생: {exc}")
            self.after(0, self._log, traceback.format_exc())

    # -- 브라우저 -----------------------------------------------------------

    def open_in_browser(self) -> None:
        if self.last_html_path and self.last_html_path.exists():
            webbrowser.open(self.last_html_path.resolve().as_uri())
        else:
            messagebox.showinfo(APP_TITLE, "먼저 파일을 열어 그래프를 생성하세요.")


def main() -> None:
    app = MakeGraphApp()
    # 탐색기에서 .lst/.ttl 파일을 실행파일에 드래그&드롭한 경우에도 동작하도록 지원
    if len(sys.argv) > 1:
        app.after(200, lambda: app.load_path(Path(sys.argv[1])))
    app.mainloop()


if __name__ == "__main__":
    main()
