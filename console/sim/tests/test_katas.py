"""Every kata must ship red (no test passes against the stub) and go fully green with the reference solution."""

import shutil
from pathlib import Path

import pytest

from sim import config, katas

SOLUTIONS = Path(__file__).resolve().parents[1] / "content" / "katas" / "solutions"
REPO_KATAS = Path(__file__).resolve().parents[3] / "katas"

pytestmark = pytest.mark.skipif(not REPO_KATAS.exists(), reason="needs a repo checkout (the katas folder is not in the Docker image)")


def kata_dirs():
    return sorted(p.name for p in REPO_KATAS.iterdir() if p.is_dir()) if REPO_KATAS.exists() else []


@pytest.fixture
def katas_dir(monkeypatch, tmp_path):
    dst = tmp_path / "katas"
    shutil.copytree(REPO_KATAS, dst, ignore=shutil.ignore_patterns("__pycache__"))
    monkeypatch.setattr(config, "KATAS_DIR", dst)
    return dst


def test_there_are_thirteen_katas():
    assert len(kata_dirs()) == 13


@pytest.mark.parametrize("kata", kata_dirs())
def test_stub_is_red_and_solution_is_green(kata, katas_dir):
    d = katas_dir / kata
    module = next(p for p in d.glob("*.py") if not p.name.startswith("test_"))
    red = katas.run(kata)
    assert red["passed"] == 0 and red["failed"] > 0, f"{kata}: the stub already passes {red['passed']} tests"
    shutil.copy(SOLUTIONS / module.name, d / module.name)
    green = katas.run(kata)
    assert green["failed"] == 0 and green["passed"] == red["failed"], green["output"]


def test_listing_and_detail(katas_dir):
    listed = katas.list_katas()
    assert len(listed) == 13 and listed[0]["id"].startswith("01-") and listed[0]["timebox"]
    assert "Kata" in katas.detail(listed[0]["id"])["readme"]
    assert katas.detail("../etc") is None and katas.run("nope") is None
