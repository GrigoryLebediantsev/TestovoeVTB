import pydantic


class DemoBankConfig(pydantic.BaseModel):
    BASE_URL: str
    LOGIN_TIMEOUT_SECONDS: float = 300
    ACTION_TIMEOUT_SECONDS: float = 15
