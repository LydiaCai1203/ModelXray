from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()


def print_report(result: dict, claimed_model: str, verbose: bool = False) -> None:
    confidence: dict[str, float] = result["confidence"]
    top_models = list(confidence.items())[:5]

    console.print()
    console.print(Panel(f"[bold]Claimed model:[/bold] {claimed_model}", box=box.ROUNDED))

    if verbose:
        console.print("\n[bold cyan]Probe Details:[/bold cyan]")
        for r in result["probe_results"]:
            resp_preview = r.response[:120].replace("\n", " ")
            scores_str = ", ".join(f"{m}={s:.1f}" for m, s in sorted(r.scores.items(), key=lambda x: -x[1])[:3])
            if r.response.startswith("ERROR:"):
                console.print(f"  [red]{r.probe_id}[/red]: {resp_preview}")
            else:
                console.print(f"  [green]{r.probe_id}[/green]: {resp_preview}")
                if scores_str:
                    console.print(f"    [dim]Top scores: {scores_str}[/dim]")
        console.print()

    table = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan")
    table.add_column("Rank", width=6)
    table.add_column("Model", min_width=30)
    table.add_column("Confidence", width=12)
    table.add_column("Bar", min_width=20)

    for i, (model_id, conf) in enumerate(top_models):
        bar_len = int(conf * 30)
        bar = "[green]" + "\u2588" * bar_len + "[/green]" + "\u2591" * (30 - bar_len)
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
    else:
        console.print(Panel(
            "[bold red]No matches found. All probes may have failed. Run with --verbose to debug.[/bold red]",
            title="Verdict",
            box=box.ROUNDED,
        ))

    console.print(f"[dim]Probes run: {result['total_probes']}[/dim]")
    console.print()
