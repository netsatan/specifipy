from unittest import TestCase

from specifipy.parsers.generic_parser import PythonParser
from specifipy.parsers.result_filter import FilterOptions, ParsingResultFilter
from specifipy.parsers.results import ParsingResult
from specifipy.parsers.structure.code_structure_definitions import (
    ClassStructureDefinition,
    FunctionStructureDefinition,
    StructureEnum,
    TypeAnnotatedFieldStructureDefinition,
)


_SOURCE_WITH_PRIVATE = """
class MyClass:
    public_field: int
    _private_field: str

    def public_method(self) -> None:
        pass

    def _private_method(self) -> None:
        pass

    def __init__(self) -> None:
        pass
"""

_SOURCE_TWO_CLASSES = """
class Alpha:
    value: int
    def do_alpha(self) -> None:
        pass

class Beta:
    name: str
    def do_beta(self) -> None:
        pass
"""


class ResultFilterTests(TestCase):
    def test_public_only_removes_private_and_dunder_methods(self):
        parser = PythonParser()
        result = parser.parse(_SOURCE_WITH_PRIVATE)
        filtered = ParsingResultFilter(FilterOptions(public_only=True)).apply(result)

        method_names = [f.name for f in filtered.functions]
        self.assertIn("public_method", method_names)
        self.assertNotIn("_private_method", method_names)
        self.assertNotIn("__init__", method_names)

    def test_public_only_removes_private_fields(self):
        parser = PythonParser()
        result = parser.parse(_SOURCE_WITH_PRIVATE)
        filtered = ParsingResultFilter(FilterOptions(public_only=True)).apply(result)

        field_names = [f.name for f in filtered.class_fields]
        self.assertIn("public_field", field_names)
        self.assertNotIn("_private_field", field_names)

    def test_include_classes_filters_correctly(self):
        parser = PythonParser()
        result = parser.parse(_SOURCE_TWO_CLASSES)
        filtered = ParsingResultFilter(FilterOptions(include_classes=["Alpha"])).apply(result)

        class_names = [c.name for c in filtered.classes]
        self.assertIn("Alpha", class_names)
        self.assertNotIn("Beta", class_names)

        method_names = [f.name for f in filtered.functions]
        self.assertIn("do_alpha", method_names)
        self.assertNotIn("do_beta", method_names)

    def test_filter_noop_with_defaults(self):
        parser = PythonParser()
        result = parser.parse(_SOURCE_TWO_CLASSES)
        filtered = ParsingResultFilter(FilterOptions()).apply(result)

        self.assertEqual(len(filtered.classes), len(result.classes))
        self.assertEqual(len(filtered.functions), len(result.functions))
        self.assertEqual(len(filtered.class_fields), len(result.class_fields))
