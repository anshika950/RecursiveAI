from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    MODEL_TYPE: str = "ollama"  # ollama or huggingface
    MODEL_NAME: str = "mistral"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    HF_API_TOKEN: str = ""

    DATABASE_URL: str = "sqlite:///./app.db"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False

    # Google OAuth (see .env.example for where to get these). Left blank by
    # default -- the oauth router returns a clear 503 instead of crashing
    # when they're unset.
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/auth/oauth/google/callback"

    # slowapi rate-limit string for /auth/register and /auth/login, e.g.
    # "5/minute". Overridden to something generous in the test environment
    # (see tests/conftest.py) so the suite isn't rate-limited against
    # itself -- it's one shared key_func (client IP) across every request
    # in a run, same as a real client would be.
    AUTH_RATE_LIMIT: str = "5/minute"

    class Config:
        env_file = ".env"


settings = Settings()
