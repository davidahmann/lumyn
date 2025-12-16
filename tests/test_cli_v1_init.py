import os
import shutil
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from lumyn.cli.commands.init import app

runner = CliRunner()


@pytest.fixture
def clean_workspace():
    workspace = ".lumyn_test_init_v1"
    if os.path.exists(workspace):
        shutil.rmtree(workspace)
    yield workspace
    if os.path.exists(workspace):
        shutil.rmtree(workspace)


def test_init_creates_v1_policy(clean_workspace) -> None:
    result = runner.invoke(app, ["--workspace", clean_workspace])
    assert result.exit_code == 0

    policy_path = Path(clean_workspace) / "policy.yml"
    assert policy_path.exists()

    content = yaml.safe_load(policy_path.read_text())
    assert content.get("schema_version") == "policy.v1"
    assert content.get("policy_id") == "starter-policy"
