"""CLI using Typer."""

import typer

app = typer.Typer(name="CLI using Typer")


@app.callback()
def main():
    """CLI entry point."""
    typer.echo("Welcome to the CLI!")


@app.command()
def say_hi(name):
    """Say hello to the user."""
    typer.echo(f"Hello: {name}")


@app.command()
def goodbye():
    """Say goodbye to the user."""
    typer.echo("Goodbye!")


if __name__ == "__main__":
    app()
