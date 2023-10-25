"""
OpenAI related functions for the Deadline Web App by Mervin van Brakel (2023)
"""


import asyncio
import json
from os import getenv, path, sep
from random import uniform

import openai
from dotenv import load_dotenv
from tiktoken import get_encoding
from websockets import exceptions

load_dotenv()
openai.api_key = getenv("OPENAI_API_KEY")

with open(
    path.join(path.dirname(path.realpath(__file__)).replace(sep, "/"), "prompts.json"),
    "r",
) as file:
    prompts = json.load(file)

GENERATED_PROMPTS = {}


async def create_ai_text(
    job_details: dict, job_id: str, DEADLINE_CONNECTION, websocket
) -> None:
    """This function figures out which prompt to send to OpenAI,
    then it runs the prompt through the send_ai_text function."""
    prompt_information = {}

    total_chunks = (
        int(job_details["job"]["Completed"])
        + int(job_details["job"]["Failed"])
        + int(job_details["job"]["Pending"])
        + int(job_details["job"]["Queued"])
        + int(job_details["job"]["Rendering"])
        + int(job_details["job"]["Suspended"])
    )

    # Job finished without issues
    if (
        total_chunks == int(job_details["job"]["Completed"])
        and int(job_details["job"]["Errors"]) == 0
    ):
        prompt_information["type"] = "finished_successfully"
        prompt_information["log_type_to_retrieve"] = None

    # Job finished but with warnings
    elif (
        total_chunks == int(job_details["job"]["Completed"])
        and int(job_details["job"]["Errors"]) != 0
        and int(job_details["job"]["Failed"]) == 0
        and int(job_details["job"]["Pending"]) == 0
    ):
        prompt_information["type"] = "finished_warnings"
        prompt_information["log_type_to_retrieve"] = "warning"

    # Job partially failed
    elif total_chunks == (
        int(job_details["job"]["Completed"])
        + int(job_details["job"]["Failed"])
        + int(job_details["job"]["Suspended"])
    ):
        prompt_information["type"] = "finished_partially"
        prompt_information["log_type_to_retrieve"] = "error"

    # Job failed completely
    elif total_chunks == int(job_details["job"]["Failed"]):
        prompt_information["type"] = "finished_failed"
        prompt_information["log_type_to_retrieve"] = "error"

    # Job running without issues
    elif (
        total_chunks != int(job_details["job"]["Completed"])
        and int(job_details["job"]["Errors"]) == 0
        and int(job_details["job"]["Failed"]) == 0
    ):
        prompt_information["type"] = "running_successfully"
        prompt_information["log_type_to_retrieve"] = None

    # Job running, hasn't finished anything and has only warnings
    elif (
        total_chunks != int(job_details["job"]["Completed"])
        and int(job_details["job"]["Completed"]) == 0
        and int(job_details["job"]["Errors"]) != 0
        and int(job_details["job"]["Failed"]) == 0
    ):
        prompt_information["type"] = "running_only_warnings"
        prompt_information["log_type_to_retrieve"] = "warning"

    # Job running but with warnings
    elif (
        total_chunks != int(job_details["job"]["Completed"])
        and int(job_details["job"]["Errors"]) != 0
        and int(job_details["job"]["Failed"]) == 0
    ):
        prompt_information["type"] = "running_warnings"
        prompt_information["log_type_to_retrieve"] = "warning"

    # Job running but with fails
    elif (
        total_chunks != int(job_details["job"]["Completed"])
        and int(job_details["job"]["Errors"]) != 0
        and int(job_details["job"]["Failed"]) != 0
    ):
        prompt_information["type"] = "running_fails"
        prompt_information["log_type_to_retrieve"] = "error"

    try:
        # We first try to send ai generated text from memory.
        await fake_send_ai_text(
            GENERATED_PROMPTS[job_id][prompt_information["type"]], job_id, websocket
        )
    except KeyError:
        # If we have no ai generated text in memory, we generate and store it.
        match prompt_information["log_type_to_retrieve"]:
            case None:
                log = ""

            case "warning":
                first_error_log_id = await get_first_error_log_id(job_details["tasks"])

                if first_error_log_id is not None:
                    log = await DEADLINE_CONNECTION.get_job_warning(
                        job_id, first_error_log_id
                    )
                else:
                    log = "Error! Could not find any warning logs."

            case "error":
                first_error_log_id = await get_first_error_log_id(job_details["tasks"])

                if first_error_log_id is not None:
                    log = await DEADLINE_CONNECTION.get_job_error(
                        job_id, first_error_log_id
                    )
                else:
                    log = "Error! Could not find any error logs."

        await send_ai_text(
            prompt_information["type"],
            prompts[prompt_information["type"]].replace("[LOG]", log),
            job_id,
            websocket,
        )


async def send_ai_text(prompt_type: str, prompt: str, job_id: str, websocket) -> None:
    """This function takes the prompt and sends it to OpenAI,
    then it streams the response it receives to the client."""

    await websocket.send(
        json.dumps(
            {
                "type": "ai_text",
                "job_id": job_id,
                "reset": True,
            }
        )
    )

    prompt_length = await get_token_size(prompt)

    if 4000 < prompt_length < 16000:
        model = "gpt-3.5-turbo-16k-0613"
    elif prompt_length > 16000:
        model = "gpt-3.5-turbo"
        prompt = prompts["log_too_log"]
    else:
        model = "gpt-3.5-turbo"

    try:
        response = await openai.ChatCompletion.acreate(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": prompts["system_text"],
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            stream=True,
        )

        final_prompt = ""
        async for chunk in response:
            try:
                await websocket.send(
                    json.dumps(
                        {
                            "type": "ai_text",
                            "job_id": job_id,
                            "reset": False,
                            "chunk": chunk.choices[0].delta.content,
                        }
                    )
                )
                final_prompt += chunk.choices[0].delta.content

            except exceptions.ConnectionClosed:
                return

            except AttributeError:
                pass

        try:
            GENERATED_PROMPTS[job_id][prompt_type] = final_prompt
        except KeyError:
            GENERATED_PROMPTS[job_id] = {}
            GENERATED_PROMPTS[job_id][prompt_type] = final_prompt

    except openai.error.ServiceUnavailableError:
        response = "Error: OpenAI service couldn't be reached. Try reloading the page."

        try:
            await websocket.send(
                json.dumps(
                    {
                        "type": "ai_text",
                        "job_id": job_id,
                        "reset": False,
                        "chunk": response,
                    }
                )
            )

        except exceptions.ConnectionClosed:
            return


async def fake_send_ai_text(prompt: str, job_id: str, websocket) -> None:
    """This function mimics the sending of ChatGPT responses. It is
    used for sending already generated text without it looking different
    from fresh responses. Why? Because it looks cool :)"""
    await websocket.send(
        json.dumps(
            {
                "type": "ai_text",
                "job_id": job_id,
                "reset": True,
            }
        )
    )

    for word in prompt.split():
        try:
            await websocket.send(
                json.dumps(
                    {
                        "type": "ai_text",
                        "job_id": job_id,
                        "reset": False,
                        "chunk": f" {word}",
                    }
                )
            )
            await asyncio.sleep(uniform(0.1, 0.2))
        except exceptions.ConnectionClosed:
            return


async def get_token_size(prompt: str) -> int:
    """This function gets a token size from the prompt input,
    it is useful for determining which OpenAI model to use."""
    encoding = get_encoding("cl100k_base")
    return len(encoding.encode(prompt))


async def get_first_error_log_id(tasks: list) -> int | None:
    """This function gets the ID for the first task with an error,
    so ChatGPT can parse it. It returns None if no errors are found,
    which weirdly enough happens sometimes."""
    for task in tasks:
        if task["Errs"] >= 1:
            return task["TaskID"]

    return None
