import dataclasses

from specifipy.parsers.results import ParsingResult


@dataclasses.dataclass
class FilterOptions:
    public_only: bool = False
    include_classes: list = dataclasses.field(default_factory=list)


class ParsingResultFilter:
    def __init__(self, options: FilterOptions):
        self.options = options

    def apply(self, result: ParsingResult) -> ParsingResult:
        classes = list(result.classes)
        functions = list(result.functions)
        fields = list(result.class_fields)
        docstrings = list(result.docstrings) if result.docstrings else []

        if self.options.include_classes:
            allowed_names = set(self.options.include_classes)
            classes = [c for c in classes if c.name in allowed_names]
            allowed_ids = {id(c) for c in classes}
            functions = [f for f in functions if id(f.parent_class) in allowed_ids]
            fields = [f for f in fields if id(f.parent_class) in allowed_ids]

        if self.options.public_only:
            # For Python: names starting with _ are private/dunder
            # For Java: the parser prefixes private members with -
            functions = [
                f for f in functions
                if not f.name.startswith("_") and not f.name.startswith("-")
            ]
            fields = [
                f for f in fields
                if not f.name.startswith("_") and not f.name.startswith("-")
            ]

        return ParsingResult(
            classes=classes,
            functions=functions,
            class_fields=fields,
            docstrings=docstrings if docstrings else None,
        )
