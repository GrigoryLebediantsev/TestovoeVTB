import datetime
import enum

import pydantic
from pydantic_settings import BaseSettings, SettingsConfigDict

from shared.config_helper import load_settings
from shared.logger import LoggerConfig
from src.adapter.browser_window import BrowserWindowConfig
from src.adapter.demo_bank.config import DemoBankConfig
from src.adapter.file_storage import FileStorageConfig


class BankName(enum.StrEnum):
    DEMO_BANK = 'demo_bank'


class ExtractionConfig(pydantic.BaseModel):
    BANK: BankName
    PERIOD_FROM: datetime.date
    PERIOD_TO: datetime.date


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', case_sensitive=False, env_nested_delimiter='__')

    extraction: ExtractionConfig  # EXTRACTION__BANK
    demo_bank: DemoBankConfig  # DEMO_BANK__BASE_URL
    browser: BrowserWindowConfig = BrowserWindowConfig()  # BROWSER__MODE
    storage: FileStorageConfig = FileStorageConfig()  # STORAGE__OUTPUT_DIR
    logger: LoggerConfig = LoggerConfig()  # LOGGER__LEVEL


settings: Settings = load_settings(Settings)
