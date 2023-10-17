"""
Deadline interfacing functions for the BreakTools Deadline Web App 
by Mervin van Brakel (2023)

In order to speed up reads the backend only fetches "fresh" 
information from the Deadline Web Service every x amount of seconds, 
depending on which type of information is fetched. If not enough
time has passed, the backend will send the information that was
stored in memory. 
"""

from dataclasses import dataclass
from datetime import datetime
from os import getenv

import Deadline.DeadlineConnect as DeadlineConnect
from dotenv import load_dotenv

from utility_functions import (
    get_clean_date,
    get_clean_job_data,
    get_clean_job_detail_data,
    get_clean_task_data,
    get_constructed_image_path,
)

load_dotenv()

WEB_SERVICE_IP_ADDRESS = getenv("WEB_SERVICE_IP")
WEB_SERVICE_PORT = getenv("WEB_SERVICE_PORT")


@dataclass
class jobs_data:
    """Class for storing active jobs."""

    last_refresh: datetime
    jobs: dict


class deadline_connection:
    """This class handles everything related to the deadline web service.
    It stores job data in memory and has functions for requesting information."""

    deadline_connection = DeadlineConnect.DeadlineCon(
        WEB_SERVICE_IP_ADDRESS, WEB_SERVICE_PORT
    )

    async def set_initial_data(self) -> None:
        """This function sets the initial data when the class is initialized."""
        self.active_jobs = jobs_data(datetime.now(), await self.get_fresh_active_jobs())
        self.recent_jobs = jobs_data(datetime.now(), await self.get_fresh_recent_jobs())
        self.older_jobs = jobs_data(datetime.now(), await self.get_fresh_older_jobs())
        print("[BreakTools] Successfully fetched initial data")

    async def get_job_details_and_tasks(self, job_id: str) -> dict:
        """This function returns cleaned data from a single job."""

        job_details = self.deadline_connection.Jobs.GetJobDetails(job_id)

        # Deadline returns error messages as strings instead of raised exceptions,
        # so if job_details is a string we know the job id is invalid.
        if isinstance(job_details, str):
            return {"type": "error", "error": "invalid_jobId"}

        job_details_and_tasks = {
            "job": get_clean_job_detail_data(
                job_id,
                self.deadline_connection.Jobs.GetJobDetails(job_id),
            ),
            "tasks": get_clean_task_data(
                self.deadline_connection.Tasks.GetJobTasks(job_id)
            ),
        }

        return job_details_and_tasks

    async def get_job_error(self, job_id: str, task_id: int) -> dict:
        """This function retrieves the error task report for the given job and task."""

        try:
            return self.deadline_connection.TaskReports.GetAllTaskErrorReportsContents(
                job_id, task_id
            )[0]
        except IndexError:
            return "Error: Could not find any crash reports."

    async def get_job_warning(self, job_id: str, task_id: int) -> dict:
        """This function retrieves the whole task report for the given job and task."""

        try:
            return self.deadline_connection.TaskReports.GetAllTaskReportsContents(
                job_id, task_id
            )[0]
        except IndexError:
            return "Error: Could not find any crash reports."

    async def get_task_image_path(self, job_id: str, task_id: int) -> str:
        """This function retrieves the path to an exr file for a given job and task."""

        task_frame_range = self.deadline_connection.Tasks.GetJobTask(job_id, task_id)[
            "Frames"
        ]

        output_path = self.deadline_connection.Jobs.GetJobDetails(job_id)[job_id][
            "Output Directories"
        ]["Output Path 1"]

        file_name = self.deadline_connection.Jobs.GetJobDetails(job_id)[job_id][
            "Output Filenames"
        ]["Output File 1"]

        return get_constructed_image_path(task_frame_range, output_path, file_name)

    async def get_fresh_active_jobs(self) -> dict:
        """This function retrieves all active jobs from the Deadline Web Service."""

        active_jobs = self.deadline_connection.Jobs.GetJobsInState("Active")

        cleaned_active_jobs = {}
        for job in active_jobs:
            cleaned_date = get_clean_date(job["DateStart"])
            cleaned_active_jobs[job["_id"]] = get_clean_job_data(job, cleaned_date)

        return cleaned_active_jobs

    async def get_active_jobs(self) -> dict:
        """This function returns the active jobs stored in memory.
        If 3 seconds have passed since the last update it fetches
        fresh information and returns that instead."""

        if (datetime.now() - self.active_jobs.last_refresh).total_seconds() > 3:
            self.active_jobs.last_refresh = datetime.now()
            self.active_jobs.jobs = await self.get_fresh_active_jobs()

            return self.active_jobs.jobs

        else:
            return self.active_jobs.jobs

    async def get_fresh_recent_jobs(self) -> dict:
        """This function returns a fresh list of inactive jobs that occured
        less than 48 hours ago."""

        inactive_jobs = self.deadline_connection.Jobs.GetJobsInStates(
            ["Suspended", "Completed", "Failed", "Pending"]
        )
        recent_jobs = {}

        for job in inactive_jobs:
            cleaned_date = get_clean_date(job["DateStart"])
            if (datetime.now() - cleaned_date).total_seconds() < 172800:
                recent_jobs[job["_id"]] = get_clean_job_data(job, cleaned_date)

        return recent_jobs

    async def get_recent_jobs(self) -> dict:
        """This function returns the recent jobs stored in memory.
        If 1 minute has passed since the last update it fetches
        fresh information and returns that instead."""

        if (datetime.now() - self.recent_jobs.last_refresh).total_seconds() > 60:
            self.recent_jobs.last_refresh = datetime.now()
            self.recent_jobs.jobs = await self.get_fresh_recent_jobs()

            return self.recent_jobs.jobs

        else:
            return self.recent_jobs.jobs

    async def get_fresh_older_jobs(self) -> dict:
        """This function returns a fresh list of jobs that occured more than 48 hours ago,
        but less than 2 weeks ago. Feel free to change according to your definition of old.
        """

        inactive_jobs = self.deadline_connection.Jobs.GetJobsInStates(
            ["Suspended", "Completed", "Failed", "Pending"]
        )
        older_jobs = {}

        for job in inactive_jobs:
            cleaned_date = get_clean_date(job["DateStart"])

            if 172800 < (datetime.now() - cleaned_date).total_seconds() < 483840:
                older_jobs[job["_id"]] = get_clean_job_data(job, cleaned_date)

        return older_jobs

    async def get_older_jobs(self) -> dict:
        """This function returns the older jobs stored in memory.
        If an hour has passed since the last update it fetches
        fresh information and returns that instead."""

        if (datetime.now() - self.older_jobs.last_refresh).total_seconds() > 3600:
            self.older_jobs.last_refresh = datetime.now()
            self.older_jobs.jobs = await self.get_fresh_older_jobs()

            return self.older_jobs.jobs

        else:
            return self.older_jobs.jobs
