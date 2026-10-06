"""Registry of lab checkers. Each one writes its runs into the lab's own `runs/` folder (committed = evidence)."""

from .. import config
from . import integration

SUITES = {
    "integration": {
        "run": integration.run,
        "suite": integration.suite,
        "runs_dir": config.LABS_DIR / "02-enterprise-integration" / "lab" / "runs",
    },
}
