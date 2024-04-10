"""
Image related functions for the Deadline Web App by Mervin van Brakel (2023) 
"""

# If you're having issues installing OpenEXR on windows, try these commands:
# pip install pipwin, pipwin install openexr, pip install openexr.
import json
from base64 import b64encode
from io import BytesIO

from Imath import PixelType
from numpy import float32, frombuffer, where
from OpenEXR import InputFile
from PIL import Image


async def send_image_preview(
    websocket, DEADLINE_CONNECTION, job_id: str, task_id: str
) -> None:
    """This function sends a Base64 JPEG image preview to a client."""
    if not await DEADLINE_CONNECTION.check_if_job_exists(job_id):
        return

    if not task_id.isdigit():
        return

    try:
        path_to_exr = await DEADLINE_CONNECTION.get_task_image_path(job_id, task_id)
    except KeyError:
        await websocket.send(
            json.dumps(
                {
                    "type": "image_preview",
                    "task_id": task_id,
                    "error": True,
                    "message": "Error: Could not find the output folder on deadline.",
                }
            )
        )
        return

    try:
        base64_image = await get_base64_encoded_jpeg_from_exr(path_to_exr)

        await websocket.send(
            json.dumps(
                {
                    "type": "image_preview",
                    "task_id": task_id,
                    "error": False,
                    "image": base64_image,
                }
            )
        )

    except TypeError:
        await websocket.send(
            json.dumps(
                {
                    "type": "image_preview",
                    "task_id": task_id,
                    "error": True,
                    "message": "Error: Could not extract RGB channels from EXR.",
                }
            )
        )

    except OSError:
        await websocket.send(
            json.dumps(
                {
                    "type": "image_preview",
                    "task_id": task_id,
                    "error": True,
                    "message": "Error: Could not find image file.",
                }
            )
        )


async def get_base64_encoded_jpeg_from_exr(path_to_exr: str) -> str:
    """This functions takes an EXR file, then converts it
    to a Base64 encoded JPEG so we can send it easily over the web."""
    jpeg_data = await convert_exr_to_jpeg(path_to_exr)
    bytes_buffer = BytesIO()
    jpeg_data.save(bytes_buffer, "JPEG", quality=50)
    return b64encode(bytes_buffer.getvalue()).decode()


async def convert_exr_to_jpeg(path_to_exr) -> Image.Image:
    """This function takes an EXR and convert it to a JPEG,
    using 2.4 gamma encoding. Thanks to drakeguan on GitHub
    for figuring this out and sharing the code."""
    exr_file = InputFile(path_to_exr.replace("\\", "/"))
    pixel_type = PixelType(PixelType.FLOAT)
    data_window = exr_file.header()["dataWindow"]
    image_size = (
        data_window.max.x - data_window.min.x + 1,
        data_window.max.y - data_window.min.y + 1,
    )
    rgb = [
        frombuffer(exr_file.channel(color, pixel_type), dtype=float32)
        for color in "RGB"
    ]

    for i in range(3):
        rgb[i] = where(
            rgb[i] <= 0.0031308,
            (rgb[i] * 12.92) * 255.0,
            (1.055 * (rgb[i] ** (1.0 / 2.4)) - 0.055) * 255.0,
        )

    rgb_8_bit = [
        Image.frombuffer("F", image_size, color.tobytes()).convert("L") for color in rgb
    ]

    return Image.merge("RGB", rgb_8_bit)
