"""Registry of lab checkers. Each one writes its runs into the lab's own `runs/` folder (committed = evidence)."""

from .. import config
from . import integration, lakeside, platforms, savanna

SUITES = {
    "integration": {
        "run": integration.run,
        "suite": integration.suite,
        "runs_dir": config.LABS_DIR / "02-enterprise-integration" / "lab" / "runs",
    },
    "lakeside": {
        "run": lakeside.run,
        "suite": lakeside.suite,
        "runs_dir": config.ENGAGEMENTS_DIR / "lakeside" / "runs",
        "async": True,
    },
    "savanna": {
        "run": savanna.run,
        "suite": savanna.suite,
        "runs_dir": config.ENGAGEMENTS_DIR / "savanna" / "runs",
        "async": True,
    },
    "platforms": {
        "run": platforms.run,
        "suite": platforms.suite,
        "runs_dir": config.LABS_DIR / "06-enterprise-platforms" / "lab" / "runs",
        "async": True,
    },
}
