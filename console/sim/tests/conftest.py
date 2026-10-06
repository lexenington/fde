import pytest

from sim import config, llm
from sim.crm import store


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    """Every test gets its own output folders, a clean simulator and no real API."""
    monkeypatch.setattr(config, "PRACTICE_DIR", tmp_path / "practice")
    monkeypatch.setattr(config, "LABS_DIR", tmp_path / "labs")
    store.clear_conditions()
    store.reset()
    llm.set_backend(None)
    yield
    llm.set_backend(None)
    store.clear_conditions()
