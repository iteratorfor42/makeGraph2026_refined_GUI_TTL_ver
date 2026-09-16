# -*- coding: utf-8 -*-
"""
test_makegraph.py
------------------
src/makegraph.py, src/ttl_loader.py에 대한 검증용 테스트.

실행:
    python -m pytest tests/ -v
    (또는) python -m unittest discover -s tests -v
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import makegraph as mg  # noqa: E402
import ttl_loader  # noqa: E402

SAMPLES = ROOT / "samples"


class TestLstParser(unittest.TestCase):
    def test_basic_sections_parse_without_errors(self):
        text = (SAMPLES / "example.lst").read_text(encoding="utf-8")
        result = mg.parse_lst(text)
        self.assertTrue(result.ok, msg=[str(e) for e in result.errors])
        self.assertEqual(len(result.classes), 3)
        self.assertEqual(len(result.relations), 3)
        self.assertEqual(len(result.nodes), 5)
        self.assertEqual(len(result.links), 4)

    def test_unknown_section_name_is_error(self):
        result = mg.parse_lst("#Klass\nfoo\n")
        self.assertFalse(result.ok)
        self.assertIn("알 수 없는 섹션", result.errors[0].message)

    def test_undefined_class_in_nodes_is_error(self):
        text = "#Class\n사람\n\n#Nodes\n철수 동물 철수\n"
        result = mg.parse_lst(text)
        self.assertFalse(result.ok)
        self.assertTrue(any("Class" in e.message for e in result.errors))

    def test_undefined_relation_in_links_is_error(self):
        text = (
            "#Class\n사람\n\n#Relation\nlikes\n\n"
            "#Nodes\n철수 사람 철수\n영이 사람 영이\n\n"
            "#Links\n철수 영이 loves\n"
        )
        result = mg.parse_lst(text)
        self.assertFalse(result.ok)
        self.assertTrue(any("Relation" in e.message for e in result.errors))

    def test_undefined_node_in_links_is_error(self):
        text = (
            "#Class\n사람\n\n#Relation\nlikes\n\n"
            "#Nodes\n철수 사람 철수\n\n#Links\n철수 민수 likes\n"
        )
        result = mg.parse_lst(text)
        self.assertFalse(result.ok)
        self.assertTrue(any("Node" in e.message for e in result.errors))

    def test_single_quote_is_rejected(self):
        result = mg.parse_lst("#Class\n사람 'blue'\n")
        self.assertFalse(result.ok)
        self.assertTrue(any("홑따옴표" in e.message for e in result.errors))

    def test_null_url_and_icon_become_none(self):
        text = "#Class\n동물\n\n#Nodes\n보미 동물 보미 null files/Dog.png 2\n"
        result = mg.parse_lst(text)
        node = result.nodes["보미"]
        self.assertIsNone(node.url)
        self.assertEqual(node.icon, "files/Dog.png")
        self.assertEqual(node.display, "2")


class TestVisDataMapping(unittest.TestCase):
    def setUp(self):
        text = (
            "#Class\n사람 blue circle\n\n"
            "#Relation\nlikes 좋아한다 arrow 2\nisPreviousTo ~보다_먼저이다 sequence\n\n"
            "#Nodes\n철수 사람 철수\n영이 사람 영이\n\n"
            "#Links\n철수 영이 likes\n영이 철수 isPreviousTo\n"
        )
        self.result = mg.parse_lst(text)
        self.assertTrue(self.result.ok)
        self.nodes, self.edges = mg.build_vis_data(self.result)

    def test_class_color_and_shape_applied(self):
        n = next(n for n in self.nodes if n["id"] == "철수")
        self.assertEqual(n["color"], "blue")
        self.assertEqual(n["shape"], "circle")

    def test_relation_display_option_2_shows_description(self):
        e = next(e for e in self.edges if e["from"] == "철수")
        self.assertEqual(e["label"], "좋아한다")
        self.assertEqual(e["title"], "likes")

    def test_sequence_arrow_uses_orange_thick_style(self):
        e = next(e for e in self.edges if e["from"] == "영이")
        self.assertEqual(e["color"], mg.SEQUENCE_COLOR)
        self.assertEqual(e["width"], 4)


class TestTtlLoader(unittest.TestCase):
    def test_example_ttl_maps_to_classes_nodes_links(self):
        result = ttl_loader.load_ttl_as_parse_result(SAMPLES / "example.ttl")
        self.assertTrue(result.ok, msg=[str(e) for e in result.errors])
        self.assertEqual(set(result.classes.keys()), {"Person", "Animal", "Food"})
        self.assertEqual(len(result.nodes), 5)
        self.assertGreaterEqual(len(result.links), 4)
        cheolsu = result.nodes["cheolsu"]
        self.assertEqual(cheolsu.cls, "Person")
        self.assertEqual(cheolsu.label, "철수")

    def test_schema_only_ttl_reports_error(self):
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".ttl", mode="w", delete=False,
                                          encoding="utf-8") as f:
            f.write(
                "@prefix ex: <http://example.org/onto#> .\n"
                "@prefix owl: <http://www.w3.org/2002/07/owl#> .\n"
                "ex:Person a owl:Class .\n"
            )
            path = Path(f.name)
        try:
            result = ttl_loader.load_ttl_as_parse_result(path)
            self.assertFalse(result.ok)
        finally:
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
