from textwrap import dedent
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.reasoning import ReasoningTools
from agno.tools import tool
from agno.utils.log import logger
from agno.tools.shell import ShellTools
from agno.storage.sqlite import SqliteStorage




reasoning_agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[ReasoningTools(add_instructions=True), ShellTools()],
    instructions=dedent("""\
        You are an expert problem-solving assistant with strong analytical, system administration and IoT skills! 🧠
        The User will ask for questions about the system this software is currently running on. You should have complete idea of the environment you are currently running on.
        Your job is to act as a mediator with reasoning capabilities to understand the user's queries properly and determine appropriete tool calls to answer the user's queries.
        You judge the output from the terminal commands and reason further to provide a final answer to the user.
        \
    """),
    add_datetime_to_instructions=True,
    stream_intermediate_steps=True,
    show_tool_calls=True,
    markdown=True,
    storage=SqliteStorage(table_name="reasoning_agent_sessions", db_file="tmp/data.db"),
    add_history_to_messages=True,
    num_history_runs=3,
)

if __name__ == "__main__":
    logger.info("Starting interactive agent CLI. Type 'exit' or 'quit' to end the session.")
    reasoning_agent.cli_app()
