from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_frontend_covers_every_known_status_and_unknown_is_not_success():
    source = (PROJECT_ROOT / "frontend/src/views/OverviewView.vue").read_text(encoding="utf-8")
    for status in ("success", "error", "cooldown", "no_image", "file_missing"):
        assert f"{status}:" in source
    fallback = source.split("function statusMetaOf", 1)[1].split("const maxTrend", 1)[0]
    assert "未知" in fallback
    assert "tagType: 'info'" in fallback
    assert "?? knownStatusMeta.success" not in fallback
