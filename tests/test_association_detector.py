from unittest import TestCase

from specifipy.parsers.association_detector import build_association_connections
from specifipy.parsers.generic_parser import PythonParser
from specifipy.parsers.results import ParsingResult
from specifipy.parsers.structure.code_structure_definitions import (
    ClassStructureDefinition,
    StructureEnum,
    TypeAnnotatedFieldStructureDefinition,
)


def _make_class(name, inherits_from=None, implements=None):
    return ClassStructureDefinition(
        StructureEnum.CLASS, name, 1, 10, inherits_from, implements or []
    )


def _make_typed_field(name, type_annotation, parent_class):
    return TypeAnnotatedFieldStructureDefinition(
        StructureEnum.CLASS_FIELD, name, 1, 1, parent_class, type_annotation
    )


class AssociationDetectorTests(TestCase):
    def test_detects_direct_association(self):
        # @:given Class A has a field of type B, and B is a known class
        class_a = _make_class("A")
        class_b = _make_class("B")
        field = _make_typed_field("b_ref", "B", class_a)
        result = ParsingResult(classes=[class_a, class_b], functions=[], class_fields=[field])
        known = {"A", "B"}

        associations = build_association_connections(result, known)

        self.assertIn(("A", "B"), associations)

    def test_no_association_for_builtin_type(self):
        # @:given Class A has a field of type int
        class_a = _make_class("A")
        field = _make_typed_field("count", "int", class_a)
        result = ParsingResult(classes=[class_a], functions=[], class_fields=[field])
        known = {"A"}

        associations = build_association_connections(result, known)

        self.assertEqual(associations, [])

    def test_strips_list_wrapper(self):
        # @:given Class A has a field typed list[B]
        class_a = _make_class("A")
        class_b = _make_class("B")
        field = _make_typed_field("items", "list[B]", class_a)
        result = ParsingResult(classes=[class_a, class_b], functions=[], class_fields=[field])
        known = {"A", "B"}

        associations = build_association_connections(result, known)

        self.assertIn(("A", "B"), associations)

    def test_no_duplicate_with_inheritance(self):
        # @:given B inherits from A and also has a field typed A
        class_a = _make_class("A")
        class_b = _make_class("B", inherits_from="A")
        field = _make_typed_field("parent", "A", class_b)
        result = ParsingResult(classes=[class_a, class_b], functions=[], class_fields=[field])
        known = {"A", "B"}

        associations = build_association_connections(result, known)

        # Should not add association since B already inherits A
        self.assertNotIn(("B", "A"), associations)

    def test_no_self_association(self):
        # @:given Class A has a field typed A (self-reference)
        class_a = _make_class("A")
        field = _make_typed_field("next", "A", class_a)
        result = ParsingResult(classes=[class_a], functions=[], class_fields=[field])
        known = {"A"}

        associations = build_association_connections(result, known)

        self.assertEqual(associations, [])

    def test_deduplication(self):
        # @:given Class A has two fields of type B
        class_a = _make_class("A")
        class_b = _make_class("B")
        field1 = _make_typed_field("b1", "B", class_a)
        field2 = _make_typed_field("b2", "B", class_a)
        result = ParsingResult(classes=[class_a, class_b], functions=[], class_fields=[field1, field2])
        known = {"A", "B"}

        associations = build_association_connections(result, known)

        self.assertEqual(associations.count(("A", "B")), 1)
