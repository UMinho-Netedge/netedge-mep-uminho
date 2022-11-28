# Copyright 2022 Centro ALGORITMI - University of Minho
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.


import sys
import cherrypy
from time import time_ns
import jsonschema

sys.path.append("../../")
from mp1.models import *


class InvidualMecServiceLivenessController:
    
    @cherrypy.tools.json_in()
    @json_out(cls=NestedEncoder)
    def mecServiceLiveness_update(self, appInstanceId: str, serviceId: str, **kwargs,):
        """
        This method updates a resource on top of the existing resource state with partial changes described by the client.
        :return: ServiceLivenessInfo or ProblemDetails
        HTTP STATUS CODE: 200, 204, 400, 403, 404, 409, 412
        """
        data = cherrypy.request.json

        # The process of generating the class allows for "automatic" validation of the json

        try:
            livenessUpdate = serviceLivenessUpdate.from_json(data)
        except (TypeError, jsonschema.exceptions.ValidationError) as e:
            error = BadRequest(e)
            return error.message()
        
        #  If kwargs isn't None the get request was made with invalid atributes
        if kwargs != {}:
            error_msg = "Invalid attribute(s): %s" % (str(kwargs))
            error = BadRequest(error_msg)
            return error.message()

        # Check if the appInstanceId has already confirmed ready status
        appStatus = cherrypy.thread_data.db.query_col(
            "appStatus",
            query=dict(appInstanceId=appInstanceId),
            find_one=True,
        )

        # If app does not exist in db
        if appStatus is None:
            error_msg = "Application %s was not found." % (appInstanceId)
            error = NotFound(error_msg)
            return error.message()
        
        # If app exists but it is not ready
        if appStatus["indication"] != IndicationType.READY.name:
            error_msg = "Application %s is in %s state. This operation not allowed in this state." % (
            appInstanceId, appStatus["indication"])
            error = Forbidden(error_msg)
            return error.message()

        # Checks if service already exists or if it is a new one
        hasService = False
        for appService in appStatus["services"]:
            if appService["serInstanceId"] == serviceId:
                hasService = True
                break

        # If it already exists updates service state
        if hasService is False:
            error_msg = "Service %s was not found." % (serviceId)
            error = NotFound(error_msg)
            return error.message()

        if appService["state"] == ServiceState.INACTIVE.name:
            error_msg = "Service %s is in %s state. This operation not allowed in this state." % (
            serviceId, appService["state"])
            error = Conflict(error_msg)
            return error.message()


        appService["timeStamp"] = TimeStamp(time_ns(), time_ns()).to_json()
        if appService["state"] == ServiceState.SUSPENDED.name and livenessUpdate.state == ServiceState.ACTIVE.name:
            appService["state"] = ServiceState.ACTIVE.name
                
        livenessInfo = None

        if appService["liveness"]["update"] == 0:
            cherrypy.response.status = 204
        else:
            livenessInfo = ServiceLivenessInfo(appService["state"], appService["timeStamp"], appService["liveness"]["interval"])
            appService["liveness"]["update"] = 0

        cherrypy.thread_data.db.update(
            "appStatus",
            query=dict(appInstanceId=appInstanceId),
            newdata=dict(services=appStatus["services"])
        )

        return livenessInfo

    @json_out(cls=NestedEncoder)
    def mecServiceLiveness_get(self, appInstanceId: str, serviceId: str, **kwargs,):
        """
        This method retrieves information about an "Individual mecServiceLiveness" resource
        :return: ServiceLivenessInfo or ProblemDetails
        HTTP STATUS CODE: 200, 400, 403, 404
        """

        #  If kwargs isn't None the get request was made with invalid atributes
        if kwargs != {}:
            error_msg = "Invalid attribute(s): %s" % (str(kwargs))
            error = BadRequest(error_msg)
            return error.message()

        # Check if the appInstanceId has already confirmed ready status
        appStatus = cherrypy.thread_data.db.query_col(
            "appStatus",
            query=dict(appInstanceId=appInstanceId),
            find_one=True,
        )

        # If app does not exist in db
        if appStatus is None:
            error_msg = "Application %s was not found." % (appInstanceId)
            error = NotFound(error_msg)
            return error.message()

        # Checks if service already exists or if it is a new one
        hasService = False
        for appService in appStatus["services"]:
            if appService["serInstanceId"] == serviceId:
                hasService = True
                break

        # If it already exists updates service state
        if hasService is False:
            error_msg = "Service %s was not found." % (serviceId)
            error = NotFound(error_msg)
            return error.message()
        
        timeStamp = TimeStamp(appService["timeStamp"]["seconds"], appService["timeStamp"]["nanoseconds"])
        livenessInfo = ServiceLivenessInfo(appService["state"], timeStamp, appService["liveness"]["interval"])

        return livenessInfo
    
