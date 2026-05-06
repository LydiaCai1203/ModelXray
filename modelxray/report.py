from collections import defaultdict

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from .scorer import ProbeResult, _best_key

console = Console()


def _probe_passed(r: ProbeResult, claimed_model: str) -> bool | None:
    """Check if a probe matched the claimed model's expected pattern.

    Returns True if matched, False if not matched, None if no expectation exists.
    """
    if r.response.startswith("ERROR:"):
        return None
    key = _best_key(list(r.scores.keys()), claimed_model)
    if key is None:
        return None
    return r.scores.get(key, 0.0) >= 1.0


def _short_response(response: str, max_len: int = 50) -> str:
    """Extract a short, readable preview of the response."""
    if response.startswith("ERROR:"):
        return response[:max_len]
    # Take first line, strip whitespace
    first_line = response.split("\n")[0].strip()
    if len(first_line) > max_len:
        return first_line[:max_len - 1] + "\u2026"
    return first_line


def _print_verbose(probe_results: list[ProbeResult], claimed_model: str) -> dict:
    """Print grouped probe results and return stats."""
    groups: dict[str, list[ProbeResult]] = defaultdict(list)
    for r in probe_results:
        cat = r.category or "other"
        groups[cat].append(r)

    passed = 0
    errors = 0

    console.print("\n[bold]\u2501\u2501\u2501 Probe Results \u2501\u2501\u2501[/bold]\n")

    for category in sorted(groups):
        console.print(f" [bold cyan]Category: {category}[/bold cyan]")
        for r in groups[category]:
            is_error = r.response.startswith("ERROR:")
            preview = _short_response(r.response)

            if is_error:
                errors += 1
                console.print(
                    f"  [red]\u2718[/red] {r.probe_id:<35} [red]\u2192 {preview}[/red]"
                )
            else:
                status = _probe_passed(r, claimed_model)
                if status is True:
                    passed += 1
                    console.print(
                        f"  [green]\u2713[/green] {r.probe_id:<35} \u2192 [dim]\"{preview}\"[/dim]"
                    )
                elif status is False:
                    console.print(
                        f"  [yellow]\u2718[/yellow] {r.probe_id:<35} \u2192 [dim]\"{preview}\"[/dim]"
                    )
                else:
                    # No expectation for claimed model
                    console.print(
                        f"  [dim]\u2500[/dim] {r.probe_id:<35} \u2192 [dim]\"{preview}\"[/dim]"
                    )
        console.print()

    return {"passed": passed, "errors": errors}


def print_report(result: dict, claimed_model: str, verbose: bool = False) -> None:
    confidence: dict[str, float] = result["confidence"]
    top_models = list(confidence.items())[:5]

    console.print()
    console.print(Panel(
        f"[bold]Claimed model:[/bold] {claimed_model}",
        box=box.ROUNDED,
    ))

    stats = None
    if verbose:
        stats = _print_verbose(result["probe_results"], claimed_model)

    console.print("[bold]\u2501\u2501\u2501 Results \u2501\u2501\u2501[/bold]\n")

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
            verdict = "[bold red]Inconclusive \u2014 model not in probe database[/bold red]"
        console.print(Panel(verdict, title="Verdict", box=box.ROUNDED))
    else:
        console.print(Panel(
            "[bold red]No matches found. All probes may have failed. Run with --verbose to debug.[/bold red]",
            title="Verdict",
            box=box.ROUNDED,
        ))

    total = result["total_probes"]
    if stats:
        console.print(
            f"[dim]Probes: {total} run, {stats['passed']} passed, {stats['errors']} errors[/dim]"
        )
    else:
        console.print(f"[dim]Probes run: {total}[/dim]")
    console.print()
