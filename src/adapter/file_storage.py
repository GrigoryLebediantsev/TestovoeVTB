from pathlib import Path

import pydantic

from shared.csv_writer import dump_csv
from shared.json_writer import dump_json
from src.usecase import ResultStorage


class FileStorageConfig(pydantic.BaseModel):
    OUTPUT_DIR: str = 'output'


class FileStorage(ResultStorage):
    def __init__(self, config: FileStorageConfig) -> None:
        self.config = config

    async def save_json(self, folder_name: str, file_name: str, content: dict[str, object]) -> str:
        folder = self._prepare_folder(folder_name)
        (folder / file_name).write_text(dump_json(content) + '\n', encoding='utf-8')
        return str(folder)

    async def save_csv(
        self, folder_name: str, file_name: str, columns: list[str], rows: list[dict[str, object]]
    ) -> str:
        folder = self._prepare_folder(folder_name)
        # newline='': переводы строк внутри значений csv обрабатывает сам
        with (folder / file_name).open('w', encoding='utf-8', newline='') as file:
            file.write(dump_csv(columns, rows))
        return str(folder)

    def _prepare_folder(self, folder_name: str) -> Path:
        folder = Path(self.config.OUTPUT_DIR) / folder_name
        folder.mkdir(parents=True, exist_ok=True)
        return folder
