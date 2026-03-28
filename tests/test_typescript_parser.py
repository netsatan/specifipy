import os
from unittest import TestCase


_SIMPLE_TS = """
class Polygon {
    name: string;
    color: string;

    draw(): void {
        console.log("drawing");
    }

    getColor(): string {
        return this.color;
    }
}

class Circle extends Polygon {
    radius: number;
    private center: string;

    area(): number {
        return 3.14 * this.radius * this.radius;
    }
}
"""

_TS_WITH_IMPLEMENTS = """
interface Drawable {
    draw(): void;
}

class Rectangle implements Drawable {
    width: number;
    height: number;

    draw(): void {
        console.log("rect");
    }
}
"""


class TypeScriptParserTests(TestCase):
    def _get_parser(self):
        try:
            from specifipy.parsers.generic_parser import TypeScriptParser
            return TypeScriptParser()
        except ImportError:
            self.skipTest("tree-sitter or tree-sitter-typescript not installed")

    def test_extracts_classes(self):
        parser = self._get_parser()
        result = parser.parse(_SIMPLE_TS)
        class_names = [c.name for c in result.classes]
        self.assertIn("Polygon", class_names)
        self.assertIn("Circle", class_names)

    def test_extracts_methods(self):
        parser = self._get_parser()
        result = parser.parse(_SIMPLE_TS)
        method_names = [f.name for f in result.functions]
        self.assertIn("draw", method_names)
        self.assertIn("getColor", method_names)
        self.assertIn("area", method_names)

    def test_extracts_public_fields(self):
        parser = self._get_parser()
        result = parser.parse(_SIMPLE_TS)
        field_names = [f.name for f in result.class_fields]
        self.assertIn("name", field_names)
        self.assertIn("radius", field_names)

    def test_marks_private_fields(self):
        parser = self._get_parser()
        result = parser.parse(_SIMPLE_TS)
        field_names = [f.name for f in result.class_fields]
        self.assertIn("-center", field_names)

    def test_extracts_inheritance(self):
        parser = self._get_parser()
        result = parser.parse(_SIMPLE_TS)
        circle_class = next(c for c in result.classes if c.name == "Circle")
        self.assertEqual(circle_class.inherits_from, "Polygon")

    def test_extracts_field_types(self):
        parser = self._get_parser()
        result = parser.parse(_SIMPLE_TS)
        from specifipy.parsers.structure.code_structure_definitions import TypeAnnotatedFieldStructureDefinition
        radius_field = next(
            f for f in result.class_fields
            if f.name == "radius" and isinstance(f, TypeAnnotatedFieldStructureDefinition)
        )
        self.assertEqual(radius_field.type_annotation, "number")

    def test_extracts_return_types(self):
        parser = self._get_parser()
        result = parser.parse(_SIMPLE_TS)
        area_method = next(f for f in result.functions if f.name == "area")
        self.assertEqual(area_method.return_type, "number")
