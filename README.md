# Pedantic Troll

Nitpicks a blog post series for internal consistency issues, contradictions, and continuity errors in the voice of a smug critic.

## Features
- **Series-Wide Analysis**: Compares multiple drafts simultaneously to find drift or contradictions.
- **Troll Persona**: Provides feedback that is both actionable and entertainingly condescending.
- **Grievance Tracking**: Categorizes issues by severity (nit, error, contradiction).
- **Flexible Premise**: Define the series premise to ensure the troll understands the context.

## Installation
```bash
uv sync
```

## Usage
```bash
uv run pedantic-troll nitpick -p "premise.md" drafts/*.md
```

Standard flags supported: `--dry-run`, `--no-llm`, `--provider`, `--model`.
