from datetime import date
import importlib.util
from pathlib import Path
import sys
from types import ModuleType

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

def test_concurrent_check_in_returns_the_winning_record(tmp_path, monkeypatch):
    # 插件导入会连接生产数据库；仅加载模型和服务，使用隔离数据库验证竞争。
    package_name = "check_in_test_package"
    package = ModuleType(package_name)
    package.__path__ = []
    monkeypatch.setitem(sys.modules, package_name, package)
    plugin_dir = Path(__file__).resolve().parents[1] / "backend/bot/plugins/mention_command"

    def load_module(name):
        fullname = f"{package_name}.{name}"
        spec = importlib.util.spec_from_file_location(fullname, plugin_dir / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, fullname, module)
        spec.loader.exec_module(module)
        return module

    models = load_module("models")
    services = load_module("services")
    CheckIn = models.CheckIn
    engine = create_engine(f"sqlite:///{tmp_path / 'checkins.db'}")
    models.Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    session = sessions()
    original_commit = session.commit

    def concurrent_commit():
        with sessions() as other:
            other.add(CheckIn(
                user_id=-123,
                group_id=-456,
                check_in_date=date.today(),
                lucky_actor_id=7,
                lucky_image_id=8,
            ))
            other.commit()
        original_commit()

    monkeypatch.setattr(session, "commit", concurrent_commit)
    monkeypatch.setattr(services, "get_session", lambda: session)

    assert services.CheckInService.check_in(-123, -456, 10, 11) == (False, 1, 7, 8)
    with sessions() as verify:
        assert verify.query(CheckIn).count() == 1
    engine.dispose()
