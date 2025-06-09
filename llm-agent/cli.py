"""Command-line interface placeholder."""

import typer

app = typer.Typer()

@app.command()
def main():
    """Run the agent."""
    typer.echo("Agent starting...")

if __name__ == "__main__":
    app()
