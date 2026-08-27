"""Application settings shared by development, test, and production."""

from typing import Literal

from pydantic import ConfigDict, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Load runtime settings from environment variables and an optional .env file."""

    app_env: Literal["development", "test", "production"] = "development"

    db_host: str = "localhost"
    db_port: int = 3306
    db_name: str = "qqbot"
    db_user: str = "qqbot"
    db_password: str = ""

    napcat_host: str = "localhost"
    napcat_port: int = 3001
    napcat_ws_path: str = "/onebot/v11/ws"

    log_level: str = "INFO"
    log_folder: str = "logs"

    cooldown_duration: int = 1
    image_folder: str = "images"
    bot_qq: str = ""
    group_id: str = ""
    onebot_access_token: str = ""

    observability_queue_capacity: int = 2048
    observability_batch_size: int = 50
    observability_flush_interval_seconds: float = 0.5
    observability_shutdown_timeout_seconds: float = 10.0
    observability_retention_days: int = 30
    observability_retention_interval_hours: int = 24
    observability_system_sample_seconds: float = 5.0

    # MaiBot (麦麦) 桥接
    mai_enabled: bool = False
    # maim_message 0.6.x 客户端按原始 URL 连接，不会自动补路径；服务端路由挂在 /ws
    mai_ws_url: str = "ws://mai:8000/ws"
    mai_platform_name: str = "qqbot"
    mai_auth_token: str = ""
    # 逗号分隔的群号白名单；留空表示允许所有群
    mai_allowed_groups: str = ""
    # 麦麦出站回复之间的最小间隔（秒），防止刷屏
    mai_min_interval_seconds: float = 10.0
    # 单条回复文本长度上限（超出截断），防止长篇大论
    mai_max_reply_length: int = 1500
    # 出站发送队列上限，超过即丢弃最旧回复
    mai_outbound_queue_size: int = 32

    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_production_secrets(self):
        """Fail fast when production is started with missing or sample credentials."""
        if self.app_env != "production":
            return self

        insecure_db_passwords = {
            "",
            "change_me",
            "qqbot123",
            "dev-app-password",
            "test-app-password",
        }
        insecure_tokens = {
            "",
            "change_me",
            "dev-only-onebot-token",
            "test-only-onebot-token",
        }
        errors = []

        if self.db_password.strip().lower() in insecure_db_passwords:
            errors.append("DB_PASSWORD must be set to a production secret")
        if self.onebot_access_token.strip().lower() in insecure_tokens:
            errors.append("ONEBOT_ACCESS_TOKEN must be set to a production secret")
        if self.bot_qq.strip().lower() in {"", "change_me"}:
            errors.append("BOT_QQ must be set in production")

        if errors:
            raise ValueError("; ".join(errors))

        return self

    @model_validator(mode="after")
    def validate_observability_limits(self):
        positive_values = {
            "OBSERVABILITY_QUEUE_CAPACITY": self.observability_queue_capacity,
            "OBSERVABILITY_BATCH_SIZE": self.observability_batch_size,
            "OBSERVABILITY_FLUSH_INTERVAL_SECONDS": self.observability_flush_interval_seconds,
            "OBSERVABILITY_SHUTDOWN_TIMEOUT_SECONDS": self.observability_shutdown_timeout_seconds,
            "OBSERVABILITY_RETENTION_DAYS": self.observability_retention_days,
            "OBSERVABILITY_RETENTION_INTERVAL_HOURS": self.observability_retention_interval_hours,
            "OBSERVABILITY_SYSTEM_SAMPLE_SECONDS": self.observability_system_sample_seconds,
        }
        invalid = [name for name, value in positive_values.items() if value <= 0]
        if invalid:
            raise ValueError(f"must be positive: {', '.join(invalid)}")
        if self.observability_batch_size > self.observability_queue_capacity:
            raise ValueError(
                "OBSERVABILITY_BATCH_SIZE cannot exceed OBSERVABILITY_QUEUE_CAPACITY"
            )
        return self

    @property
    def db_url(self) -> str:
        """Build the SQLAlchemy MySQL connection URL."""
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"
        )

    @property
    def napcat_ws_url(self) -> str:
        """Build the internal NapCat WebSocket URL."""
        return f"ws://{self.napcat_host}:{self.napcat_port}{self.napcat_ws_path}"


settings = Settings()
