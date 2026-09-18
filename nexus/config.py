"""Workspace + settings model (PRD §6, §28). Secrets NEVER live here — only refs."""
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    workspace: str = Field(default="personal", alias="NEXUS_WORKSPACE")
    data_dir: str = Field(default="./nexus_data", alias="NEXUS_DATA_DIR")
    dry_run: bool = Field(default=False, alias="NEXUS_DRY_RUN")

    class Config:
        env_file = ".env"
        extra = "ignore"


WORKSPACES = {
    "personal": {"type": "personal", "policy_pack": "standard"},
    "business_a": {"type": "business", "policy_pack": "standard"},
    "business_b": {"type": "business", "policy_pack": "standard"},
    "projects": {"type": "project", "policy_pack": "dev_auto_test"},
}

settings = Settings()
