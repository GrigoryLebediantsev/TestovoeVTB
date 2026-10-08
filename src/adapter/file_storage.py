from pathlib import Path

import pydantic

from shared.json_writer import dump_json
from src.usecase import ResultStorage


class FileStorageConfig(pydantic.BaseModel):
    OUTPUT_DIR: str = 'output'


class FileStorage(ResultStorage):
    def __init__(self, config: FileStorageConfig) -> None:
        self.config = config

    async def save_json(self, folder_name: str, file_name: str, content: dict[str, object]) -> str:
        folder = Path(self.config.OUTPUT_DIR) / folder_name
        folder.mkdir(parents=True, exist_ok=True)
        (folder / file_name).write_text(dump_json(content) + '\n', encoding='utf-8')
        return str(folder)
