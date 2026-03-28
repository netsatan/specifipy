from enum import Enum

from specifipy.parsers.base_diagram_generator import BaseDiagramGenerator
from specifipy.parsers.generic_parser import FileType
from specifipy.parsers.result_filter import FilterOptions


class DiagramFormat(Enum):
    D2 = "d2"
    MERMAID = "mermaid"


class DiagramGeneratorFactory:
    @staticmethod
    def get_generator(
        diagram_format: DiagramFormat = DiagramFormat.D2,
        file_type: FileType = FileType.PYTHON,
        filter_options: FilterOptions = None,
    ) -> BaseDiagramGenerator:
        if diagram_format == DiagramFormat.D2:
            from specifipy.parsers.diagram_generator_d2 import DiagramGenerator
            return DiagramGenerator(file_type=file_type, filter_options=filter_options)
        if diagram_format == DiagramFormat.MERMAID:
            from specifipy.parsers.diagram_generator_mermaid import MermaidDiagramGenerator
            return MermaidDiagramGenerator(file_type=file_type, filter_options=filter_options)
        raise NotImplementedError(f"Unsupported diagram format: {diagram_format}")
