"""CLI using Typer."""

import typer

app = typer.Typer(name="CLI using Typer")


@app.command()
def say_hi(name):
    """Say hello to the user."""
    typer.echo(f"Hello: {name}")


@app.command()
def goodbye():
    """Say goodbye to the user."""
    typer.echo("Goodbye!")


@app.command()
def greet(name: str):
    """Send kind regards to the user."""
    typer.echo(f"Kind regards, {name}")


@app.command()
def welcome(name: str, greeting: str = "Hello", enthusiastic: bool = False):
    """Welcome the user with a customer greeting."""
    if enthusiastic:
        typer.echo(f"{greeting}, {name}!!!")
    else:
        typer.echo(f"{greeting}, {name}")


if __name__ == "__main__":
    app()
