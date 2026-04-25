"""
NoneBot 应用配置文件
"""

import os
from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict


class Settings(BaseSettings):
    """应用主配置"""

    # 数据库配置
    db_host: str = Field(default="localhost", env="DB_HOST")
    db_port: int = Field(default=3306, env="DB_PORT")
    db_name: str = Field(default="qqbot", env="DB_NAME")
    db_user: str = Field(default="qqbot", env="DB_USER")
    db_password: str = Field(default="qqbot123", env="DB_PASSWORD")

    # NapCat 配置
    napcat_host: str = Field(default="localhost", env="NAPCAT_HOST")
    napcat_port: int = Field(default=3001, env="NAPCAT_PORT")
    napcat_ws_path: str = Field(default="/onebot/v11/ws", env="NAPCAT_WS_PATH")

    # 日志配置
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    # 应用配置
    cooldown_duration: int = Field(default=1, env="COOLDOWN_DURATION")
    image_folder: str = Field(default="/app/images", env="IMAGE_FOLDER")
    bot_qq: str = Field(default="", env="BOT_QQ")
    group_id: str = Field(default="", env="GROUP_ID")

    # OneBot v11 Token 配置（反向 WebSocket 连接需要）
    onebot_access_token: str = Field(
        default="s~N9cCeg-SDmpwWM", env="ONEBOT_ACCESS_TOKEN"
    )

    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",  # 忽略 .env 中未定义的字段
    )

    @property
    def db_url(self) -> str:
        """生成数据库连接字符串"""
        return f"mysql+pymysql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"

    @property
    def napcat_ws_url(self) -> str:
        """生成 NapCat WebSocket 连接地址"""
        return f"ws://{self.napcat_host}:{self.napcat_port}{self.napcat_ws_path}"


# 全局配置实例
settings = Settings()
