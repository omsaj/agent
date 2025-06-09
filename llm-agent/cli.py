"""Command line interface for interacting with the agent."""

from agent.core import LocalAgent
import typer

app = typer.Typer(help="Interact with the local agent")


@app.command()
def chat(text: str) -> None:
    """Send ``text`` to the agent and print the response."""

    agent = LocalAgent()
    response = agent.process_input(text)
    typer.echo(response)


@app.command()
def tool(name: str, input: str) -> None:
    """Run a tool by ``name`` with ``input`` and print the result."""

    agent = LocalAgent()
    result = agent.run_tool(name, input)
    typer.echo(result)


if __name__ == "__main__":
    app()
