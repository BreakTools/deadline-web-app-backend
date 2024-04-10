"""This file contains a tiny restructured version of the Deadline standalone Python API.
The Python API can only be retrieved from a Deadline installation, which makes it very tedious
to use in a containerized environment as you have to manually copy it. Thus I've recreated it here
in this file so this backend can be easily installed. It's a bit messy though, I'm afraid..
"""

from __future__ import absolute_import
import json
import base64
import ssl
import traceback

from urllib.request import urlopen, Request
from urllib.error import HTTPError


class DeadlineCon:
    def __init__(self, host, port, useTls=False, caCert=None, insecure=False):
        address = host + ":" + str(port)
        self.connectionProperties = ConnectionProperty(
            address, False, useTls, caCert, insecure
        )

        self.Jobs = Jobs(self.connectionProperties)
        self.Tasks = Tasks(self.connectionProperties)
        self.TaskReports = TaskReports(self.connectionProperties)


class ConnectionProperty:
    def __init__(
        self, address, useAuth=False, useTls=True, caCert=None, insecure=False
    ):
        self.address = address
        self.useAuth = useAuth
        self.user = ""
        self.password = ""
        self.useTls = useTls
        self.caCert = caCert
        self.insecure = insecure

    def __get__(self, commandString):
        return send(
            self.address,
            commandString,
            "GET",
            None,
            self.useAuth,
            self.user,
            self.password,
            self.useTls,
            self.caCert,
            self.insecure,
        )


class Jobs:
    def __init__(self, connectionProperties):
        self.connectionProperties = connectionProperties

    def GetJobsInStates(self, states):
        return self.connectionProperties.__get__("/api/jobs?States=" + ",".join(states))

    def GetJobsInState(self, state):
        return self.connectionProperties.__get__("/api/jobs?States=" + state)

    def GetJobDetails(self, ids):
        script = "/api/jobs"

        script = script + "?JobID=" + ArrayToCommaSeparatedString(ids) + "&Details=true"
        return self.connectionProperties.__get__(script)


class Tasks:
    def __init__(self, connectionProperties):
        self.connectionProperties = connectionProperties

    def GetJobTasks(self, id):
        return self.connectionProperties.__get__("/api/tasks?JobID=" + id)

    def GetJobTask(self, jobId, taskId):
        result = self.connectionProperties.__get__(
            "/api/tasks?JobID=" + jobId + "&TaskID=" + str(taskId)
        )

        if isinstance(result, list) and len(result) > 0:
            result = result[0]

        return result


class TaskReports:
    def __init__(self, connectionProperties):
        self.connectionProperties = connectionProperties

    def GetAllTaskReportsContents(self, jobId, taskId):
        return self.connectionProperties.__get__(
            "/api/taskreports?JobID="
            + jobId
            + "&TaskID="
            + str(taskId)
            + "&Data=allcontents"
        )

    def GetAllTaskErrorReportsContents(self, jobId, taskId):
        return self.connectionProperties.__get__(
            "/api/taskreports?JobID="
            + jobId
            + "&TaskID="
            + str(taskId)
            + "&Data=allerrorcontents"
        )


def ArrayToCommaSeparatedString(iterable):
    if isinstance(iterable, str):
        return iterable

    if iterable is None:
        return ""

    return ",".join(str(x) for x in iterable)


def send(
    address,
    message,
    requestType,
    body=None,
    useAuth=False,
    username="",
    password="",
    useTls=True,
    caCert=None,
    insecure=False,
):
    try:
        httpString = "https://" if useTls else "http://"
        if not address.startswith(httpString):
            address = httpString + address
        url = address + message

        if body is not None:
            request = Request(url, data=body.encode("utf-8"))
            request.add_header("Content-Type", "application/json; charset=utf-8")
        else:
            request = Request(url)

        request.get_method = lambda: requestType

        if useAuth:
            userPassword = "%s:%s" % (username, password)
            userPasswordEncoded = base64.b64encode(
                userPassword.encode("utf-8")
            ).decode()
            request.add_header("Authorization", "Basic %s" % userPasswordEncoded)

        context = None
        if useTls:
            context = ssl.create_default_context(cafile=caCert)
            context.check_hostname = not insecure
            context.verify_mode = ssl.CERT_NONE if insecure else ssl.CERT_REQUIRED

        response = urlopen(request, context=context)

        data = response.read().decode()
        data = data.replace("\n", " ")

        try:
            data = json.loads(data)
        except:
            pass
        return data

    except HTTPError as e:
        if e.code == 401:
            return "Error: HTTP Status Code 401. Authentication with the Web Service failed. Please ensure that the authentication credentials are set, are correct, and that authentication mode is enabled."
        else:
            return traceback.print_exc()
    except Exception as e:
        return traceback.print_exc()
