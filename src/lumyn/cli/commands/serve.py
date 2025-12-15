from __future__ import annotations

from pathlib import Path

import typer

from lumyn.config import load_settings

from ..util import die

app = typer.Typer(help="Run the Lumyn FastAPI service (uvicorn).")


@app.callback(invoke_without_command=True)
def main(
    *,
    host: str = typer.Option("127.0.0.1", "--host", help="Bind host."),
    port: int = typer.Option(8000, "--port", help="Bind port."),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload (dev only)."),
    config_path: Path | None = typer.Option(
        None,
        "--config",
        help="Optional config TOML path (else uses LUMYN_CONFIG_PATH/env defaults).",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Print effective config and exit without starting."
    ),
) -> None:
    try:
        settings = load_settings(config_path=config_path)
    except Exception as e:
        die(str(e))

    typer.echo("Lumyn service")
    typer.echo(f"url: http://{host}:{port}")
    typer.echo(f"storage_url: {settings.lumyn.storage_url}")
    typer.echo(f"policy_path: {settings.lumyn.policy_path}")
    typer.echo(f"mode: {settings.lumyn.mode}")
    typer.echo(f"redaction_profile: {settings.lumyn.redaction_profile}")
    typer.echo(f"top_k: {settings.lumyn.top_k}")
    typer.echo(f"signing: {'enabled' if settings.service.signing_secret else 'disabled'}")

    if dry_run:
        typer.echo(
            "uvicorn --factory lumyn.api.app:create_app "
            f"--host {host} --port {port}" + (" --reload" if reload else "")
        )
        return

    try:
        import uvicorn  # type: ignore[import-not-found]
    except Exception:
        die(
            "uvicorn not installed; install with `pip install uvicorn` "
            "(or `pip install lumyn[service]`)."
        )

    uvicorn.run(
        "lumyn.api.app:create_app",
        factory=True,
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )
