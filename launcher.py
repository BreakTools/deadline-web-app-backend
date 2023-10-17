"""
Backend for the BreakTools Deadline Web App by Mervin van Brakel (2023)

This is the Python file you should run to start the backend.
"""

import asyncio
from os import getenv

from dotenv import load_dotenv

load_dotenv()


def check_or_ask_for_env(key: str, text: str) -> bool:
    """This function checks if an environment variable is set."""
    value = getenv(key)

    if not value:
        print(text)
        return False
    else:
        return True


def all_variables_set() -> bool:
    """This function checks if all of our environment variables are
    set, if they aren't we return false."""
    can_run = True

    if not check_or_ask_for_env(
        "WEBSOCKET_PORT",
        "Your WebSocket environment variable is not set. Please set it.",
    ):
        can_run = False

    if not check_or_ask_for_env(
        "WEB_SERVICE_IP",
        "Your Deadline web service IP environment variable is not set. Please set it.",
    ):
        can_run = False

    if not check_or_ask_for_env(
        "WEB_SERVICE_PORT",
        "Your Deadline web server port enviroment variable is not set. Please set it.",
    ):
        can_run = False
    if not check_or_ask_for_env(
        "OPENAI_API_KEY",
        "Your OpenAI key environment variable is not set. Please set it.",
    ):
        can_run = False

    return can_run


if __name__ == "__main__":
    if all_variables_set():
        from websocket_handler import start_websocket_server

        asyncio.run(start_websocket_server())
