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
import time

import requests
import cherrypy
import uuid
import jsonschema
from deepdiff import DeepDiff

sys.path.append("../../")
from mp1.models import *


class AppTrafficRulesController:

    @cherrypy.tools.json_in()
    @json_out(cls=NestedEncoder)
    def support_traffic_rules_post(self, appInstanceId: str):

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

        data = cherrypy.request.json

        try:
            trafficRule = TrafficRules.from_json(data)

        except (TypeError, jsonschema.exceptions.ValidationError) as e:
            error = BadRequest(e)
            return error.message()

        if appStatus['indication'] == IndicationType.READY.name:

            # Add appInstanceId for internal usage
            cherrypy.thread_data.db.create(
                "trafficRules",
                object_to_mongodb_dict(
                    trafficRule,
                    extra=dict(appInstanceId=appInstanceId) ),
            )

            cherrypy.response.status = 201
            return trafficRule


        else:
            error_msg = "Application %s is in %s state. This operation not allowed in this state." % (
            appInstanceId, appStatus["indication"])
            error = Forbidden(error_msg)
            return error.message()

    @json_out(cls=NestedEncoder)
    def app_traffic_rules_get(self, appInstanceId: str):

        cherrypy.respose.status = 200
        return None

    @json_out(cls=NestedEncoder)
    def app_traffic_rules_get_with_rule_id(self, appInstanceId: str,
                                                  trafficRuleId: str):
        cherrypy.respose.status = 200
        return None


    @cherrypy.tools.json_in()
    @json_out(cls=NestedEncoder)
    def app_traffic_rules_put(self, appInstanceId: str,
                                    trafficRuleId: str):

        cherrypy.respose.status = 200
        return None

