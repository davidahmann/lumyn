import os
import shutil
from collections.abc import Generator
from pathlib import Path

import pytest
import yaml

from lumyn.cli.commands.migrate import main as migrate_main


@pytest.fixture
def clean_workspace() -> Generator[str, None, None]:
    workspace = ".lumyn_test_migrate_v1"
    if os.path.exists(workspace):
        shutil.rmtree(workspace)
    os.makedirs(workspace)
    yield workspace
    if os.path.exists(workspace):
        shutil.rmtree(workspace)


def test_migrate_v0_policy(clean_workspace) -> None:
    # Copy v0 policy to workspace
    src_policy = Path("policies/lumyn-support.v0.yml")
    v0_path = Path(clean_workspace) / "policy.v0.yml"
    shutil.copy(src_policy, v0_path)

    v1_path = Path(clean_workspace) / "policy.v1.yml"

    # Run migrate function directly
    # Note: main uses
    # die() which raises SystemExit on failure. On success it returns None.
    # Typer arguments are passed as keyword args or positional depending on definition.
    # main definition: def main(policy_path: Path, out: Path, force: bool)
    migrate_main(policy_path=v0_path, out=v1_path, force=False)

    # Verify output
    assert v1_path.exists()

    content = yaml.safe_load(v1_path.read_text())
    assert content.get("schema_version") == "policy.v1"
    assert "rules" in content

    # Check rule migration
    rules = content["rules"]
    assert len(rules) > 0
    # Check R007 which had if_all logic
    r007 = next((r for r in rules if r["id"] == "R007"), None)
    assert r007 is not None
    assert "amount_currency_ne" in r007["if_all"][0]  # Check logic preservation

    # Check verdict mapping
    # Check verdict mapping
    r001 = next((r for r in rules if r["id"] == "R001"), None)
    assert r001 is not None
    # R001 was QUERY in v0, should be DENY in v1
    assert r001["then"]["verdict"] == "DENY"
