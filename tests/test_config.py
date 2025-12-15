from __future__ import annotations

from pathlib import Path

import pytest

from lumyn.config import load_settings


def test_config_env_overrides_file(tmp_path: Path) -> None:
    cfg_path = tmp_path / "lumyn.toml"
    cfg_contents = "\n".join(
        [
            "[lumyn]",
            'storage_url = "sqlite:from_file.db"',
            'policy_path = "policies/lumyn-support.v0.yml"',
            'mode = "advisory"',
            'redaction_profile = "strict"',
            "top_k = 2",
            "",
            "[service]",
        ]
    )
    cfg_contents += "\n" + 'signing_secret = "from_file_value"' + "\n"  # pragma: allowlist secret
    cfg_path.write_text(cfg_contents, encoding="utf-8")

    settings = load_settings(
        config_path=cfg_path,
        env={
            "LUMYN_MODE": "enforce",
            "LUMYN_TOP_K": "7",
            "LUMYN_SIGNING_SECRET": "from_env_value",  # pragma: allowlist secret
        },
    )

    assert settings.lumyn.storage_url == "sqlite:from_file.db"
    assert settings.lumyn.mode == "enforce"
    assert settings.lumyn.top_k == 7
    assert settings.service.signing_secret == "from_env_value"  # pragma: allowlist secret


def test_config_validates_mode() -> None:
    with pytest.raises(ValueError):
        load_settings(env={"LUMYN_MODE": "bad"})
