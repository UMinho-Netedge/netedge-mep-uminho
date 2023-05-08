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

import json
import sys
from time import time_ns
import cherrypy

sys.path.append("../../")
from mp1.models import *
import uuid
import jsonschema


class AppTokenController:

    @cherrypy.tools.json_in()
    @json_out(cls=NestedEncoder)
    def get_credentials(self, **kwargs):
        """"
        This method retrieves the application OAuth 2.0 credentials
        
        :return: Credentials or ProblemDetails
        """

        try:
            data = cherrypy.request.json
            cherrypy.log("Received a get credentials request")
            appInstanceId = data['appInstanceId']
            cherrypy.log('appInstanceId: '+appInstanceId)
        except (TypeError, jsonschema.exceptions.ValidationError) as e:
            error = BadRequest(e)
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

        credentials = appStatus["oauth"]
        
        return credentials