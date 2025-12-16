import typer

from lumyn.version import __version__

from .commands import convert as convert_cmd
from .commands import decide as decide_cmd
from .commands import demo as demo_cmd
from .commands import diff as diff_cmd
from .commands import doctor as doctor_cmd
from .commands import explain as explain_cmd
from .commands import export as export_cmd
from .commands import init as init_cmd
from .commands import label as label_cmd
from .commands import learn as learn_cmd
from .commands import migrate as migrate_cmd
from .commands import monitor as monitor_cmd
from .commands import policy as policy_cmd
from .commands import replay as replay_cmd
from .commands import serve as serve_cmd
from .commands import show as show_cmd

app = typer.Typer(add_completion=False)


@app.callback()
def _root() -> None:
    """Lumyn CLI."""


@app.command()
def version() -> None:
    """Print Lumyn version."""

    typer.echo(__version__)


app.command("init")(init_cmd.main)
app.command("demo")(demo_cmd.main)
app.command("decide")(decide_cmd.main)
app.command("show")(show_cmd.main)
app.command("explain")(explain_cmd.main)
app.command("export")(export_cmd.main)
app.command("replay")(replay_cmd.main)
app.command("label")(label_cmd.main)
app.add_typer(policy_cmd.app, name="policy")
app.command("diff")(diff_cmd.main)
app.command("convert")(convert_cmd.main)
app.command("migrate")(migrate_cmd.main)
app.command("monitor")(monitor_cmd.main)
app.command("doctor")(doctor_cmd.main)
app.command("serve")(serve_cmd.main)
app.command("learn")(learn_cmd.main)  # Added this line


def main() -> None:
    app()
