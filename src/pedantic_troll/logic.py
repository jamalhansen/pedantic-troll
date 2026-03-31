import asyncio
import os
from pathlib import Path
from typing import Annotated, List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from pydantic_ai import Agent

from local_first_common.pydantic_ai_utils import build_model, PROVIDER_DEFAULTS, VALID_PROVIDERS
from local_first_common.personas import list_vault_personas
from local_first_common.cli import (
    dry_run_option,
    no_llm_option,
    resolve_dry_run,
)
from local_first_common.tracking import register_tool, track_llm_run

from .schema import TrollReport
from .prompts import build_system_prompt, build_user_prompt
from .persistence import save_troll_report

_TOOL = register_tool("pedantic-troll")
console = Console()
err_console = Console(stderr=True)
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
    drafts: Annotated[Optional[List[Path]], typer.Argument(help="List of markdown drafts for the series.")] = None,
    premise: Annotated[Optional[str], typer.Option("--premise", "-e", help="Series premise text or path to premise file.")] = "A technical blog series for developers.",
    provider: Annotated[
        str,
        typer.Option(
            "--provider",
            "-p",
            help=f"LLM provider. Choices: {', '.join(VALID_PROVIDERS)}",
        ),
    ] = os.environ.get("MODEL_PROVIDER", "ollama"),
    model: Annotated[
        Optional[str],
        typer.Option("--model", "-m", help="Override the provider's default model."),
    ] = None,
    persona: Annotated[Optional[str], typer.Option("--persona", help="Name of an Obsidian persona to use.")] = None,
    dry_run: bool = dry_run_option(),
    no_llm: bool = no_llm_option(),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
    list_personas: bool = typer.Option(False, "--list-personas", help="List available marketing personas."),
):
    """Critique a series of blog post drafts."""
    
    # Handle --list-personas
    if list_personas:
        personas = list_vault_personas("brand")
        if not personas:
            err_console.print("[yellow]No marketing personas found. Check OBSIDIAN_VAULT_PATH/personas/brand[/yellow]")
            raise typer.Exit(1)
        console.print("\n[bold]Available Marketing Personas:[/bold]\n")
        for p in personas:
            console.print(f"  [cyan]{p.name}[/cyan] ({p.archetype})")
        console.print()
        raise typer.Exit()

    if not drafts:
        err_console.print("[red]Error:[/red] Missing argument 'DRAFTS'.")
        raise typer.Exit(1)

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

    # 3. Resolve Model
    actual_provider = "mock" if no_llm else provider
    actual_model = "test-model" if no_llm else model
    
    try:
        pai_model = build_model(actual_provider, actual_model)
    except Exception as e:
        console.print(f"[red]Error building model:[/red] {e}")
        raise typer.Exit(1)

    model_name = actual_model or PROVIDER_DEFAULTS.get(actual_provider, "unknown")

    # 4. Resolve Persona and System Prompt
    if persona:
        all_personas = list_vault_personas("brand")
        matched = [p for p in all_personas if p.name.lower() == persona.lower()]
        if not matched:
            err_console.print(f"[red]Error:[/red] Persona '{persona}' not found in vault.")
            raise typer.Exit(1)
        p = matched[0]
        # Mix the persona prompt with the nitpicking instructions
        system = f"{p.system_prompt}\n\nYour task is to nitpick the following blog post series based on the premise: {premise_text}. Find contradictions, continuity errors, and repetition. Use your unique voice."
    else:
        system = build_system_prompt(premise_text)

    user = build_user_prompt(posts_data)

    if verbose:
        console.print(f"Nitpicking {len(posts_data)} drafts using {actual_provider}:{model_name}...")

    try:
        with track_llm_run("pedantic-troll", f"{actual_provider}:{model_name}", source_location=str(drafts[0].parent)) as run:
            agent = Agent(pai_model, output_type=TrollReport, system_prompt=system)
            result = asyncio.run(agent.run(user))
            report = result.output
            run.track(result, item_count=len(posts_data))
    except Exception as e:
        console.print(f"[red]Error during nitpicking: {e}[/red]")
        raise typer.Exit(1)

    display_troll_report(report)

    if dry_run:
        console.print("\n[yellow][dry-run] Nitpicking complete. No feelings were actually hurt.[/yellow]")
    else:
        # Save to database
        source_loc = str(drafts[0].parent) if drafts else "unknown"
        save_troll_report(report, source_loc, premise_text)
        console.print("\n[green]Grievances recorded in Content Quality history.[/green]")

if __name__ == "__main__":
    app()
