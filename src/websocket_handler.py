"""
WebSocket related functions for the Deadline Web App by Mervin van Brakel (2023)

This backend only fecthes information whenever a user is using the Web App.
Update speed depends on which page the user is looking at.
The homepage will be updated every 3 seconds, only sending the needed changes.
The render job specific page will get an update every second, 
only sending the needed changes.
"""

import asyncio
import json
from dataclasses import dataclass
from os import getenv

import websockets
from dotenv import load_dotenv

import deadline_interfacing
from image_handling import send_image_preview
from openai_interfacing import create_ai_text
from utility_functions import get_dict_differences

load_dotenv()
DEADLINE_CONNECTION = deadline_interfacing.deadline_connection()


@dataclass
class websocket_connection:
    """Class for storing websocket connection data."""

    connected: bool
    looking_at_job: bool
    subscribed_updates: list
    job_id: str
    last_sent_data: dict
    data_type_to_send: str
    data_to_send: dict


async def update_client_information(
    connection_data: websocket_connection, websocket
) -> None:
    """This function updates the client every 3 seconds on the homepage and every
    1 second on the job detail page. It only sends the differences, because student
    cellular data is not infinite, y'know. Gotta keep that data small."""

    while connection_data.connected:
        if connection_data.looking_at_job:
            if "error" not in connection_data.last_sent_data["job_details"]:
                connection_data.data_to_send["job_details"] = (
                    await DEADLINE_CONNECTION.get_job_details_and_tasks(
                        connection_data.job_id
                    )
                )

                differences_to_send = get_dict_differences(
                    connection_data.last_sent_data["job_details"],
                    connection_data.data_to_send["job_details"],
                )

                if differences_to_send != {}:
                    try:
                        await websocket.send(
                            json.dumps(
                                {
                                    "type": "job_details",
                                    "data": differences_to_send,
                                    "update": True,
                                }
                            )
                        )
                    except websockets.exceptions.ConnectionClosed:
                        connection_data.connected = False
                        return

                # If error appears, rewrite AI text
                if (
                    int(connection_data.last_sent_data["job_details"]["job"]["Errors"])
                    == 0
                    and int(
                        connection_data.data_to_send["job_details"]["job"]["Errors"]
                    )
                    != 0
                ):
                    asyncio.create_task(
                        create_ai_text(
                            connection_data.data_to_send["job_details"],
                            connection_data.job_id,
                            DEADLINE_CONNECTION,
                            websocket,
                        )
                    )

                # If task fails, rewrite AI text
                elif (
                    int(connection_data.last_sent_data["job_details"]["job"]["Failed"])
                    == 0
                    and int(
                        connection_data.data_to_send["job_details"]["job"]["Failed"]
                    )
                    != 0
                ):
                    asyncio.create_task(
                        create_ai_text(
                            connection_data.data_to_send["job_details"],
                            connection_data.job_id,
                            DEADLINE_CONNECTION,
                            websocket,
                        )
                    )

                connection_data.last_sent_data["job_details"] = (
                    connection_data.data_to_send["job_details"]
                )

            await asyncio.sleep(1)

        else:
            for data_type_to_send in connection_data.subscribed_updates:
                match data_type_to_send:
                    case "active_jobs":
                        connection_data.data_to_send[data_type_to_send] = (
                            await DEADLINE_CONNECTION.get_active_jobs()
                        )
                    case "recent_jobs":
                        connection_data.data_to_send[data_type_to_send] = (
                            await DEADLINE_CONNECTION.get_recent_jobs()
                        )
                    case "older_jobs":
                        connection_data.data_to_send[data_type_to_send] = (
                            await DEADLINE_CONNECTION.get_older_jobs()
                        )

                differences_to_send = get_dict_differences(
                    connection_data.last_sent_data[data_type_to_send],
                    connection_data.data_to_send[data_type_to_send],
                )

                if differences_to_send != {}:
                    try:
                        await websocket.send(
                            json.dumps(
                                {
                                    "type": data_type_to_send,
                                    "data": differences_to_send,
                                    "update": True,
                                }
                            )
                        )
                    except websockets.exceptions.ConnectionClosed:
                        connection_data.connected = False
                        return

                connection_data.last_sent_data[data_type_to_send] = (
                    connection_data.data_to_send[data_type_to_send]
                )

            await asyncio.sleep(3)


async def websocket_connection_handler(websocket):
    """This function handles WebSocket connection and sends
    information based on the requests it receives. It also spawns
    a seperate process that handles updating the information."""

    connection_data = websocket_connection(False, False, [], "", {}, None, {})

    while True:
        try:
            message = await websocket.recv()
        except websockets.exceptions.ConnectionClosed:
            connection_data.connected = False
            return

        try:
            parsed_message = json.loads(message)

            match parsed_message["body"]:
                case "get_active_jobs":
                    connection_data.looking_at_job = False
                    connection_data.subscribed_updates.append("active_jobs")
                    connection_data.data_type_to_send = "active_jobs"
                    connection_data.data_to_send["active_jobs"] = (
                        await DEADLINE_CONNECTION.get_active_jobs()
                    )

                case "get_recent_jobs":
                    connection_data.looking_at_job = False
                    connection_data.subscribed_updates.append("recent_jobs")
                    connection_data.data_type_to_send = "recent_jobs"
                    connection_data.data_to_send["recent_jobs"] = (
                        await DEADLINE_CONNECTION.get_recent_jobs()
                    )

                case "get_older_jobs":
                    connection_data.looking_at_job = False
                    connection_data.subscribed_updates.append("older_jobs")
                    connection_data.data_type_to_send = "older_jobs"
                    connection_data.data_to_send["older_jobs"] = (
                        await DEADLINE_CONNECTION.get_older_jobs()
                    )

                case "get_job_details":
                    connection_data.looking_at_job = True
                    connection_data.subscribed_updates = []

                    if parsed_message["jobId"] != "undefined":
                        connection_data.job_id = parsed_message["jobId"]
                        connection_data.data_type_to_send = "job_details"
                        connection_data.data_to_send["job_details"] = (
                            await DEADLINE_CONNECTION.get_job_details_and_tasks(
                                parsed_message["jobId"]
                            )
                        )

                case "get_image_preview":
                    asyncio.create_task(
                        send_image_preview(
                            websocket,
                            DEADLINE_CONNECTION,
                            parsed_message["jobId"],
                            parsed_message["taskId"],
                        )
                    )

                    connection_data.data_to_send = None

        except Exception as error:
            print(f"[BreakTools] Parsing client data failed. Error: {error}")

        if connection_data.data_to_send is not None:
            try:
                await websocket.send(
                    json.dumps(
                        {
                            "type": connection_data.data_type_to_send,
                            "data": connection_data.data_to_send[
                                connection_data.data_type_to_send
                            ],
                            "update": False,
                        }
                    )
                )

            except websockets.exceptions.ConnectionClosed:
                connection_data.connected = False
                return

            connection_data.last_sent_data[connection_data.data_type_to_send] = (
                connection_data.data_to_send[connection_data.data_type_to_send]
            )

            if connection_data.data_type_to_send == "job_details":
                asyncio.create_task(
                    create_ai_text(
                        connection_data.last_sent_data["job_details"],
                        parsed_message["jobId"],
                        DEADLINE_CONNECTION,
                        websocket,
                    )
                )

        connection_data.data_to_send = {}

        if not connection_data.connected:
            asyncio.create_task(update_client_information(connection_data, websocket))
            connection_data.connected = True


async def start_websocket_server() -> None:
    """This function starts the WebSocket server asynchronously,
    so multiple people can use the web app at the same time."""

    await DEADLINE_CONNECTION.set_initial_data()

    async with websockets.serve(websocket_connection_handler, "", 80):
        print("[BreakTools] Started WebSocket server.")
        await asyncio.Future()
