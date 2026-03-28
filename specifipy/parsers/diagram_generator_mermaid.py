from specifipy.parsers.association_detector import build_association_connections
from specifipy.parsers.base_diagram_generator import BaseDiagramGenerator
from specifipy.parsers.generic_parser import FileType, ParserFactory
from specifipy.parsers.result_filter import FilterOptions, ParsingResultFilter
from specifipy.parsers.results import ParsingResult
from specifipy.parsers.structure.code_structure_definitions import (
    ClassStructureDefinition,
    FieldStructureDefinition,
    FunctionStructureDefinition,
    TypeAnnotatedFieldStructureDefinition,
)


class MermaidDiagramGenerator(BaseDiagramGenerator):
    def __init__(
        self,
        file_type: FileType = FileType.PYTHON,
        filter_options: FilterOptions = None,
    ):
        self.parser = ParserFactory.get_parser(file_type)
        self.filter_options = filter_options

    def __render_visibility(self, name: str) -> str:
        if name.startswith("-"):
            return "-"
        return "+"

    def __render_field(self, field: FieldStructureDefinition) -> str:
        vis = self.__render_visibility(field.name)
        display_name = field.name.lstrip("-")
        if isinstance(field, TypeAnnotatedFieldStructureDefinition):
            return f"        {vis}{field.type_annotation} {display_name}"
        return f"        {vis}{display_name}"

    def __render_method(self, method: FunctionStructureDefinition) -> str:
        vis = self.__render_visibility(method.name)
        display_name = method.name.lstrip("-")
        params = ", ".join(method.params)
        if method.return_type and method.return_type != "None":
            return f"        {vis}{display_name}({params}) {method.return_type}"
        return f"        {vis}{display_name}({params})"

    def __render_class(
        self,
        class_def: ClassStructureDefinition,
        fields: list[FieldStructureDefinition],
        methods: list[FunctionStructureDefinition],
    ) -> str:
        lines = [f"    class {class_def.name} {{"]
        for field in fields:
            lines.append(self.__render_field(field))
        for method in methods:
            lines.append(self.__render_method(method))
        lines.append("    }")
        return "\n".join(lines)

    def generate_diagram(
        self,
        source_file_content: str,
        source_file_name: str,
        base_path: str = None,
        save_file: bool = True,
        file_name_container: bool = False,
    ) -> str | None:
        parsing_result: ParsingResult = self.parser.parse(source_file_content)

        if self.filter_options:
            parsing_result = ParsingResultFilter(self.filter_options).apply(parsing_result)

        if not parsing_result.classes:
            return None

        lines = ["classDiagram"]

        for class_def in parsing_result.classes:
            if file_name_container:
                class_def.name = f'{source_file_name.replace(".", "-")}_{class_def.name}'

            class_fields = [
                f for f in parsing_result.class_fields if f.parent_class == class_def
            ]
            class_methods = [
                f for f in parsing_result.functions if f.parent_class == class_def
            ]
            lines.append(self.__render_class(class_def, class_fields, class_methods))

        # Inheritance arrows
        for class_def in parsing_result.classes:
            if class_def.inherits_from:
                lines.append(f"    {class_def.name} --|> {class_def.inherits_from}")
            if class_def.implements:
                for interface in class_def.implements:
                    lines.append(f"    {class_def.name} ..|> {interface}")

        # Association arrows
        known_class_names = {c.name for c in parsing_result.classes}
        for src, tgt in build_association_connections(parsing_result, known_class_names):
            lines.append(f"    {src} --> {tgt}")

        diagram = "\n".join(lines) + "\n"

        if save_file:
            self.save_diagram_to_file(base_path, diagram, source_file_name)
        return diagram

    def save_diagram_to_file(
        self, base_path: str, diagram: str, source_file_name: str
    ) -> None:
        with open(
            f"{base_path if base_path else ''}{source_file_name}.mmd",
            "w",
            encoding="utf-8",
        ) as output_file:
            output_file.write(diagram)
