from pathlib import Path
import sys

import pytest
from pydantic import ValidationError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from bot.config import Settings


def production_settings(**overrides):
    values = {
        "app_env": "production",
        "db_password": "a-production-db-password",
        "onebot_access_token": "a-production-onebot-token",
        "bot_qq": "123456789",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_production_accepts_explicit_non_placeholder_secrets():
    settings = production_settings()

    assert settings.app_env == "production"


@pytest.mark.parametrize("placeholder", ["", "CHANGE_ME", "qqbot123"])
def test_production_rejects_placeholder_database_password(placeholder):
    with pytest.raises(ValidationError):
        production_settings(db_password=placeholder)


@pytest.mark.parametrize("placeholder", ["", "CHANGE_ME", "test-only-onebot-token"])
def test_production_rejects_placeholder_onebot_token(placeholder):
    with pytest.raises(ValidationError):
        production_settings(onebot_access_token=placeholder)


def test_test_environment_accepts_isolated_test_credentials():
    settings = Settings(
        _env_file=None,
        app_env="test",
        db_name="qqbot_test",
        db_password="test-app-password",
        onebot_access_token="test-only-onebot-token",
    )

    assert settings.app_env == "test"
    assert settings.db_name == "qqbot_test"


def test_local_default_paths_are_not_container_specific(monkeypatch):
    monkeypatch.delenv("IMAGE_FOLDER", raising=False)
    monkeypatch.delenv("LOG_FOLDER", raising=False)
    settings = Settings(_env_file=None)

    assert settings.image_folder == "images"
    assert settings.log_folder == "logs"
