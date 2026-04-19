import asyncio
import os
from pathlib import Path
from typing import Annotated, List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from pydantic_ai import Agent

from local_first_common.pydantic_ai_utils import (
    build_model,
    PROVIDER_DEFAULTS,
    VALID_PROVIDERS,
)
from local_first_common.personas import list_personas, get_persona
from local_first_common.cli import (
    init_config_option,
    dry_run_option,
    no_llm_option,
    resolve_dry_run,
)
from local_first_common.tracking import register_tool, track_llm_run

from .schema import TrollReport
from .prompts import build_system_prompt, build_user_prompt
from .persistence import save_troll_report

TOOL_NAME = "pedantic-troll"


class PedanticTrollError(Exception):
    """Base typed error for pedantic-troll."""


class ModelBuildError(PedanticTrollError):
    """Raised when LLM model construction fails."""


class NitpickRunError(PedanticTrollError):
    """Raised when the LLM nitpicking run fails."""


DEFAULTS = {"provider": "ollama", "model": "llama3"}
_TOOL = register_tool(TOOL_NAME)

console = Console()
err_console = Console(stderr=True)
app = typer.Typer(
    help="Nitpicks blog post series for internal consistency and continuity errors."
)


def display_troll_report(report: TrollReport):
    """Rich display of the Troll's grievances."""
    console.print(
        Panel(
            report.intro,
            title="[bold red]The Pedantic Troll Speaks[/bold red]",
            border_style="red",
        )
    )

    if not report.grievances:
        console.print(
            "\n[bold green]Miraculously, the Troll found nothing to complain about.[/bold green]"
        )
    else:
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Post", style="dim")
        table.add_column("Severity", style="bold")
        table.add_column("Quote", style="italic")
        table.add_column("Complaint")

        for g in report.grievances:
            color = (
                "red"
                if g.severity == "error" or g.severity == "contradiction"
                else "yellow"
            )
            table.add_row(
                g.post_reference,
                f"[{color}]{g.severity.upper()}[/{color}]",
                g.quote_snippet,
                g.complaint,
            )
        console.print(table)

    console.print(f"\n[bold]VERDICT:[/bold] {report.verdict}")


@app.command()
def nitpick(
    drafts: Annotated[
        Optional[List[Path]],
        typer.Argument(help="List of markdown drafts for the series."),
    ] = None,
    premise: Annotated[
        Optional[str],
        typer.Option(
            "--premise", "-e", help="Series premise text or path to premise file."
        ),
    ] = "A technical blog series for developers.",
    provider_name: Annotated[
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
    persona_name: Annotated[
        Optional[str], typer.Option("--persona", help="Name of a persona to use.")
    ] = None,
    vault: Annotated[
        Optional[Path],
        typer.Option("--vault", help="Override the Obsidian vault path."),
    ] = None,
    dry_run: Annotated[bool, dry_run_option()] = False,
    no_llm: Annotated[bool, no_llm_option()] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
    list_personas_flag: Annotated[
        bool, typer.Option("--list-personas", help="List available personas.")
    ] = False,
    init_config: Annotated[bool, init_config_option(TOOL_NAME, DEFAULTS)] = False,
):
    """Critique a series of blog post drafts."""

    # Handle --list-personas
    if list_personas_flag:
        personas = list_personas()
        if not personas:
            err_console.print("[yellow]No personas found.[/yellow]")
            raise typer.Exit(1)
        console.print("\n[bold]Available Personas (Util & Brand):[/bold]\n")
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
        posts_data.append({"title": d.name, "content": d.read_text()})

    if not posts_data:
        console.print("[red]No valid drafts found to analyze.[/red]")
        raise typer.Exit(1)

    # 3. Resolve Model
    actual_provider = "mock" if no_llm else provider_name
    actual_model = "test-model" if no_llm else model

    try:
        pai_model = build_model(actual_provider, actual_model)
    except ModelBuildError as e:
        console.print(f"[red]Error building model:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error building model:[/red] {e}")
        raise typer.Exit(1)

    model_name = actual_model or PROVIDER_DEFAULTS.get(actual_provider, "unknown")

    # 4. Resolve Persona and System Prompt
    if persona_name:
        # Search in Brand first, then Util
        try:
            p = get_persona(persona_name, "Brand", vault_path=vault)
        except FileNotFoundError:
            try:
                p = get_persona(persona_name, "Util", vault_path=vault)
            except FileNotFoundError:
                err_console.print(
                    f"[red]Error:[/red] Persona '{persona_name}' not found."
                )
                raise typer.Exit(1)

        # Mix the persona prompt with the nitpicking instructions
        system = build_system_prompt(premise_text, p.system_prompt)
    else:
        # Default to Pedantic Troll from Util
        try:
            p = get_persona("Pedantic Troll", "Util", vault_path=vault)
            system = build_system_prompt(premise_text, p.system_prompt)
        except FileNotFoundError:
            err_console.print(
                "[yellow]Pedantic Troll persona not found. Run 'bootstrap' to create it.[/yellow]"
            )
            raise typer.Exit(1)

    user = build_user_prompt(posts_data)

    if verbose:
        console.print(
            f"Nitpicking {len(posts_data)} drafts using {actual_provider}:{model_name}..."
        )

    try:
        with track_llm_run(
            "pedantic-troll",
            f"{actual_provider}:{model_name}",
            source_location=str(drafts[0].parent),
        ) as run:
            agent = Agent(pai_model, output_type=TrollReport, system_prompt=system)
            result = asyncio.run(agent.run(user))
            report = result.output
            run.track(result, item_count=len(posts_data))
    except NitpickRunError as e:
        console.print(f"[red]Error during nitpicking: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error during nitpicking: {e}[/red]")
        raise typer.Exit(1)

    display_troll_report(report)

    if dry_run:
        console.print(
            "\n[yellow][dry-run] Nitpicking complete. No feelings were actually hurt.[/yellow]"
        )
    else:
        # Save to database
        source_loc = str(drafts[0].parent) if drafts else "unknown"
        save_troll_report(report, source_loc, premise_text)
        console.print(
            "\n[green]Grievances recorded in Content Quality history.[/green]"
        )


@app.command()
def bootstrap(
    vault: Optional[Path] = typer.Option(
        None, "--vault", help="Override the Obsidian vault path."
    ),
):
    """Create the Pedantic Troll persona in your vault if it's missing."""
    from local_first_common.obsidian import find_vault_root

    try:
        root = vault or find_vault_root()
    except Exception as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    troll_path = root / "personas" / "Util" / "Pedantic Troll.md"
    if troll_path.exists():
        console.print(f"[green]Pedantic Troll already exists at:[/green] {troll_path}")
        return

    content = """# Pedantic Troll
**Archetype:** Annoying Critic
**Category:** [[Persona]]

## Lens
You are the Pedantic Troll, an annoying-but-accurate critic of blog post series. You care deeply about facts and internal consistency. You find it physically painful when an author uses a code example in Post 2 that relies on a concept they don't explain until Post 4. You hate repeated analogies.

## System Prompt Seed
> You are smug, pedantic, and slightly condescending. Your job is to find internal consistency issues, contradictions, and continuity errors. Flag contradictions, continuity errors, drift from the premise, and repetitive analogies.
"""

    troll_path.parent.mkdir(parents=True, exist_ok=True)
    troll_path.write_text(content, encoding="utf-8")
    console.print(f"[bold green]Created Pedantic Troll at:[/bold green] {troll_path}")


if __name__ == "__main__":
    app()
