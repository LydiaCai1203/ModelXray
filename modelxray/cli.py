import typer
from .client import create_client, VALID_API_TYPES
from .detector import detect
from .report import print_report, console

app = typer.Typer(help="Detect the real model behind any OpenAI-compatible API.")


@app.command()
def run(
    base_url: str = typer.Option(..., "--base-url", "-b", help="API base URL"),
    api_key: str = typer.Option(..., "--api-key", "-k", help="API key"),
    model: str = typer.Option(..., "--model", "-m", help="Model name to test"),
    api_type: str = typer.Option("openai-chat", "--api-type", "-t",
        help="API protocol: openai-chat | openai-responses | anthropic"),
    mode: str = typer.Option("standard", "--mode", help="Detection mode: quick | standard"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show probe details"),
):
    if api_type not in VALID_API_TYPES:
        console.print(
            f"[bold red]Error:[/bold red] Unknown api-type '{api_type}'. "
            f"Valid types: {', '.join(VALID_API_TYPES)}"
        )
        raise typer.Exit(code=1)

    client = create_client(api_type=api_type, base_url=base_url, api_key=api_key, model=model)

    with console.status("[bold cyan]Running probes...[/bold cyan]"):
        result = detect(client, mode=mode)

    print_report(result, claimed_model=model, verbose=verbose)
