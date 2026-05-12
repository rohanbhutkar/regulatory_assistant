from __future__ import annotations

from pathlib import Path

from agents.ema_json_index import EmaJsonIndex


def test_ema_json_cache_falls_back_when_default_unwritable(
    tmp_path: Path, monkeypatch
) -> None:
    bad_cache = tmp_path / "app" / ".cache" / "ema_json"
    xdg_cache = tmp_path / "xdg-cache"
    expected_fallback = xdg_cache / "regulatory_bot" / "ema_json"
    monkeypatch.setenv("XDG_CACHE_HOME", str(xdg_cache))

    original_mkdir = Path.mkdir

    def fake_mkdir(self: Path, *args, **kwargs):
        if self == bad_cache:
            raise PermissionError("permission denied")
        return original_mkdir(self, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", fake_mkdir)

    index = EmaJsonIndex()
    index._cache_dir = bad_cache

    index._ensure_cache_dir()

    assert index._cache_dir == expected_fallback
    assert expected_fallback.is_dir()


def test_ema_json_cache_uses_configured_writable_directory(tmp_path: Path) -> None:
    cache_dir = tmp_path / "ema-cache"
    index = EmaJsonIndex()
    index._cache_dir = cache_dir

    index._ensure_cache_dir()

    assert index._cache_dir == cache_dir
    assert index._cache_path("guidance").parent == cache_dir
