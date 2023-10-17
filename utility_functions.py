"""
Utility functions for the BreakTools Deadline Web App by Mervin van Brakel (2023)
"""

from datetime import datetime
from os import path


def get_clean_job_data(job: dict, date: datetime) -> dict:
    """This function extracts only the job information we need for
    the Web App to function."""

    cleaned_job_data = {}
    cleaned_job_data["Name"] = job["Props"]["Name"]
    cleaned_job_data["User"] = job["Props"]["User"]

    try:
        cleaned_job_data["EpochStarted"] = date.timestamp()
    except ValueError:
        # EpochStarted is used for sorting only, so we can
        # sort it to the end of the list if no date is set.
        cleaned_job_data["EpochStarted"] = 0

    cleaned_job_data["CompletedChunks"] = job["CompletedChunks"]
    cleaned_job_data["QueuedChunks"] = job["QueuedChunks"]
    cleaned_job_data["SuspendedChunks"] = job["SuspendedChunks"]
    cleaned_job_data["RenderingChunks"] = job["RenderingChunks"]
    cleaned_job_data["FailedChunks"] = job["FailedChunks"]
    cleaned_job_data["PendingChunks"] = job["PendingChunks"]

    cleaned_job_data["Errs"] = job["Errs"]

    return cleaned_job_data


def get_clean_job_detail_data(job_id: str, job_details: dict) -> dict:
    """This function extracts only the job detail information we need
    for the Web App to function."""

    job = job_details.get(job_id)

    cleaned_job_detail_data = {}
    cleaned_job_detail_data["Name"] = job["Job"]["Name"]
    cleaned_job_detail_data["User"] = job["Job"]["User"]
    cleaned_job_detail_data["Submit_Date"] = job["Job"]["Submit Date"]

    cleaned_job_detail_data["Completed"] = job["Task States"]["Completed"]
    cleaned_job_detail_data["Failed"] = job["Task States"]["Failed"]
    cleaned_job_detail_data["Pending"] = job["Task States"]["Pending"]
    cleaned_job_detail_data["Queued"] = job["Task States"]["Queued"]
    cleaned_job_detail_data["Rendering"] = job["Task States"]["Rendering"]
    cleaned_job_detail_data["Suspended"] = job["Task States"]["Suspended"]
    cleaned_job_detail_data["Errors"] = job["Job"]["Errors"]

    cleaned_job_detail_data["Estimated_Time_Remaining"] = job["Statistics"][
        "Estimated Time Remaining"
    ]
    cleaned_job_detail_data["Average_Task_Time"] = job["Statistics"][
        "Average Task Time"
    ]

    return cleaned_job_detail_data


def get_clean_task_data(job_tasks: dict) -> list:
    """This function extracts only the task information we need
    for the Web App to function."""

    cleaned_task_data = [
        {
            "TaskID": task["TaskID"],
            "Frames": task["Frames"],
            "Errs": task["Errs"],
            "Prog": task["Prog"],
        }
        for task in job_tasks["Tasks"]
    ]

    return cleaned_task_data


def get_clean_date(dirty_date: str) -> datetime:
    """This function parses Deadline's ISO8601 date to a Python datetime object.
    For the life of me I couldn't get it to just work in one line."""

    date_year_month_day = dirty_date[:10]
    date_hour_minute_second = dirty_date[11:19]
    cleaned_date = datetime.strptime(
        f"{date_year_month_day} {date_hour_minute_second}", "%Y-%m-%d %H:%M:%S"
    )

    return cleaned_date


def get_dict_differences(dictionary_1: dict, dictionary_2: dict) -> dict:
    """This function compares two dictionaries and returns only the
    data that has changed between the two. I'm going to be honest here,
    ChatGPT wrote this one and I have no idea how it works."""

    dictionary_3 = {}
    for key, value in dictionary_2.items():
        if key in dictionary_1:
            if isinstance(value, dict) and isinstance(dictionary_1[key], dict):
                nested_diff = get_dict_differences(dictionary_1[key], value)
                if nested_diff:
                    dictionary_3[key] = nested_diff
            elif value != dictionary_1[key]:
                dictionary_3[key] = value
        else:
            dictionary_3[key] = value

    return dictionary_3


def get_constructed_image_path(
    frame_range: str, output_path: str, file_name: str
) -> str:
    """This function constructs the image path for the exr image previews.
    It expects the file names to follow proper conventions, but I've added a few
    edge cases for the artist who are more creative with their file naming."""

    first_frame = frame_range.split("-")[0]

    if int(first_frame) < 1000:
        if len(first_frame) != 4:
            zero_string = "0000"

            for number in range(len(first_frame)):
                zero_string = zero_string[:-1]

            first_frame = f"{zero_string}{first_frame}"

    if "####" in file_name:
        constructed_file_name = file_name.replace("####", first_frame)
    elif "%04d" in file_name:
        constructed_file_name = file_name.replace("%04d", first_frame)
    else:
        print(f"Unhandled file format requested: {file_name}")
        constructed_file_name = ""

    path_to_file = path.join(output_path, constructed_file_name)
    return path_to_file
