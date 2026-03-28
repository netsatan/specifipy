import fnmatch
import os

from py_d2 import D2Diagram

from specifipy.diagram_engines.hashable_connection import D2HashableConnection
from specifipy.parsers.base_diagram_generator import BaseDiagramGenerator
from specifipy.parsers.generic_parser import FileType


class DirectoryScanner:
    scan_path: str = None
    full_dir_paths: list[str] = []
    full_file_paths: list[str] = []
    file_type: FileType = FileType.PYTHON

    file_extension_mapping: dict[str, str] = {
        "python": "py",
        "java": "java",
        "typescript": "ts",
    }

    def __matches_file_classification(self, full_file_path) -> bool:
        file_name = full_file_path.split("/")[-1]
        expected_file_type_expression_length = (
            len(self.file_extension_mapping[self.file_type.value]) + 1
        )
        if self.exclude_pattern and fnmatch.fnmatch(file_name, self.exclude_pattern):
            return False
        return (
            os.path.isfile(full_file_path)
            and file_name[0] != "."
            and file_name[-expected_file_type_expression_length:]
            == f".{self.file_extension_mapping[self.file_type.value]}"
        )

    def __matches_directory_classification(self, full_dir_path) -> bool:
        dir_name: str = full_dir_path.split("/")[-1]
        return (
            os.path.isdir(full_dir_path)
            and dir_name[0] != "."
            and not "venv" in dir_name
            and not "virtualenv" in dir_name
        )

    def __init__(
        self,
        base_path: str,
        file_type: FileType = FileType.PYTHON,
        exclude_pattern: str = None,
    ):
        self.file_type = file_type
        self.exclude_pattern = exclude_pattern
        self.scan_path = os.path.abspath(base_path)
        for obj in os.listdir(self.scan_path):
            os.path.join(self.scan_path, obj)
        file_system_element: str

        # Perform initial directories scanning
        self.full_dir_paths = [
            os.path.join(self.scan_path, file_system_element)
            for file_system_element in os.listdir(self.scan_path)
            if self.__matches_directory_classification(
                os.path.join(self.scan_path, file_system_element)
            )
        ]

        # Perform initial files scanning
        self.full_file_paths = [
            os.path.join(self.scan_path, file_system_element)
            for file_system_element in os.listdir(self.scan_path)
            if self.__matches_file_classification(
                os.path.join(self.scan_path, file_system_element)
            )
        ]

        self.do_recursive_directory_scanning()

    def make_diagrams(
        self,
        collect_files=True,
        file_name_containers: bool = False,
        base_path: str | None = None,
        generator: BaseDiagramGenerator = None,
    ):
        if generator is None:
            from specifipy.parsers.diagram_generator_d2 import DiagramGenerator
            generator = DiagramGenerator(self.file_type)

        is_mermaid = _is_mermaid_generator(generator)

        if is_mermaid:
            self._make_diagrams_mermaid(
                generator, collect_files, file_name_containers, base_path
            )
        else:
            self._make_diagrams_d2(
                generator, collect_files, file_name_containers, base_path
            )

    def _make_diagrams_d2(self, generator, collect_files, file_name_containers, base_path):
        diagrams: list[D2Diagram] = []
        for f in self.full_file_paths:
            name = f.split("/")[-1]
            with open(f) as code_file:
                diagram = generator.generate_diagram(
                    code_file.read(),
                    name,
                    base_path=base_path,
                    save_file=not collect_files,
                    file_name_container=file_name_containers,
                )
                if collect_files and diagram:
                    diagrams.append(diagram)
        if diagrams:
            classes = sum([diagram.shapes for diagram in diagrams], [])
            connections = [
                D2HashableConnection(x.shape_1, x.shape_2, x.label, x.direction)
                for x in sum([diagram.connections for diagram in diagrams], [])
            ]
            generator.save_diagram_to_file(
                base_path if base_path else "./",
                D2Diagram(classes, list(set(connections))),
                "code_diagrams",
            )

    def _make_diagrams_mermaid(self, generator, collect_files, file_name_containers, base_path):
        collected_lines = ["classDiagram"]
        seen_relationships = set()
        any_content = False

        for f in self.full_file_paths:
            name = f.split("/")[-1]
            with open(f) as code_file:
                diagram = generator.generate_diagram(
                    code_file.read(),
                    name,
                    base_path=base_path,
                    save_file=not collect_files,
                    file_name_container=file_name_containers,
                )
                if collect_files and diagram:
                    for line in diagram.splitlines():
                        if line.strip() == "classDiagram":
                            continue
                        # Deduplicate only relationship arrows, never structural lines
                        is_relationship = any(
                            token in line for token in ("--|>", "..|>", "-->")
                        )
                        if is_relationship:
                            if line in seen_relationships:
                                continue
                            seen_relationships.add(line)
                        collected_lines.append(line)
                        any_content = True

        if collect_files and any_content:
            combined = "\n".join(collected_lines) + "\n"
            generator.save_diagram_to_file(
                base_path if base_path else "./",
                combined,
                "code_diagrams",
            )

    def do_recursive_directory_scanning(self):
        new_found_directory_paths: list[str] = []
        if self.full_dir_paths:
            directory_path: str
            for directory_path in self.full_dir_paths:
                for file_system_element in os.listdir(directory_path):
                    full_file_path = os.path.join(directory_path, file_system_element)
                    if os.path.isdir(full_file_path):
                        new_found_directory_paths.append(
                            os.path.join(directory_path, file_system_element)
                        )
                    if os.path.isfile(
                        full_file_path
                    ) and self.__matches_file_classification(full_file_path):
                        self.full_file_paths.append(
                            os.path.join(directory_path, file_system_element)
                        )
            self.full_dir_paths = new_found_directory_paths
            self.do_recursive_directory_scanning()


def _is_mermaid_generator(generator: BaseDiagramGenerator) -> bool:
    from specifipy.parsers.diagram_generator_mermaid import MermaidDiagramGenerator
    return isinstance(generator, MermaidDiagramGenerator)
