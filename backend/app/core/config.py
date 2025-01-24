from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ENV_STATE: str | None = None


# Define the configuration settings class
class GlobalConfig(BaseSettings):
    DATABASE_URL: str | None = None
    DB_FORCE_ROLL_BACK: bool = False

    # Twilio API Credentials
    TWILIO_ACCOUNT_SID: str | None = None
    TWILIO_AUTH_TOKEN: str | None = None
    TWILIO_PHONE_NUMBER: str | None = None

    # OpenAI API Credentials
    OPENAI_API_KEY: str | None = None

    # Eleven Labs API Credentials
    ELEVENLABS_API_KEY: str | None = None
    VOICE_ID: str | None = None


class DevConfig(GlobalConfig):
    model_config = SettingsConfigDict(env_prefix="DEV_", extra="ignore")


class ProdConfig(GlobalConfig):
    model_config = SettingsConfigDict(env_prefix="PROD_", extra="ignore")


class TestConfig(GlobalConfig):
    model_config = SettingsConfigDict(env_prefix="TEST_", extra="ignore")

    DATABASE_URL: str = "sqlite:///./test.db"
    DB_FORCE_ROLL_BACK: bool = True


# Use lru_cache to cache the configuration object
@lru_cache
def get_config(env_state: str):
    configs = {"dev": DevConfig, "prod": ProdConfig, "test": TestConfig}
    return configs[env_state]()


# Accessing the configuration
config = get_config(BaseConfig().ENV_STATE)
