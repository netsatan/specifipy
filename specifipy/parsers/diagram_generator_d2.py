from py_d2 import D2Connection, D2Diagram, D2Shape, Direction
from py_d2.shape import Shape

from specifipy.diagram_engines.hashable_connection import D2HashableConnection
from specifipy.parsers.association_detector import build_association_connections
from specifipy.parsers.base_diagram_generator import BaseDiagramGenerator
from specifipy.parsers.generic_parser import FileType, ParserFactory, PythonParser
from specifipy.parsers.result_filter import FilterOptions, ParsingResultFilter
from specifipy.parsers.results import ParsingResult
from specifipy.parsers.structure.code_structure_definitions import (
    ClassStructureDefinition,
    FieldStructureDefinition,
    FunctionStructureDefinition,
    StructureEnum,
    TypeAnnotatedFieldStructureDefinition,
)


class DiagramGenerator(BaseDiagramGenerator):
    def __init__(
        self,
        file_type: FileType = FileType.PYTHON,
        filter_options: FilterOptions = None,
    ):
        self.parser = ParserFactory.get_parser(file_type)
        self.filter_options = filter_options

    def __generate_class_definition_d2(
        self,
        class_element: ClassStructureDefinition,
        fields: list[D2Shape] = None,
        methods: list[D2Shape] = None,
    ) -> D2Shape:
        fields = [] if fields is None else fields
        methods = [] if methods is None else methods
        result_shape = D2Shape(
            name=class_element.name, shape=Shape.classs, shapes=fields + methods
        )
        return result_shape

    def __generate_field_definition_d2(
        self, class_function_element: FieldStructureDefinition
    ) -> D2Shape:
        if isinstance(class_function_element, TypeAnnotatedFieldStructureDefinition):
            result_shape = D2Shape(
                name=class_function_element.name,
                label=f"'{class_function_element.type_annotation}'"
                if not "'" in class_function_element.type_annotation
                else f'"{class_function_element.type_annotation}"',
            )
        else:
            result_shape = D2Shape(name=class_function_element.name)

        return result_shape

    def __generate_class_function_definition_d2(
        self, method_element: FunctionStructureDefinition
    ) -> D2Shape:
        if method_element.return_type:
            result_shape = D2Shape(
                name=f"{method_element.name}({', '.join([x for x in method_element.params])})",
                label=f"'{method_element.return_type}'"
                if not "'" in method_element.return_type
                else f'"{method_element.return_type}"',
            )
        else:
            result_shape = D2Shape(
                name=f"{method_element.name}({', '.join([x for x in method_element.params])})"
            )
        return result_shape

    def generate_diagram(
        self,
        source_file_content: str,
        source_file_name: str,
        base_path: str = None,
        save_file: bool = True,
        file_name_container=False,
    ) -> D2Diagram | None:
        parsing_result: ParsingResult = self.parser.parse(source_file_content)
        if not (parsing_result.class_fields or parsing_result.classes or parsing_result.functions or parsing_result.docstrings):
            print(f"File {source_file_name} returned empty result as it probably contains syntax errors")

        if self.filter_options:
            parsing_result = ParsingResultFilter(self.filter_options).apply(parsing_result)

        elements_to_generate: list[D2Shape] = []
        link_to_generate: list[D2Connection] = []

        class_element: ClassStructureDefinition

        for class_element in parsing_result.classes:
            class_functions = [
                self.__generate_class_function_definition_d2(x)
                for x in parsing_result.functions
                if x.parent_class == class_element
            ]
            class_fields = [
                self.__generate_field_definition_d2(x)
                for x in parsing_result.class_fields
                if x.parent_class == class_element
            ]
            if file_name_container:
                class_element.name = (
                    f'{source_file_name.replace(".", "-")}.{class_element.name}'
                )
            elements_to_generate.append(
                self.__generate_class_definition_d2(
                    class_element, fields=class_fields, methods=class_functions
                )
            )
            if class_element.inherits_from:
                if file_name_container:
                    class_element.inherits_from = f'{source_file_name.replace(".", "-")}.{class_element.inherits_from}'
                link_to_generate.append(
                    D2Connection(
                        shape_1=class_element.name, shape_2=class_element.inherits_from
                    )
                )
            if class_element.implements:
                for interface in class_element.implements:
                    link_to_generate.append(
                        D2HashableConnection(
                            class_element.name,
                            interface,
                            "{ style: { stroke-dash: 3 } } ",
                        )
                    )

        # Add association arrows for typed fields that reference known classes
        known_class_names = {c.name for c in parsing_result.classes}
        for src, tgt in build_association_connections(parsing_result, known_class_names):
            link_to_generate.append(
                D2HashableConnection(src, tgt, "{ style: { stroke-dash: 1 } }")
            )

        self.add_missing_elements_from_links_as_classes(
            elements_to_generate, link_to_generate
        )
        diagram = D2Diagram(shapes=elements_to_generate, connections=link_to_generate)
        if str(diagram) is not None and str(diagram) != "":
            if save_file:
                self.save_diagram_to_file(base_path, diagram, source_file_name)
            return diagram

    def add_missing_elements_from_links_as_classes(
        self, elements_to_generate, link_to_generate
    ):
        missing_elements = set([link.shape_2 for link in link_to_generate]) - set(
            [element.name for element in elements_to_generate]
        )
        elements_to_generate.extend(
            [
                self.__generate_class_definition_d2(
                    ClassStructureDefinition(
                        StructureEnum.CLASS, missing_element, 0, 0, None
                    )
                )
                for missing_element in missing_elements
            ]
        )

    def save_diagram_to_file(self, base_path, diagram, source_file_name):
        with open(
            f"{base_path if base_path else ''}{source_file_name}.d2",
            "w",
            encoding="utf-8",
        ) as output_file:
            output_file.write("direction: up\n")
            output_file.write(str(diagram))
