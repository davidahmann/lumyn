from __future__ import annotations

import os
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class LumynSettings:
    storage_url: str
    policy_path: Path
    mode: str
    redaction_profile: str
    top_k: int


@dataclass(frozen=True, slots=True)
class ServiceSettings:
    signing_secret: str | None


@dataclass(frozen=True, slots=True)
class Settings:
    lumyn: LumynSettings
    service: ServiceSettings


def _parse_storage_url(storage_url: str) -> str:
    # v0 supports sqlite only; keep a stable string for hashing/diagnostics.
    if storage_url.startswith("sqlite:"):
        return storage_url
    raise ValueError("unsupported storage_url (v0 supports sqlite:...)")


def storage_path_from_url(storage_url: str) -> Path:
    if not storage_url.startswith("sqlite:"):
        raise ValueError("unsupported storage_url (v0 supports sqlite:...)")
    raw = storage_url.removeprefix("sqlite:")
    if raw.startswith("///"):
        return Path("/" + raw.removeprefix("///"))
    if raw.startswith("//"):
        return Path("/" + raw.removeprefix("//"))
    if raw == "":
        raise ValueError("sqlite storage_url missing path (e.g. sqlite:.lumyn/lumyn.db)")
    return Path(raw)


def _env_get(env: Mapping[str, str], key: str) -> str | None:
    value = env.get(key)
    if value is None:
        return None
    value = value.strip()
    return value if value != "" else None


def load_settings(
    *,
    config_path: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> Settings:
    env = env or os.environ

    lumyn_defaults: dict[str, object] = {
        "storage_url": "sqlite:.lumyn/lumyn.db",
        "policy_path": "policies/lumyn-support.v0.yml",
        "mode": "enforce",
        "redaction_profile": "default",
        "top_k": 5,
    }
    service_defaults: dict[str, object] = {
        "signing_secret": "",
    }

    config_file_path = config_path
    config_path_env = _env_get(env, "LUMYN_CONFIG_PATH")
    if config_file_path is None and config_path_env is not None:
        config_file_path = Path(config_path_env)

    if config_file_path is not None and config_file_path.exists():
        raw = tomllib.loads(config_file_path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            raw_lumyn = raw.get("lumyn")
            if isinstance(raw_lumyn, dict):
                lumyn_defaults.update(raw_lumyn)
            raw_service = raw.get("service")
            if isinstance(raw_service, dict):
                service_defaults.update(raw_service)

    storage_url = _env_get(env, "LUMYN_STORAGE_URL") or str(lumyn_defaults["storage_url"])
    storage_url = _parse_storage_url(storage_url)

    policy_path = Path(_env_get(env, "LUMYN_POLICY_PATH") or str(lumyn_defaults["policy_path"]))

    mode = (_env_get(env, "LUMYN_MODE") or str(lumyn_defaults["mode"])).strip().lower()
    if mode not in {"enforce", "advisory"}:
        raise ValueError("LUMYN_MODE must be 'enforce' or 'advisory'")

    redaction_profile = (
        _env_get(env, "LUMYN_REDACTION_PROFILE") or str(lumyn_defaults["redaction_profile"])
    ).strip()
    if redaction_profile not in {"default", "strict", "off"}:
        raise ValueError("LUMYN_REDACTION_PROFILE must be default|strict|off")

    top_k_raw = _env_get(env, "LUMYN_TOP_K") or str(lumyn_defaults["top_k"])
    try:
        top_k = int(top_k_raw)
    except ValueError as e:
        raise ValueError("LUMYN_TOP_K must be an integer") from e
    if top_k < 0:
        raise ValueError("LUMYN_TOP_K must be >= 0")

    signing_secret = _env_get(env, "LUMYN_SIGNING_SECRET")
    if signing_secret is None:
        signing_secret = str(service_defaults["signing_secret"]).strip() or None

    return Settings(
        lumyn=LumynSettings(
            storage_url=storage_url,
            policy_path=policy_path,
            mode=mode,
            redaction_profile=redaction_profile,
            top_k=top_k,
        ),
        service=ServiceSettings(signing_secret=signing_secret),
    )
