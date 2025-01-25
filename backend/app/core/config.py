from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


# Define the base configuration class
class BaseConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ENV_STATE: str | None = None  # ENV_STATE will be read from the environment


# Define the global configuration settings class
class GlobalConfig(BaseConfig):
    DATABASE_URL: str | None = None
    DB_FORCE_ROLL_BACK: bool = False
    APP_PUBLIC_URL: str | None = None

    # Twilio API Credentials
    TWILIO_ACCOUNT_SID: str | None = None
    TWILIO_AUTH_TOKEN: str | None = None
    TWILIO_PHONE_NUMBER: str | None = None

    # Groq API Credentials
    GROQ_API_KEY: str | None = None

    # Eleven Labs API Credentials
    ELEVENLABS_API_KEY: str | None = None
    VOICE_ID: str | None = None

    AISALESAGENT_NAME: str | None = None
    COMPANY_NAME: str | None = None
    COMPANY_BUSINESS: str | None = None
    CONVERSATION_PURPOSE: str | None = None
    COMPANY_PRODUCTS_SERVICES: str | None = None


# Ensure environment variables are prefixed based on ENV_STATE
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


# Get the ENV_STATE value from the environment (or default to 'dev' if not set)
env_state = BaseConfig().ENV_STATE or "dev"

# Load the appropriate configuration
config = get_config(env_state)
