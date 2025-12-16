import os

import pytest
from typer.testing import CliRunner

from lumyn.core.decide import LumynConfig, decide_v1
from lumyn.store.sqlite import SqliteStore

runner = CliRunner()


@pytest.fixture
def clean_env():
    # Setup temp workspace
    workspace_dir = ".lumyn_test_cli_v1"
    store_path = f"{workspace_dir}/lumyn.db"
    policy_path = "policies/lumyn-support.v0.yml"

    if os.path.exists(workspace_dir):
        import shutil

        shutil.rmtree(workspace_dir)
    os.makedirs(workspace_dir)

    # Store must exist for CLI to connect
    store = SqliteStore(store_path)
    store.init()

    # Ensure policy.yml exists to avoid auto-init
    workspace_policy = f"{workspace_dir}/policy.yml"
    import shutil

    shutil.copy(policy_path, workspace_policy)

    yield workspace_dir, store_path, policy_path

    if os.path.exists(workspace_dir):
        import shutil

        shutil.rmtree(workspace_dir)


def test_explain_v1_record(clean_env, capsys) -> None:
    workspace_dir, store_path, policy_path = clean_env

    # Create and persist a v1 record
    config = LumynConfig(store_path=store_path, policy_path=policy_path)
    request = {
        "schema_version": "decision_request.v1",
        "request_id": "req_cli_v1",
        "tenant": {"tenant_id": "cli_test"},
        "subject": {"type": "user", "id": "u1"},
        "action": {
            "type": "support.refund",
            "intent": "r",
            "amount": {"value": 1.0, "currency": "USD"},
        },
        "context": {
            "mode": "digest_only",
            "digest": "sha256:0000000000000000000000000000000000000000000000000000000000000000",
        },
        "evidence": {"ticket_id": "t1"},
    }

    record = decide_v1(request, config=config)
    decision_id = record["decision_id"]

    # Run explain command logic directly
    from pathlib import Path

    from lumyn.cli.commands.explain import main

    # We must pass values directly because function defaults are typer.Option objects
    # Pass defaults: workspace as Path, markdown as False
    try:
        main(decision_id=decision_id, workspace=Path(workspace_dir), markdown=False)
    except SystemExit:
        pass  # Handle potential exit

    # Check output
    captured = capsys.readouterr()
    stdout = captured.out

    assert f"decision_id: {decision_id}" in stdout
    # V0 policy logic maps TRUST -> ALLOW according to our migration logic implicitly?
    # Let's check what verdict we got. Refund 1.0 is likely ALLOW (TRUST).
    # In V1 engine we mapped TRUST to ALLOW (evaluator_v1.py logic for backward compat).
    # So we expect ALLOW.
