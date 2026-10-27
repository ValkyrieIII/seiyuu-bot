from pathlib import Path
import sys
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import create_engine, inspect, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from bot.identity import check_qq_identity_storage, migrate_qq_identities, resolve_qq_identity
from bot.observability.events import ObservabilityEvent


def test_identity_is_stable_and_scoped_to_app_group_and_scene():
    engine = create_engine("sqlite://")
    assert migrate_qq_identities(engine) == ["qq_official_identities created"]
    assert migrate_qq_identities(engine) == []
    member = resolve_qq_identity("app1", "member", "UserA", group_openid="G1", engine=engine)
    assert member < 0
    assert resolve_qq_identity("app1", "member", "UserA", group_openid="G1", engine=engine) == member
    others = {
        resolve_qq_identity("app2", "member", "UserA", group_openid="G1", engine=engine),
        resolve_qq_identity("app1", "member", "UserA", group_openid="G2", engine=engine),
        resolve_qq_identity("app1", "member", "usera", group_openid="G1", engine=engine),
        resolve_qq_identity("app1", "user", "UserA", engine=engine),
        resolve_qq_identity("app1", "group", "UserA", engine=engine),
    }
    assert len(others) == 5
    assert member not in others
    check_qq_identity_storage(engine)


def test_identity_requires_valid_scene_and_preserves_case():
    engine = create_engine("sqlite://")
    migrate_qq_identities(engine)
    for args in [
        ("app", "member", "member", None),
        ("", "user", "member", None),
        ("app", "group", "", None),
        ("app", "unknown", "openid", None),
        ("app", "user", "openid", "group"),
    ]:
        app, kind, openid, group = args
        with pytest.raises(ValueError):
            resolve_qq_identity(app, kind, openid, group_openid=group, engine=engine)


def test_simultaneous_first_events_share_one_identity(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'identities.db'}")
    migrate_qq_identities(engine)
    def resolve(_):
        return resolve_qq_identity("app", "member", "user", group_openid="group", engine=engine)
    with ThreadPoolExecutor(max_workers=8) as pool:
        values = list(pool.map(resolve, range(20)))
    assert len(set(values)) == 1
    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM qq_official_identities")).scalar_one() == 1


def test_migration_rejects_existing_unmapped_negative_ids():
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE check_ins (user_id INTEGER, group_id INTEGER)"))
        conn.execute(text("INSERT INTO check_ins VALUES (-3, 10)"))
    with pytest.raises(RuntimeError, match="已有负数"):
        migrate_qq_identities(engine)
    assert not inspect(engine).has_table("qq_official_identities")


def test_startup_check_detects_unmapped_negative_but_allows_mapped_id():
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE check_ins (user_id INTEGER, group_id INTEGER)"))
    migrate_qq_identities(engine)
    user = resolve_qq_identity("app", "member", "u", group_openid="g", engine=engine)
    group = resolve_qq_identity("app", "group", "g", engine=engine)
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO check_ins VALUES (:user, :group)"), {"user": user, "group": group})
    check_qq_identity_storage(engine)
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO check_ins VALUES (-2000, 1)"))
    with pytest.raises(RuntimeError, match="未映射的负数身份"):
        check_qq_identity_storage(engine)


def test_startup_never_creates_missing_table():
    engine = create_engine("sqlite://")
    with pytest.raises(RuntimeError, match="migrate-qq-identities"):
        check_qq_identity_storage(engine)
    assert not inspect(engine).has_table("qq_official_identities")


def test_observability_accepts_official_ids_but_other_ids_stay_positive():
    event = ObservabilityEvent(command="check_in", status="success", user_id=-1, group_id=-2)
    assert event.to_record()["user_id"] == -1
    with pytest.raises(ValueError):
        ObservabilityEvent(command="check_in", status="success", user_id=0)
    with pytest.raises(ValueError):
        ObservabilityEvent(command="check_in", status="success", user_id=-1, voice_actor_id=-1)
