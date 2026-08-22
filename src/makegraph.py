#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
makegraph.py
------------
MakeGraph2022 호환 재구현 (Phase 1: 실용적 현대화)

한국학중앙연구원 디지털인문학연구소의 makeGraph2022.exe가 사용하던
온톨로지 설계 스크립트(.lst)를 읽어, 
Vis.js Network 기반의 네트워크 그래프 HTML 파일을 생성한다.

이 구현은 공개된 사용 설명서(README.md 및 매뉴얼 문서)에 기술된
입력 문법과 동작 규칙만을 근거로 한 클린룸(clean-room) 재구현이며,
원본 실행파일의 코드를 역컴파일하거나 그대로 옮긴 것이 아니다.

사용법:
    python makegraph.py sample.lst
    python makegraph.py sample.lst -o result.html
    python makegraph.py sample.lst --vis-js vis-network.min.js
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 상수 / 스펙 정의
# ---------------------------------------------------------------------------

VALID_SECTIONS = {"#Project", "#Class", "#Relation", "#Nodes", "#Links", "#End"}
SECTION_ORDER = ["#Project", "#Class", "#Relation", "#Nodes", "#Links", "#End"]

VALID_SHAPES = {"box", "circle", "ellipse", "star", "triangle", "square", "dot", "text"}
VALID_ARROWS = {"arrow", "inverse", "both", "moving-arrows", "line", "sequence"}
VALID_NODE_DISPLAY = {"0", "1", "2"}
VALID_RELATION_DISPLAY = {"0", "1", "2", "3"}

DEFAULT_VIS_CDN = "https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"

SEQUENCE_COLOR = "#e67e22"  # 굵은 오렌지색 (sequence 전용)


# ---------------------------------------------------------------------------
# 데이터 모델
# ---------------------------------------------------------------------------

@dataclass
class ParseError:
    message: str
    line_no: Optional[int] = None

    def __str__(self) -> str:
        if self.line_no is not None:
            return f"[{self.line_no}행] {self.message}"
        return self.message


@dataclass
class ClassDef:
    name: str
    color: Optional[str] = None
    shape: Optional[str] = None


@dataclass
class RelationDef:
    name: str
    desc: Optional[str] = None
    arrow: str = "arrow"
    display: str = "1"


@dataclass
class NodeDef:
    node_id: str
    cls: str
    label: str
    url: Optional[str] = None
    icon: Optional[str] = None
    display: str = "1"


@dataclass
class LinkDef:
    domain: str
    range_: str
    relation: str


@dataclass
class ParseResult:
    project_lines: List[Tuple[str, str]] = field(default_factory=list)
    classes: Dict[str, ClassDef] = field(default_factory=dict)
    relations: Dict[str, RelationDef] = field(default_factory=dict)
    nodes: Dict[str, NodeDef] = field(default_factory=dict)
    links: List[LinkDef] = field(default_factory=list)
    errors: List[ParseError] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0


# ---------------------------------------------------------------------------
# 파서
# ---------------------------------------------------------------------------

def split_fields(line: str) -> List[str]:
    """공백(스페이스/탭 1개 이상)을 구분자로 필드를 분리한다."""
    return [f for f in re.split(r"\s+", line.strip()) if f != ""]


def parse_lst(text: str) -> ParseResult:
    result = ParseResult()
    current_section: Optional[str] = None
    seen_end = False

    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        stripped = raw_line.strip()
        if stripped == "":
            continue
        if seen_end:
            # #End 이후의 내용은 무시한다 (원본 스펙상 종료 표시자)
            continue

        # 섹션 헤더
        if stripped.startswith("#"):
            if stripped not in VALID_SECTIONS:
                result.errors.append(ParseError(
                    f"알 수 없는 섹션 이름입니다: '{stripped}'. "
                    f"허용된 섹션: {', '.join(SECTION_ORDER)}", line_no))
                current_section = None
                continue
            current_section = stripped
            if stripped == "#End":
                seen_end = True
            continue

        if current_section is None:
            result.errors.append(ParseError(
                f"섹션이 지정되지 않은 상태에서 데이터가 발견되었습니다: '{stripped}'",
                line_no))
            continue

        if "'" in stripped:
            result.errors.append(ParseError(
                f"홑따옴표(')는 사용할 수 없습니다: '{stripped}'", line_no))
            continue

        _parse_section_line(result, current_section, stripped, line_no)

    # 구조적 검증 (섹션 간 참조 무결성은 각 라인 파싱 중 이미 처리됨)
    if not result.project_lines and "#Project" not in text:
        pass  # #Project 자체는 선택적으로 취급 (원본 문서상 필수 표시는 없음)

    return result


def _parse_section_line(result: ParseResult, section: str, stripped: str, line_no: int) -> None:
    if section == "#Project":
        m = re.match(r"^(h[1-7])\s+(.*)$", stripped)
        if m:
            result.project_lines.append((m.group(1), m.group(2)))
        else:
            result.project_lines.append(("h1", stripped))

    elif section == "#Class":
        fields = split_fields(stripped)
        name = fields[0]
        color = fields[1] if len(fields) > 1 else None
        shape = fields[2] if len(fields) > 2 else None
        if shape and shape not in VALID_SHAPES:
            result.errors.append(ParseError(
                f"Class '{name}'에 정의되지 않은 shape '{shape}'가 사용되었습니다. "
                f"(허용: {', '.join(sorted(VALID_SHAPES))})", line_no))
            shape = None
        if name in result.classes:
            result.errors.append(ParseError(f"Class '{name}'가 중복 정의되었습니다.", line_no))
        result.classes[name] = ClassDef(name=name, color=color, shape=shape)

    elif section == "#Relation":
        fields = split_fields(stripped)
        name = fields[0]
        desc = fields[1] if len(fields) > 1 else None
        arrow = fields[2] if len(fields) > 2 else "arrow"
        display = fields[3] if len(fields) > 3 else "1"
        if arrow not in VALID_ARROWS:
            result.errors.append(ParseError(
                f"Relation '{name}'에 정의되지 않은 화살표 모양 '{arrow}'가 사용되었습니다. "
                f"(허용: {', '.join(VALID_ARROWS)})", line_no))
            arrow = "arrow"
        if display not in VALID_RELATION_DISPLAY:
            result.errors.append(ParseError(
                f"Relation '{name}'의 표시 옵션 '{display}'은 올바르지 않습니다. (허용: 0/1/2/3)",
                line_no))
            display = "1"
        if name in result.relations:
            result.errors.append(ParseError(f"Relation '{name}'가 중복 정의되었습니다.", line_no))
        result.relations[name] = RelationDef(name=name, desc=desc, arrow=arrow, display=display)

    elif section == "#Nodes":
        fields = split_fields(stripped)
        if len(fields) < 3:
            result.errors.append(ParseError(
                f"Node 정의에 필요한 필드(ID, Class, Label)가 부족합니다: '{stripped}'", line_no))
            return
        node_id, cls, label = fields[0], fields[1], fields[2]
        url = fields[3] if len(fields) > 3 else None
        icon = fields[4] if len(fields) > 4 else None
        display = fields[5] if len(fields) > 5 else "1"
        if url == "null":
            url = None
        if icon == "null":
            icon = None
        if display not in VALID_NODE_DISPLAY:
            result.errors.append(ParseError(
                f"Node '{node_id}'의 표시 옵션 '{display}'은 올바르지 않습니다. (허용: 0/1/2)",
                line_no))
            display = "1"
        if cls not in result.classes:
            result.errors.append(ParseError(
                f"Node '{node_id}'에 정의되지 않은 Class '{cls}'가 사용되었습니다.", line_no))
        if node_id in result.nodes:
            result.errors.append(ParseError(f"Node '{node_id}'가 중복 정의되었습니다.", line_no))
        result.nodes[node_id] = NodeDef(
            node_id=node_id, cls=cls, label=label, url=url, icon=icon, display=display)

    elif section == "#Links":
        fields = split_fields(stripped)
        if len(fields) < 3:
            result.errors.append(ParseError(
                f"Link 정의에 필요한 필드(Domain, Range, Relation)가 부족합니다: '{stripped}'",
                line_no))
            return
        domain, rng, rel = fields[0], fields[1], fields[2]
        if domain not in result.nodes:
            result.errors.append(ParseError(
                f"Link에서 정의되지 않은 Node '{domain}'이 사용되었습니다.", line_no))
        if rng not in result.nodes:
            result.errors.append(ParseError(
                f"Link에서 정의되지 않은 Node '{rng}'이 사용되었습니다.", line_no))
        if rel not in result.relations:
            result.errors.append(ParseError(
                f"Link에서 정의되지 않은 Relation '{rel}'이 사용되었습니다.", line_no))
        result.links.append(LinkDef(domain=domain, range_=rng, relation=rel))


# ---------------------------------------------------------------------------
# Vis.js 데이터 변환
# ---------------------------------------------------------------------------

def build_vis_data(result: ParseResult) -> Tuple[List[dict], List[dict]]:
    vis_nodes: List[dict] = []
    for node_id, node in result.nodes.items():
        cls = result.classes.get(node.cls)
        vis_node: dict = {"id": node_id, "label": node.label}

        # 색상/모양 (Class 기준)
        if cls and cls.color:
            vis_node["color"] = cls.color
        if cls and cls.shape:
            vis_node["shape"] = cls.shape

        # 아이콘 / 표시 옵션
        if node.icon:
            if node.display == "2":
                vis_node["shape"] = "circularImage"
                vis_node["image"] = node.icon
            elif node.display == "1":
                vis_node["shape"] = "image"
                vis_node["image"] = node.icon
            else:  # display == "0": 기본 모양 유지, hover 시에만 아이콘
                vis_node["shape"] = cls.shape if (cls and cls.shape) else "dot"
                vis_node["_hoverIcon"] = node.icon

        # 하이퍼링크 (title 툴팁에 표시, 밑줄로 클릭 가능함을 암시)
        title = html.escape(node.label)
        if node.url:
            title = f'<u>{html.escape(node.label)}</u>'
        if node.icon and node.display == "0":
            title += f'<br><img src="{html.escape(node.icon)}" height="40">'
        vis_node["title"] = title

        if node.url:
            vis_node["_url"] = node.url

        vis_nodes.append(vis_node)

    vis_edges: List[dict] = []
    for link in result.links:
        rel = result.relations.get(link.relation)
        edge: dict = {"from": link.domain, "to": link.range_}

        arrow_style = rel.arrow if rel else "arrow"
        if arrow_style == "arrow":
            edge["arrows"] = "to"
        elif arrow_style == "inverse":
            edge["arrows"] = "from"
        elif arrow_style == "both":
            edge["arrows"] = "to,from"
        elif arrow_style == "moving-arrows":
            edge["arrows"] = "to"
            edge["dashes"] = True
        elif arrow_style == "line":
            pass  # 화살표 없음
        elif arrow_style == "sequence":
            edge["arrows"] = "to"
            edge["color"] = SEQUENCE_COLOR
            edge["width"] = 4

        # 라벨 표시 옵션
        name = rel.name if rel else link.relation
        desc = (rel.desc if rel else None) or name
        display = rel.display if rel else "1"
        if display == "0":
            pass  # 라벨 없음
        elif display == "1":
            edge["label"] = name
            edge["title"] = desc
        elif display == "2":
            edge["label"] = desc
            edge["title"] = name
        elif display == "3":
            edge["label"] = f"{name} ({desc})"

        vis_edges.append(edge)

    return vis_nodes, vis_edges


# ---------------------------------------------------------------------------
# HTML 렌더링
# ---------------------------------------------------------------------------

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<script src="{vis_js_src}"></script>
<style>
  html, body {{ margin: 0; padding: 0; height: 100%; font-family: "Malgun Gothic", "Apple SD Gothic Neo", sans-serif; }}
  #project-header {{ padding: 10px 16px; border-bottom: 1px solid #ddd; }}
  #network {{ width: 100%; height: calc(100vh - 60px); border: none; }}
  #layout-controls {{ position: fixed; bottom: 16px; right: 16px; z-index: 10; }}
  #layout-controls button {{
    margin-left: 6px; padding: 6px 12px; border: 1px solid #999; background: #fff;
    border-radius: 4px; cursor: pointer; font-size: 13px;
  }}
  #layout-controls button.active {{ background: #333; color: #fff; }}
</style>
</head>
<body>
<div id="project-header">{project_html}</div>
<div id="network"></div>
<div id="layout-controls">
  <button id="btn-normal" class="active" onclick="setLayout('normal')">Normal</button>
  <button id="btn-horizontal" onclick="setLayout('horizontal')">Horizontal</button>
  <button id="btn-vertical" onclick="setLayout('vertical')">Vertical</button>
</div>

<script type="text/javascript">
  var nodesData = {nodes_json};
  var edgesData = {edges_json};

  var nodes = new vis.DataSet(nodesData);
  var edges = new vis.DataSet(edgesData);

  var container = document.getElementById('network');
  var data = {{ nodes: nodes, edges: edges }};

  var baseOptions = {{
    nodes: {{
      font: {{ size: 14 }},
      borderWidth: 1
    }},
    edges: {{
      font: {{ size: 11, align: 'middle' }},
      smooth: {{ type: 'dynamic' }}
    }},
    physics: {{
      stabilization: true,
      barnesHut: {{ gravitationalConstant: -6000, springLength: 140 }}
    }},
    interaction: {{ hover: true, tooltipDelay: 120 }},
    layout: {{ improvedLayout: true }}
  }};

  var layoutOptions = {{
    normal: {{ layout: {{ hierarchical: false }}, physics: {{ enabled: true }} }},
    horizontal: {{
      layout: {{ hierarchical: {{ enabled: true, direction: 'LR', sortMethod: 'directed' }} }},
      physics: {{ enabled: false }}
    }},
    vertical: {{
      layout: {{ hierarchical: {{ enabled: true, direction: 'UD', sortMethod: 'directed' }} }},
      physics: {{ enabled: false }}
    }}
  }};

  var network = new vis.Network(container, data, baseOptions);

  function setLayout(kind) {{
    network.setOptions(layoutOptions[kind]);
    ['normal', 'horizontal', 'vertical'].forEach(function (k) {{
      document.getElementById('btn-' + k).classList.toggle('active', k === kind);
    }});
  }}

  // 하이퍼링크: 노드 클릭 시 지정된 URL로 이동
  network.on('click', function (params) {{
    if (params.nodes.length === 1) {{
      var node = nodes.get(params.nodes[0]);
      if (node && node._url) {{
        window.open(node._url, '_blank');
      }}
    }}
  }});
</script>
</body>
</html>
"""

ERROR_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>MakeGraph - 오류</title>
<script src="{vis_js_src}"></script>
<style>
  html, body {{ margin: 0; padding: 0; height: 100%; font-family: "Malgun Gothic", "Apple SD Gothic Neo", sans-serif; }}
  #error-list {{ padding: 16px; color: #b00020; }}
  #error-list li {{ margin-bottom: 6px; }}
  #network {{ width: 100%; height: 60vh; border-top: 1px solid #ddd; }}
</style>
</head>
<body>
<h2 style="padding: 16px 16px 0;">네트워크 그래프 생성 오류</h2>
<div id="error-list">
  <ul>
    {error_items}
  </ul>
</div>
<div id="network"></div>
<script type="text/javascript">
  var nodes = new vis.DataSet({error_nodes_json});
  var edges = new vis.DataSet([]);
  var container = document.getElementById('network');
  var network = new vis.Network(container, {{ nodes: nodes, edges: edges }}, {{
    nodes: {{ shape: 'box', color: {{ background: '#ffe0e0', border: '#b00020' }}, font: {{ size: 13 }} }},
    physics: {{ enabled: true }}
  }});
</script>
</body>
</html>
"""


def render_project_html(project_lines: List[Tuple[str, str]]) -> str:
    if not project_lines:
        return ""
    return "\n".join(f"<{level}>{html.escape(text)}</{level}>" for level, text in project_lines)


def render_html(result: ParseResult, vis_js_src: str) -> str:
    nodes, edges = build_vis_data(result)
    title = result.project_lines[0][1] if result.project_lines else "MakeGraph Network"
    return HTML_TEMPLATE.format(
        title=html.escape(title),
        vis_js_src=vis_js_src,
        project_html=render_project_html(result.project_lines),
        nodes_json=json.dumps(nodes, ensure_ascii=False),
        edges_json=json.dumps(edges, ensure_ascii=False),
    )


def render_error_html(errors: List[ParseError], vis_js_src: str) -> str:
    error_items = "\n    ".join(f"<li>{html.escape(str(e))}</li>" for e in errors)
    error_nodes = [
        {"id": i, "label": f"오류 {i + 1}\n{str(e)[:60]}"}
        for i, e in enumerate(errors)
    ]
    return ERROR_HTML_TEMPLATE.format(
        vis_js_src=vis_js_src,
        error_items=error_items,
        error_nodes_json=json.dumps(error_nodes, ensure_ascii=False),
    )


# ---------------------------------------------------------------------------
# CLI (이 구현에 대한 자세한 정보는 기존 저장소 makeGraph2026_refined에서 확인할 수 있다.)
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="makegraph.py",
        description="MakeGraph2022 호환 재구현: .lst 온톨로지 스크립트를 Vis.js 네트워크 그래프 HTML로 변환합니다.")
    parser.add_argument("input", help="입력 .lst 파일 경로")
    parser.add_argument("-o", "--output", help="출력 HTML 파일 경로 (기본: 입력파일명.html)")
    parser.add_argument("--vis-js", dest="vis_js", default=None,
                         help="오프라인 사용을 위한 로컬 vis-network.min.js 경로")
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"오류: 입력 파일을 찾을 수 없습니다: {input_path}", file=sys.stderr)
        return 1

    output_path = Path(args.output) if args.output else input_path.with_suffix(".html")
    vis_js_src = args.vis_js if args.vis_js else DEFAULT_VIS_CDN

    try:
        raw_bytes = input_path.read_bytes()
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        errors = [ParseError(
            "스크립트 파일이 UTF-8 인코딩이 아닙니다. 에디터에서 UTF-8로 다시 저장하세요.")]
        output_path.write_text(render_error_html(errors, vis_js_src), encoding="utf-8")
        print(f"오류: {errors[0]}", file=sys.stderr)
        print(f"오류 리포트가 생성되었습니다: {output_path}")
        return 1

    result = parse_lst(text)

    if not result.ok:
        output_path.write_text(render_error_html(result.errors, vis_js_src), encoding="utf-8")
        print(f"{len(result.errors)}개의 오류가 발견되었습니다:", file=sys.stderr)
        for e in result.errors:
            print(f"  - {e}", file=sys.stderr)
        print(f"오류 리포트가 생성되었습니다: {output_path}")
        return 1

    html_out = render_html(result, vis_js_src)
    output_path.write_text(html_out, encoding="utf-8")
    print(f"생성 완료: {output_path}")
    print(f"  - Class: {len(result.classes)}개")
    print(f"  - Relation: {len(result.relations)}개")
    print(f"  - Node: {len(result.nodes)}개")
    print(f"  - Link: {len(result.links)}개")
    return 0


if __name__ == "__main__":
    sys.exit(main())
