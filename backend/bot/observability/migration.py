"""Explicit and idempotent production migration for observability storage."""

from typing import Any, Dict, List, Optional

from sqlalchemy import BigInteger, create_engine, inspect
from sqlalchemy.engine import Engine

from bot.config import settings


def _is_bigint(column: Dict[str, Any]) -> bool:
    return isinstance(column["type"], BigInteger)


def request_log_migration_plan(columns, indexes):
    """Return required DDL; an empty second run demonstrates idempotency."""
    statements = []
    if not _is_bigint(columns["user_id"]):
        statements.append((
            "ALTER TABLE request_logs MODIFY COLUMN user_id BIGINT NOT NULL",
            "request_logs.user_id -> BIGINT",
        ))
    if not _is_bigint(columns["group_id"]):
        statements.append((
            "ALTER TABLE request_logs MODIFY COLUMN group_id BIGINT NULL",
            "request_logs.group_id -> BIGINT",
        ))
    if "error_code" not in columns:
        statements.append((
            "ALTER TABLE request_logs ADD COLUMN error_code VARCHAR(64) NULL AFTER error_message",
            "request_logs.error_code added",
        ))

    indexed_columns = {tuple(index.get("column_names") or []) for index in indexes}
    index_names = {index["name"] for index in indexes}
    for name, column_tuple, ddl_columns in (
        ("idx_request_logs_created_status", ("created_at", "status"), "created_at, status"),
        ("idx_request_logs_created_command", ("created_at", "command"), "created_at, command"),
    ):
        if name not in index_names and column_tuple not in indexed_columns:
            statements.append((
                f"CREATE INDEX {name} ON request_logs ({ddl_columns})",
                f"index {name} added",
            ))
    return statements


def migrate_observability(engine: Optional[Engine] = None) -> List[str]:
    """Apply required MySQL DDL and return the actions that were performed."""
    owned_engine = engine is None
    target = engine or create_engine(settings.db_url, pool_pre_ping=True)
    if target.dialect.name != "mysql":
        if owned_engine:
            target.dispose()
        raise RuntimeError("migrate-observability only supports MySQL")

    actions: List[str] = []
    try:
        with target.begin() as connection:
            inspector = inspect(connection)
            tables = set(inspector.get_table_names())
            if "request_logs" not in tables:
                raise RuntimeError(
                    "request_logs does not exist; initialize a fresh database with database/init.sql"
                )

            columns = {
                column["name"]: column
                for column in inspector.get_columns("request_logs")
            }
            indexes = inspector.get_indexes("request_logs")
            for ddl, action in request_log_migration_plan(columns, indexes):
                connection.exec_driver_sql(ddl)
                actions.append(action)

            # The old check-in initializer altered these columns at startup. Keep
            # compatibility, but move that DDL behind this explicit command.
            if "check_ins" in tables:
                check_in_columns = {
                    column["name"]
                    for column in inspect(connection).get_columns("check_ins")
                }
                for name in ("lucky_actor_id", "lucky_image_id"):
                    if name not in check_in_columns:
                        connection.exec_driver_sql(
                            f"ALTER TABLE check_ins ADD COLUMN {name} INT NULL"
                        )
                        actions.append(f"check_ins.{name} added")
    finally:
        if owned_engine:
            target.dispose()
    return actions
