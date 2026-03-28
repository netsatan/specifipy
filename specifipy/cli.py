import argparse
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="specifipy",
        description="Generate class diagrams from source code",
    )
    parser.add_argument("path", help="Path to directory to scan")
    parser.add_argument(
        "--format",
        dest="diagram_format",
        choices=["d2", "mermaid"],
        default="d2",
        help="Output diagram format (default: d2)",
    )
    parser.add_argument(
        "--output",
        dest="output_dir",
        default=None,
        help="Directory to write diagram files into",
    )
    parser.add_argument(
        "--file-type",
        dest="file_type",
        choices=["python", "java", "typescript"],
        default="python",
        help="Source language (default: python)",
    )
    parser.add_argument(
        "--public-only",
        action="store_true",
        default=False,
        help="Exclude private/dunder methods and fields",
    )
    parser.add_argument(
        "--exclude-pattern",
        dest="exclude_pattern",
        default=None,
        help="Glob pattern for file names to skip (e.g. 'test_*.py')",
    )
    parser.add_argument(
        "--include-classes",
        dest="include_classes",
        nargs="*",
        default=None,
        metavar="CLASS",
        help="Only include these class names in output",
    )
    collect_group = parser.add_mutually_exclusive_group()
    collect_group.add_argument(
        "--collect",
        dest="collect",
        action="store_true",
        default=True,
        help="Merge all diagrams into one file (default)",
    )
    collect_group.add_argument(
        "--no-collect",
        dest="collect",
        action="store_false",
        help="Write one diagram file per source file",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    from specifipy.parsers.diagram_generator_factory import (
        DiagramFormat,
        DiagramGeneratorFactory,
    )
    from specifipy.parsers.generic_parser import FileType
    from specifipy.parsers.result_filter import FilterOptions
    from specifipy.file_scanners.directory_scanner import DirectoryScanner

    file_type_map = {
        "python": FileType.PYTHON,
        "java": FileType.JAVA,
        "typescript": FileType.TYPESCRIPT,
    }
    file_type = file_type_map[args.file_type]

    diagram_format = (
        DiagramFormat.D2 if args.diagram_format == "d2" else DiagramFormat.MERMAID
    )

    filter_options = FilterOptions(
        public_only=args.public_only,
        include_classes=args.include_classes or [],
    )

    generator = DiagramGeneratorFactory.get_generator(
        diagram_format=diagram_format,
        file_type=file_type,
        filter_options=filter_options,
    )

    scanner = DirectoryScanner(
        base_path=args.path,
        file_type=file_type,
        exclude_pattern=args.exclude_pattern,
    )

    scanner.make_diagrams(
        collect_files=args.collect,
        base_path=args.output_dir,
        generator=generator,
    )


if __name__ == "__main__":
    main()
