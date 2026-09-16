# -*- coding: utf-8 -*-
"""
ttl_loader.py
-------------
Turtle(.ttl) 온톨로지 파일을 읽어 makegraph.py의 ParseResult와 동일한
데이터 구조(Class/Relation/Node/Link)로 변환한다.

.lst 문법에는 "Class/Relation/Node"라는 명시적 섹션이 있지만, 
TTL(RDF)에는 그런 구분이 없다. 따라서 다음과 같은 휴리스틱으로 대응한다.

  - Class    : rdf:type의 목적어로 쓰인 리소스
               (owl:Class, rdfs:Class 등 스키마 자체는 제외)
  - Node     : rdf:type을 가진 개체(individual)
  - Node 라벨 : rdfs:label이 있으면 사용, 없으면 URI의 로컬 이름(#, / 뒤)
  - Relation : 두 개체 사이를 잇는 predicate
               (rdf:type, rdfs:label, rdfs:comment, owl:sameAs 등은 제외)
  - Link     : subject/object가 모두 "개체로 인식된" 노드인 트리플만 사용

리터럴 값(문자열/숫자 등)을 갖는 datatype property는 노드로 만들지 않고
현재는 시각화에서 제외한다.
(그래프가 지저분해지는 것을 방지하고자 이렇게 한 것이며,
온톨로지 프로젝트 구상 단계에서 노드가 최소 50개 이상이 되었기에 시각화는 최대한 단순하게 했다.
시각화의 단순함과 복잡성은 지원자 포트폴리오 웹페이지
[일제강점기 독립운동 & 근대학교 온톨로지] 시각화 v1와 v10를 비교를 통해 명확히 알 수 있다.)

참고> 이 파일은 makegraph.py와 같은 폴더에 있어야 한다 (mg.ClassDef 등을 재사용).
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

try:
    import rdflib
    from rdflib import RDF, RDFS, OWL
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "TTL 파일을 읽으려면 rdflib 패키지가 필요합니다.\n"
        "설치: pip install rdflib"
    ) from exc

import makegraph as mg

IGNORED_PREDICATES = {RDF.type, RDFS.label, RDFS.comment, OWL.sameAs}

SCHEMA_TYPES = {
    OWL.Class, RDFS.Class, OWL.NamedIndividual,
    OWL.ObjectProperty, OWL.DatatypeProperty, OWL.Ontology,
    OWL.AnnotationProperty, RDF.Property,
}

# Class별 자동 색상/모양 배정용 팔레트 (.ttl에는 색상/모양 지정이 없으므로 자동 배정)
AUTO_COLORS = ["#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f",
               "#edc948", "#b07aa1", "#ff9da7", "#9c755f", "#bab0ac"]
AUTO_SHAPES = ["circle", "box", "ellipse", "triangle", "star", "square"]


def _local_name(uri) -> str:
    s = str(uri)
    if "#" in s:
        return s.rsplit("#", 1)[-1]
    return s.rsplit("/", 1)[-1]


def load_ttl_as_parse_result(path: Path) -> mg.ParseResult:
    result = mg.ParseResult()

    graph = rdflib.Graph()
    try:
        graph.parse(str(path), format="turtle")
    except Exception as exc:  # noqa: BLE001
        result.errors.append(mg.ParseError(f"TTL 파싱 실패: {exc}"))
        return result

    # 1) rdf:type 트리플에서 Class / 개체(Node) 후보 수집
    node_class_uri: Dict[rdflib.term.Identifier, rdflib.term.Identifier] = {}
    class_uris: Dict[rdflib.term.Identifier, str] = {}

    for s, _, o in graph.triples((None, RDF.type, None)):
        if o in SCHEMA_TYPES:
            continue
        class_uris.setdefault(o, _local_name(o))
        node_class_uri.setdefault(s, o)

    if not node_class_uri:
        result.errors.append(mg.ParseError(
            "TTL에서 rdf:type으로 클래스가 지정된 개체(instance)를 찾지 못했습니다. "
            "스키마 정의(TBox)만 있고 개체(ABox)가 없는 파일일 수 있습니다."))
        return result

    # 2) Class 정의 (자동 색상/모양 배정)
    for i, (uri, name) in enumerate(class_uris.items()):
        result.classes[name] = mg.ClassDef(
            name=name,
            color=AUTO_COLORS[i % len(AUTO_COLORS)],
            shape=AUTO_SHAPES[i % len(AUTO_SHAPES)],
        )

    # 3) rdfs:label 수집
    labels: Dict[rdflib.term.Identifier, str] = {}
    for s, _, o in graph.triples((None, RDFS.label, None)):
        labels[s] = str(o)

    # 4) Node 정의 + URI -> node_id 매핑 (동시에 구성)
    uri_to_id: Dict[rdflib.term.Identifier, str] = {}
    used_ids = set()

    for uri, cls_uri in node_class_uri.items():
        base_id = _local_name(uri)
        node_id = base_id
        suffix = 2
        while node_id in used_ids:
            node_id = f"{base_id}_{suffix}"
            suffix += 1
        used_ids.add(node_id)
        uri_to_id[uri] = node_id

        result.nodes[node_id] = mg.NodeDef(
            node_id=node_id,
            cls=class_uris[cls_uri],
            label=labels.get(uri, base_id),
            url=str(uri),   # 노드 클릭 시 원본 URI로 이동 (하이퍼링크 재활용)
            icon=None,
            display="1",
        )

    # 5) Relation 및 Link 정의 (개체-개체 사이의 object property만 사용)
    for s, p, o in graph:
        if p in IGNORED_PREDICATES:
            continue
        if not isinstance(o, rdflib.URIRef):
            continue  # 리터럴 값(datatype property)은 현재 시각화에서 제외
        if s not in uri_to_id or o not in uri_to_id:
            continue

        rel_name = _local_name(p)
        if rel_name not in result.relations:
            result.relations[rel_name] = mg.RelationDef(
                name=rel_name, desc=None, arrow="arrow", display="1")

        result.links.append(mg.LinkDef(
            domain=uri_to_id[s], range_=uri_to_id[o], relation=rel_name))

    return result
