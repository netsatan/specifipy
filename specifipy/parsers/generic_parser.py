import abc
import ast
from enum import Enum

import javalang.parse
from javalang.parser import JavaSyntaxError
from javalang.tree import CompilationUnit, FieldDeclaration, MethodDeclaration

from specifipy.parsers.results import ParsingResult
from specifipy.parsers.structure.code_structure_definitions import (
    ClassStructureDefinition,
    Docstring,
    FunctionStructureDefinition,
    NotTypeAnnotatedFieldStructureDefinition,
    StructureEnum,
    TypeAnnotatedFieldStructureDefinition,
)


class FileType(Enum):
    PYTHON = "python"
    JAVA = "java"
    TYPESCRIPT = "typescript"


class GenericParser(abc.ABC):
    @abc.abstractmethod
    def parse(self, source_code_file_content: str) -> ParsingResult:
        pass


class ParserFactory:
    @staticmethod
    def get_parser(file_type: FileType) -> GenericParser:
        if file_type == FileType.PYTHON:
            return PythonParser()
        if file_type == FileType.JAVA:
            return JavaParser()
        if file_type == FileType.TYPESCRIPT:
            return TypeScriptParser()
        raise NotImplementedError(f"Unsupported file type: {file_type}")


class JavaParser(GenericParser):
    def __generate_method_definition(
            self, method: MethodDeclaration, parent_class: ClassStructureDefinition
    ) -> FunctionStructureDefinition:
        name: str = method.name
        return_type: str = None
        if "private" in method.modifiers:
            name = f"-{name}"

        params: list[str] = []
        if method.parameters:
            for param in method.parameters:
                params.append(
                    f"{param.type.name} {'<' + param.arguments[0].name + '>' if (hasattr(param, 'arguments') and param.arguments) else ''} {param.name}"
                )
        if method.return_type:
            return_type = method.return_type.name
        return FunctionStructureDefinition(
            StructureEnum.FUNCTION,
            name,
            method.position.line,
            method.position.line,
            params,
            parent_class,
            return_type,
        )

    def parse(self, source_code_file_content: str) -> ParsingResult:
        try:
            parsing_result: ParsingResult = ParsingResult([], [], [])
            tree: CompilationUnit = javalang.parse.parse(source_code_file_content)

        except JavaSyntaxError as java_syntax_error:
            print(f"There was a problem with a file: {java_syntax_error.description}")
            return parsing_result

        if (
                tree.types
        ):  # This list represents classes defined in the Java file. Should be 1 per file.
            for declaration in tree.types:
                class_structure = ClassStructureDefinition(
                    StructureEnum.CLASS,
                    declaration.name,
                    declaration.position.line,
                    declaration.position.line,
                    declaration.extends.name if hasattr(declaration, "extends") and declaration.extends and hasattr(
                        declaration.extends, "name") else None,
                    [interface.name for interface in declaration.implements]
                    if hasattr(declaration, "implements") and declaration.implements
                    else None,
                )
                parsing_result.classes.append(class_structure)
                # Extract documentation if present
                if declaration.documentation:
                    docstring = Docstring(declaration.documentation)
                    if parsing_result.docstrings is not None:
                        parsing_result.docstrings.append(docstring)
                    else:
                        parsing_result.docstrings = [docstring]

                # Now methods
                if (
                        declaration.methods
                ):  # might be None if no method is declared (various DTOs etc.)
                    methods: list[FunctionStructureDefinition] = []
                    for method in declaration.methods:
                        methods.append(
                            self.__generate_method_definition(method, class_structure)
                        )
                    parsing_result.functions = methods

                # And fields
                if declaration.fields:
                    field: FieldDeclaration
                    for field in declaration.fields:
                        name: str = (
                            field.declarators[0].name
                            if not "private" in field.modifiers
                            else f"-{field.declarators[0].name}"
                        )
                        field_type: str = field.type.name
                        field_structure = TypeAnnotatedFieldStructureDefinition(
                            StructureEnum.CLASS_FIELD,
                            name,
                            field.position.line,
                            field.position.line,
                            class_structure,
                            field_type,
                        )
                        parsing_result.class_fields.append(field_structure)
        return parsing_result


class PythonParser(GenericParser):
    def __init__(self):
        pass

    def get_return_type_annotation(self, function_node: ast.FunctionDef) -> str | None:
        # Check if the function has a return type annotation directly
        if function_node.returns:
            return ast.unparse(function_node.returns)

        # If not, try to find the return type annotation in the function body
        for node in ast.walk(function_node):
            if isinstance(node, ast.Return):
                if (
                        isinstance(node.value, ast.NameConstant)
                        and node.value.value is None
                ):
                    continue
                if isinstance(node.value, ast.AnnAssign):
                    return ast.unparse(node.value.annotation)
        return None

    def __classify_node(
            self, node: ast.AST, parsing_result: ParsingResult, parent=None
    ) -> None:
        match type(node):
            case ast.ClassDef:
                node: ast.ClassDef
                name: str = node.name
                inherits_from = ""
                if len(node.bases) > 0:
                    if isinstance(node.bases[0], ast.Name):
                        inherits_from = node.bases[0].id
                    if isinstance(node.bases[0], ast.Attribute):
                        inherits_from = f"{node.bases[0].value.id if hasattr(node.bases[0].value, 'id') else node.bases[0].value.value.id}_{node.bases[0].attr}"

                class_definition = ClassStructureDefinition(
                    StructureEnum.CLASS,
                    name,
                    node.lineno,
                    node.end_lineno,
                    inherits_from,
                )

                if class_definition not in parsing_result.classes:
                    parsing_result.classes.append(class_definition)
                sub_node: ast.AST
                for sub_node in node.body:
                    self.__classify_node(
                        sub_node, parsing_result, parent=class_definition
                    )

            case ast.FunctionDef:
                node: ast.FunctionDef
                name: str = node.name
                params: ast.arguments = node.args
                params_string: list[str] = [x.arg for x in params.args]
                function_definition = FunctionStructureDefinition(
                    StructureEnum.FUNCTION,
                    name,
                    node.lineno,
                    node.end_lineno,
                    params_string,
                    (parent if parent else None),
                    str(self.get_return_type_annotation(node)),
                )
                if function_definition not in parsing_result.functions:
                    parsing_result.functions.append(function_definition)

            case ast.AnnAssign:
                if isinstance(parent, ClassStructureDefinition) and parent:
                    node: ast.AnnAssign
                    name: str = node.target.id
                    type_annotation: str = (
                        node.annotation.id
                        if not isinstance(
                            node.annotation,
                            (ast.Attribute, ast.Subscript, ast.BinOp, ast.Call),
                        )
                        else node.annotation.attr
                        if isinstance(node.annotation, ast.Attribute)
                        else ast.unparse(node.annotation.slice)
                        if isinstance(node.annotation, ast.Subscript)
                        else ast.unparse(node.annotation)
                        if isinstance(node.annotation, ast.BinOp)
                        else ast.unparse(node.annotation)
                    )
                    field = TypeAnnotatedFieldStructureDefinition(
                        StructureEnum.CLASS_FIELD,
                        name,
                        node.lineno,
                        node.end_lineno,
                        parent,
                        type_annotation,
                    )
                    parsing_result.class_fields.append(field)

            case ast.Assign:
                if isinstance(parent, ClassStructureDefinition) and parent:
                    node: ast.Assign
                    name: str = (
                        node.targets[0].id
                        if isinstance(node.targets[0], ast.Name)
                        else node.targets[0].attr
                        if isinstance(node.targets[0], ast.Attribute)
                        else str(node.targets[0])
                    )
                    field = NotTypeAnnotatedFieldStructureDefinition(
                        StructureEnum.CLASS_FIELD,
                        name,
                        node.lineno,
                        node.end_lineno,
                        parent,
                    )
                    parsing_result.class_fields.append(field)

    def parse(self, source_code_file_content: str) -> ParsingResult:
        code = ast.parse(source_code_file_content)
        parsing_result: ParsingResult = ParsingResult([], [], [])
        for node in ast.walk(code):
            self.__classify_node(node, parsing_result)
        return parsing_result


class TypeScriptParser(GenericParser):
    """
    Parser for TypeScript (and JavaScript) source files using tree-sitter.
    Extracts classes, methods, and typed properties.
    """

    def __init__(self):
        try:
            import tree_sitter_typescript as _tstypescript
            from tree_sitter import Language, Parser
            self._Language = Language
            self._Parser = Parser
            self._language_typescript = _tstypescript.language_typescript
        except ImportError as e:
            raise ImportError(
                "TypeScript parsing requires 'tree-sitter' and 'tree-sitter-typescript'. "
                "Install them with: pip install tree-sitter tree-sitter-typescript"
            ) from e

    def _make_parser(self):
        lang = self._Language(self._language_typescript())
        parser = self._Parser(lang)
        return parser

    def _node_text(self, node, source_bytes: bytes) -> str:
        return source_bytes[node.start_byte:node.end_byte].decode("utf-8")

    def _parse_type_annotation(self, node, source_bytes: bytes) -> str | None:
        """Extract the text of a type annotation node."""
        if node is None:
            return None
        return self._node_text(node, source_bytes)

    def _find_child_by_type(self, node, *node_types):
        for child in node.children:
            if child.type in node_types:
                return child
        return None

    def _collect_method_params(self, params_node, source_bytes: bytes) -> list[str]:
        params = []
        if params_node is None:
            return params
        for child in params_node.children:
            if child.type in ("required_parameter", "optional_parameter", "rest_parameter"):
                # child: identifier or pattern: type
                name_node = self._find_child_by_type(child, "identifier", "object_pattern", "array_pattern")
                if name_node:
                    name = self._node_text(name_node, source_bytes)
                    type_node = self._find_child_by_type(child, "type_annotation")
                    if type_node:
                        # type_annotation node wraps ': Type'
                        type_text = self._node_text(type_node, source_bytes).lstrip(": ").strip()
                        params.append(f"{name}: {type_text}")
                    else:
                        params.append(name)
        return params

    def _get_return_type(self, method_node, source_bytes: bytes) -> str | None:
        type_node = self._find_child_by_type(method_node, "type_annotation")
        if type_node:
            return self._node_text(type_node, source_bytes).lstrip(": ").strip()
        return None

    def _process_class_body(
        self,
        class_def: ClassStructureDefinition,
        body_node,
        source_bytes: bytes,
        parsing_result: ParsingResult,
    ) -> None:
        for member in body_node.children:
            if member.type == "method_definition":
                name_node = self._find_child_by_type(member, "property_identifier", "private_property_identifier")
                if not name_node:
                    continue
                name = self._node_text(name_node, source_bytes)

                # Check for private modifier (# prefix = private field identifier)
                is_private = name.startswith("#")
                # Also check accessibility_modifier
                acc_node = self._find_child_by_type(member, "accessibility_modifier")
                if acc_node and self._node_text(acc_node, source_bytes) == "private":
                    is_private = True

                if is_private:
                    name = f"-{name.lstrip('#')}"

                params_node = self._find_child_by_type(member, "formal_parameters")
                params = self._collect_method_params(params_node, source_bytes)

                return_type = self._get_return_type(member, source_bytes)

                func_def = FunctionStructureDefinition(
                    StructureEnum.FUNCTION,
                    name,
                    member.start_point[0] + 1,
                    member.end_point[0] + 1,
                    params,
                    class_def,
                    return_type,
                )
                parsing_result.functions.append(func_def)

            elif member.type == "public_field_definition":
                name_node = self._find_child_by_type(
                    member, "property_identifier", "private_property_identifier"
                )
                if not name_node:
                    continue
                name = self._node_text(name_node, source_bytes)

                is_private = name.startswith("#")
                acc_node = self._find_child_by_type(member, "accessibility_modifier")
                if acc_node and self._node_text(acc_node, source_bytes) == "private":
                    is_private = True

                if is_private:
                    name = f"-{name.lstrip('#')}"

                type_node = self._find_child_by_type(member, "type_annotation")
                if type_node:
                    type_text = self._node_text(type_node, source_bytes).lstrip(": ").strip()
                    field = TypeAnnotatedFieldStructureDefinition(
                        StructureEnum.CLASS_FIELD,
                        name,
                        member.start_point[0] + 1,
                        member.end_point[0] + 1,
                        class_def,
                        type_text,
                    )
                else:
                    field = NotTypeAnnotatedFieldStructureDefinition(
                        StructureEnum.CLASS_FIELD,
                        name,
                        member.start_point[0] + 1,
                        member.end_point[0] + 1,
                        class_def,
                    )
                parsing_result.class_fields.append(field)

    def parse(self, source_code_file_content: str) -> ParsingResult:
        parsing_result: ParsingResult = ParsingResult([], [], [])
        parser = self._make_parser()
        source_bytes = source_code_file_content.encode("utf-8")
        tree = parser.parse(source_bytes)

        def walk(node):
            if node.type == "class_declaration":
                name_node = self._find_child_by_type(node, "type_identifier")
                if not name_node:
                    return
                class_name = self._node_text(name_node, source_bytes)

                # Inheritance: class_heritage -> extends_clause
                inherits_from = None
                implements_list = []
                for child in node.children:
                    if child.type == "class_heritage":
                        for heritage_child in child.children:
                            if heritage_child.type == "extends_clause":
                                for hc in heritage_child.children:
                                    if hc.type == "identifier":
                                        inherits_from = self._node_text(hc, source_bytes)
                                        break
                            elif heritage_child.type == "implements_clause":
                                for hc in heritage_child.children:
                                    if hc.type in ("type_identifier", "generic_type"):
                                        implements_list.append(
                                            self._node_text(hc, source_bytes)
                                        )

                class_def = ClassStructureDefinition(
                    StructureEnum.CLASS,
                    class_name,
                    node.start_point[0] + 1,
                    node.end_point[0] + 1,
                    inherits_from,
                    implements_list if implements_list else [],
                )
                parsing_result.classes.append(class_def)

                body_node = self._find_child_by_type(node, "class_body")
                if body_node:
                    self._process_class_body(class_def, body_node, source_bytes, parsing_result)

            for child in node.children:
                walk(child)

        walk(tree.root_node)
        return parsing_result
