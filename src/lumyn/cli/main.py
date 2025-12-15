import typer

from lumyn.version import __version__

app = typer.Typer(add_completion=False)


@app.callback()
def _root() -> None:
    """Lumyn CLI."""


@app.command()
def version() -> None:
    """Print Lumyn version."""

    typer.echo(__version__)


def main() -> None:
    app()
