import pydantic


class DemoBankConfig(pydantic.BaseModel):
    BASE_URL: str
    LOGIN_TIMEOUT_SECONDS: float = 300
    ACTION_TIMEOUT_SECONDS: float = 15
    # Сколько раз повторить чтение после технического сбоя (таймаут, ошибка сервера)
    RETRY_COUNT: int = pydantic.Field(default=2, ge=0)
