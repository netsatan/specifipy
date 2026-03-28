import abc


class BaseDiagramGenerator(abc.ABC):
    @abc.abstractmethod
    def generate_diagram(
        self,
        source_file_content: str,
        source_file_name: str,
        base_path: str = None,
        save_file: bool = True,
        file_name_container: bool = False,
    ):
        pass

    @abc.abstractmethod
    def save_diagram_to_file(
        self, base_path: str, diagram, source_file_name: str
    ) -> None:
        pass
