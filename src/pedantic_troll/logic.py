from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from local_first_common.providers import PROVIDERS
from local_first_common.cli import (
    provider_option,
    model_option,
    dry_run_option,
    no_llm_option,
    verbose_option,
    debug_option,
    resolve_provider,
    resolve_dry_run,
)
from local_first_common.tracking import register_tool, timed_run

from .schema import TrollReport
from .prompts import build_system_prompt, build_user_prompt

_TOOL = register_tool("pedantic-troll")
console = Console()
app = typer.Typer(help="Nitpicks blog post series for internal consistency and continuity errors.")

def display_troll_report(report: TrollReport):
    """Rich display of the Troll's grievances."""
    console.print(Panel(report.intro, title="[bold red]The Pedantic Troll Speaks[/bold red]", border_style="red"))

    if not report.grievances:
        console.print("\n[bold green]Miraculously, the Troll found nothing to complain about.[/bold green]")
    else:
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Post", style="dim")
        table.add_column("Severity", style="bold")
        table.add_column("Quote", style="italic")
        table.add_column("Complaint")

        for g in report.grievances:
            color = "red" if g.severity == "error" or g.severity == "contradiction" else "yellow"
            table.add_row(
                g.post_reference,
                f"[{color}]{g.severity.upper()}[/{color}]",
                g.quote_snippet,
                g.complaint
            )
        console.print(table)

    console.print(f"\n[bold]VERDICT:[/bold] {report.verdict}")

@app.command()
def nitpick(
    drafts: List[Path] = typer.Argument(..., help="List of markdown drafts for the series."),
    premise: Optional[str] = typer.Option("A technical blog series for developers.", "--premise", "-p", help="Series premise text or path to premise file."),
    provider: str = provider_option(PROVIDERS),
    model: Optional[str] = model_option(),
    dry_run: bool = dry_run_option(),
    no_llm: bool = no_llm_option(),
    verbose: bool = verbose_option(),
    debug: bool = debug_option(),
):
    """Critique a series of blog post drafts."""
    dry_run = resolve_dry_run(dry_run, no_llm)

    # 1. Resolve premise
    premise_text = premise
    if Path(premise).exists():
        premise_text = Path(premise).read_text()
    
    # 2. Load drafts
    posts_data = []
    for d in drafts:
        if not d.exists():
            console.print(f"[red]Error: Draft file {d} not found.[/red]")
            continue
        posts_data.append({
            "title": d.name,
            "content": d.read_text()
        })
    
    if not posts_data:
        console.print("[red]No valid drafts found to analyze.[/red]")
        raise typer.Exit(1)

    # 3. LLM Review
    try:
        llm = resolve_provider(PROVIDERS, provider, model, debug=debug, no_llm=no_llm)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

    system = build_system_prompt(premise_text)
    user = build_user_prompt(posts_data)

    if verbose:
        console.print(f"Nitpicking {len(posts_data)} drafts using {llm.model}...")

    try:
        with timed_run("pedantic-troll", llm.model, source_location=str(drafts[0].parent)) as run:
            response = llm.complete(system, user, response_model=TrollReport)
            result = response
            run.item_count = len(posts_data)
    except Exception as e:
        console.print(f"[red]Error during nitpicking: {e}[/red]")
        raise typer.Exit(1)

    display_troll_report(result)

    if dry_run:
        console.print("\n[yellow][dry-run] Nitpicking complete. No feelings were actually hurt.[/yellow]")

if __name__ == "__main__":
    app()
