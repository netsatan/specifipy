import os
from unittest import TestCase

from specifipy.parsers.diagram_generator_mermaid import MermaidDiagramGenerator


_SOURCE_WITH_INHERITANCE = """
class Animal:
    name: str
    def speak(self) -> str:
        pass

class Dog(Animal):
    breed: str
    def fetch(self) -> None:
        pass
"""

_SOURCE_WITH_ASSOCIATION = """
class Engine:
    horsepower: int

class Car:
    engine: Engine
    model: str
"""


class MermaidDiagramGeneratorTests(TestCase):
    base_path = os.path.dirname(__file__)
    test_results_path = f"{base_path}/results/"

    def tearDown(self) -> None:
        for f in os.listdir(self.test_results_path):
            os.remove(f"{self.test_results_path}{f}")

    def test_generates_classDiagram_header(self):
        generator = MermaidDiagramGenerator()
        result = generator.generate_diagram(
            _SOURCE_WITH_INHERITANCE,
            "test_inheritance.py",
            base_path=self.test_results_path,
        )
        self.assertIsNotNone(result)
        self.assertTrue(result.startswith("classDiagram"))

    def test_generates_class_blocks(self):
        generator = MermaidDiagramGenerator()
        result = generator.generate_diagram(
            _SOURCE_WITH_INHERITANCE,
            "test_inheritance.py",
            base_path=self.test_results_path,
        )
        self.assertIn("class Animal", result)
        self.assertIn("class Dog", result)

    def test_generates_inheritance_arrow(self):
        generator = MermaidDiagramGenerator()
        result = generator.generate_diagram(
            _SOURCE_WITH_INHERITANCE,
            "test_inheritance.py",
            base_path=self.test_results_path,
        )
        self.assertIn("Dog --|> Animal", result)

    def test_generates_association_arrow(self):
        generator = MermaidDiagramGenerator()
        result = generator.generate_diagram(
            _SOURCE_WITH_ASSOCIATION,
            "test_association.py",
            base_path=self.test_results_path,
        )
        self.assertIn("Car --> Engine", result)

    def test_saves_mmd_file(self):
        generator = MermaidDiagramGenerator()
        generator.generate_diagram(
            _SOURCE_WITH_INHERITANCE,
            "test_save.py",
            base_path=self.test_results_path,
        )
        self.assertTrue(os.path.exists(f"{self.test_results_path}test_save.py.mmd"))

    def test_returns_none_for_empty_source(self):
        generator = MermaidDiagramGenerator()
        result = generator.generate_diagram(
            "# no classes here\nx = 1\n",
            "empty.py",
            base_path=self.test_results_path,
            save_file=False,
        )
        self.assertIsNone(result)
