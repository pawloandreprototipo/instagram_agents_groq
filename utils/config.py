from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")

    groq_api_key: str
    instagram_username: str
    instagram_password: str
    output_dir: str = "output"
    log_level: str = "INFO"

    # Provider e modelo por agent — trocar aqui sem alterar código
    media_agent_provider: str = "groq"
    media_agent_model: str = "llama-3.3-70b-versatile"

    def posts_dir(self, username: str) -> Path:
        return Path(self.output_dir) / username / "posts"

    def json_output_path(self, username: str) -> Path:
        return Path(self.output_dir) / username / "profile_data.json"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
