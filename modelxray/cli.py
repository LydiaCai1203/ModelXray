import typer
from .client import ModelClient
from .detector import detect
from .report import print_report, console

app = typer.Typer(help="Detect the real model behind any OpenAI-compatible API.")


@app.command()
def run(
    base_url: str = typer.Option(..., "--base-url", "-b", help="API base URL"),
    api_key: str = typer.Option(..., "--api-key", "-k", help="API key"),
    model: str = typer.Option(..., "--model", "-m", help="Model name to test"),
    mode: str = typer.Option("standard", "--mode", help="Detection mode: quick | standard"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show probe details"),
):
    client = ModelClient(base_url=base_url, api_key=api_key, model=model)

    with console.status("[bold cyan]Running probes...[/bold cyan]"):
        result = detect(client, mode=mode)

    print_report(result, claimed_model=model, verbose=verbose)
