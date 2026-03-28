import re

from specifipy.parsers.results import ParsingResult
from specifipy.parsers.structure.code_structure_definitions import (
    TypeAnnotatedFieldStructureDefinition,
)

_GENERIC_WRAPPER_RE = re.compile(
    r'^(?:list|List|Optional|Set|set|Dict|dict|Sequence|Iterable|Tuple|tuple|FrozenSet|frozenset)\[(.+)\]$'
)


def _unwrap_generic(type_name: str) -> str:
    """Strip one layer of a generic container wrapper, e.g. list[Foo] -> Foo."""
    match = _GENERIC_WRAPPER_RE.match(type_name.strip())
    if match:
        return match.group(1).strip()
    # Handle Optional[X] | X style: take first non-None token
    if "|" in type_name:
        parts = [p.strip() for p in type_name.split("|") if p.strip() != "None"]
        if parts:
            return parts[0]
    return type_name.strip()


def build_association_connections(
    parsing_result: ParsingResult,
    known_class_names: set,
) -> list:
    """
    Return (owner_class_name, target_class_name) tuples where a class field's
    type resolves to a known class in the same parsing result.

    Skips types that are already represented by an inheritance or implementation
    arrow to avoid duplicate connections.
    """
    associations = []
    seen = set()

    for field in parsing_result.class_fields:
        if not isinstance(field, TypeAnnotatedFieldStructureDefinition):
            continue
        if field.parent_class is None:
            continue

        owner = field.parent_class.name
        raw_type = field.type_annotation
        target = _unwrap_generic(raw_type)

        if target not in known_class_names:
            continue
        if target == owner:
            continue

        # Skip if already expressed as inheritance
        parent_class = field.parent_class
        if parent_class.inherits_from and parent_class.inherits_from == target:
            continue
        # Skip if already expressed as interface implementation
        if parent_class.implements and target in parent_class.implements:
            continue

        pair = (owner, target)
        if pair not in seen:
            seen.add(pair)
            associations.append(pair)

    return associations
