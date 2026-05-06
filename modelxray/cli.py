from typing import Optional

import typer

from .client import create_client, VALID_API_TYPES
from .detector import detect
from .report import print_report, print_analysis, console

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
    analyst_url: Optional[str] = typer.Option(None, "--analyst-url", help="Analyst model API base URL"),
    analyst_key: Optional[str] = typer.Option(None, "--analyst-key", help="Analyst model API key"),
    analyst_model: Optional[str] = typer.Option(None, "--analyst-model", help="Analyst model name"),
    analyst_type: Optional[str] = typer.Option(None, "--analyst-type", help="Analyst API protocol (defaults to --api-type)"),
):
    if api_type not in VALID_API_TYPES:
        console.print(
            f"[bold red]Error:[/bold red] Unknown api-type '{api_type}'. "
            f"Valid types: {', '.join(VALID_API_TYPES)}"
        )
        raise typer.Exit(code=1)

    # Validate analyst options: all or none (analyst_type is optional, defaults to api_type)
    analyst_opts = [analyst_url, analyst_key, analyst_model]
    analyst_provided = sum(1 for o in analyst_opts if o is not None)
    if analyst_provided not in (0, 3):
        console.print(
            "[bold red]Error:[/bold red] --analyst-url, --analyst-key, and --analyst-model "
            "must all be provided together, or all omitted."
        )
        raise typer.Exit(code=1)

    analyst_api_type = analyst_type or api_type
    if analyst_type and analyst_type not in VALID_API_TYPES:
        console.print(
            f"[bold red]Error:[/bold red] Unknown analyst-type '{analyst_type}'. "
            f"Valid types: {', '.join(VALID_API_TYPES)}"
        )
        raise typer.Exit(code=1)

    client = create_client(api_type=api_type, base_url=base_url, api_key=api_key, model=model)

    with console.status("[bold cyan]Running probes...[/bold cyan]"):
        result = detect(client, mode=mode)

    print_report(result, claimed_model=model, verbose=verbose)

    # AI analysis
    if analyst_provided == 3:
        from .analyst import analyze

        analyst_client = create_client(
            api_type=analyst_api_type,
            base_url=analyst_url,
            api_key=analyst_key,
            model=analyst_model,
        )
        with console.status("[bold cyan]AI analyzing results...[/bold cyan]"):
            analysis = analyze(analyst_client, result, claimed_model=model)
        print_analysis(analysis)
