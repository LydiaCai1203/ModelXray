from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()


def print_report(result: dict, claimed_model: str) -> None:
    confidence: dict[str, float] = result["confidence"]
    top_models = list(confidence.items())[:5]

    console.print()
    console.print(Panel(f"[bold]Claimed model:[/bold] {claimed_model}", box=box.ROUNDED))

    table = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan")
    table.add_column("Rank", width=6)
    table.add_column("Model", min_width=30)
    table.add_column("Confidence", width=12)
    table.add_column("Bar", min_width=20)

    for i, (model_id, conf) in enumerate(top_models):
        bar_len = int(conf * 30)
        bar = "[green]" + "█" * bar_len + "[/green]" + "░" * (30 - bar_len)
        pct = f"{conf * 100:.1f}%"
        rank = f"#{i+1}"
        table.add_row(rank, model_id, pct, bar)

    console.print(table)

    if top_models:
        best_model, best_conf = top_models[0]
        if best_conf > 0.6:
            verdict = f"[bold green]Likely: {best_model}[/bold green] ({best_conf*100:.1f}%)"
        elif best_conf > 0.35:
            verdict = f"[bold yellow]Uncertain: possibly {best_model}[/bold yellow] ({best_conf*100:.1f}%)"
        else:
            verdict = "[bold red]Inconclusive — model not in probe database[/bold red]"
        console.print(Panel(verdict, title="Verdict", box=box.ROUNDED))

    console.print(f"[dim]Probes run: {result['total_probes']}[/dim]")
    console.print()
