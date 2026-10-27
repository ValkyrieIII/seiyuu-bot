"""官方 QQ 身份的持久映射；旧 QQ 数字身份保持原样。"""

from functools import lru_cache
from hashlib import sha256
import json
from typing import Optional

from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, inspect, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from bot.config import settings


_MAX_INTERNAL_ID = 2_147_483_647
_metadata = MetaData()
qq_identities = Table(
    "qq_official_identities",
    _metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("identity_key", String(64), nullable=False, unique=True),
    Column("app_id", String(128), nullable=False),
    Column("kind", String(16), nullable=False),
    Column("group_openid", String(512), nullable=False),
    Column("openid", String(512), nullable=False),
)


@lru_cache(maxsize=1)
def _engine() -> Engine:
    return create_engine(settings.db_url, pool_pre_ping=True)


def _validate_inputs(app_id: str, kind: str, openid: str, group_openid: Optional[str]) -> str:
    if not isinstance(app_id, str) or not app_id or len(app_id) > 128:
        raise ValueError("app_id must be a non-empty string of at most 128 characters")
    if kind not in {"group", "member", "user"}:
        raise ValueError("kind must be group, member or user")
    if not isinstance(openid, str) or not openid or len(openid) > 512:
        raise ValueError("openid must be a non-empty string of at most 512 characters")
    if kind == "member":
        if not isinstance(group_openid, str) or not group_openid or len(group_openid) > 512:
            raise ValueError("group_openid is required for a group member")
        return group_openid
    if group_openid is not None:
        raise ValueError("group_openid is only valid for a group member")
    return ""


def check_qq_identity_storage(engine: Optional[Engine] = None) -> None:
    """检查映射表和负数 ID 保留区；启动时只读，不修改数据库。"""
    target = engine or _engine()
    inspector = inspect(target)
    tables = set(inspector.get_table_names())
    if qq_identities.name not in tables:
        raise RuntimeError("官方 QQ 身份表不存在，请备份后执行 migrate-qq-identities")
    expected = {column.name for column in qq_identities.columns}
    actual = {column["name"] for column in inspector.get_columns(qq_identities.name)}
    if not expected.issubset(actual):
        raise RuntimeError("官方 QQ 身份表结构不完整，请检查数据库迁移")

    # 已有负值若没有合法映射，无法安全划分旧 QQ 号和官方身份。
    for table, column, kinds in (
        ("aliases", "user_id", ("member", "user")),
        ("user_cooldowns", "user_id", ("member", "user")),
        ("check_ins", "user_id", ("member", "user")),
        ("check_ins", "group_id", ("group",)),
        ("request_logs", "user_id", ("member", "user")),
        ("request_logs", "group_id", ("group",)),
    ):
        if table not in tables:
            continue
        columns = {item["name"]: item for item in inspector.get_columns(table)}
        if column not in columns:
            continue
        if getattr(columns[column]["type"], "unsigned", False):
            raise RuntimeError(f"{table}.{column} 为无符号类型，无法保存官方身份")
        kind_filter = ", ".join(f"'{kind}'" for kind in kinds)
        query = text(
            f"SELECT 1 FROM {table} AS legacy WHERE legacy.{column} < 0 "
            f"AND NOT EXISTS (SELECT 1 FROM qq_official_identities AS ident "
            f"WHERE ident.id = -legacy.{column} AND ident.kind IN ({kind_filter})) LIMIT 1"
        )
        with target.connect() as connection:
            if connection.execute(query).first() is not None:
                raise RuntimeError(f"{table}.{column} 存在未映射的负数身份，无法安全启用官方 QQ")


def migrate_qq_identities(engine: Optional[Engine] = None) -> list[str]:
    """显式创建映射表；不会改写现有业务记录。"""
    target = engine or _engine()
    if inspect(target).has_table(qq_identities.name):
        check_qq_identity_storage(target)
        return []

    # 创建表前拒绝已有负值，避免与保留区冲突。
    inspector = inspect(target)
    tables = set(inspector.get_table_names())
    for table, column in (
        ("aliases", "user_id"), ("user_cooldowns", "user_id"),
        ("check_ins", "user_id"), ("check_ins", "group_id"),
        ("request_logs", "user_id"), ("request_logs", "group_id"),
    ):
        if table not in tables or column not in {item["name"] for item in inspector.get_columns(table)}:
            continue
        with target.connect() as connection:
            if connection.execute(text(f"SELECT 1 FROM {table} WHERE {column} < 0 LIMIT 1")).first():
                raise RuntimeError(f"{table}.{column} 已有负数，不能创建官方身份保留区")
    qq_identities.create(target, checkfirst=True)
    return ["qq_official_identities created"]


def resolve_qq_identity(
    app_id: str,
    kind: str,
    openid: str,
    *,
    group_openid: Optional[str] = None,
    engine: Optional[Engine] = None,
) -> int:
    """官方身份映射为负整数；成员身份按群隔离，绝不自动关联旧 QQ。"""
    scope = _validate_inputs(app_id, kind, openid, group_openid)
    parts = (app_id, kind, scope, openid)
    key = sha256(json.dumps(parts, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()
    target = engine or _engine()
    statement = select(qq_identities).where(qq_identities.c.identity_key == key)

    def existing() -> Optional[int]:
        with target.connect() as connection:
            row = connection.execute(statement).mappings().first()
        if row is None:
            return None
        if (row["app_id"], row["kind"], row["group_openid"], row["openid"]) != parts:
            raise RuntimeError("官方 QQ 身份摘要冲突")
        internal_id = row["id"]
        if internal_id <= 0 or internal_id > _MAX_INTERNAL_ID:
            raise RuntimeError("官方 QQ 内部身份 ID 超出可用范围")
        return -internal_id

    identity = existing()
    if identity is not None:
        return identity
    try:
        with target.begin() as connection:
            result = connection.execute(qq_identities.insert().values(
                identity_key=key, app_id=app_id, kind=kind,
                group_openid=scope, openid=openid,
            ))
            internal_id = result.inserted_primary_key[0]
            if internal_id <= 0 or internal_id > _MAX_INTERNAL_ID:
                raise RuntimeError("官方 QQ 内部身份 ID 已耗尽")
            return -internal_id
    except IntegrityError:
        # 并发请求同一身份时，使用另一事务已提交的结果。
        identity = existing()
        if identity is None:
            raise
        return identity
