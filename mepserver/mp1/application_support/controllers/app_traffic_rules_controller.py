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
from kubernetes import client, config

class AppTrafficRulesController:

    @json_out(cls=NestedEncoder)
    def traffic_rules_get(self, appInstanceId: str, **kwargs):
        
        if kwargs != {}:
            error_msg = "Invalid attribute(s): %s" % (str(kwargs))
            error = BadRequest(error_msg)
            return error.message()


        appStatus = cherrypy.thread_data.db.query_col(
            "appStatus",
            query=dict(appInstanceId=appInstanceId),
            find_one=True,
        )

        # If app exists in db
        if appStatus is None:
            error_msg = "Application %s does not exist." % (appInstanceId)
            error = NotFound(error_msg)
            return error.message()
    
        if appStatus['indication'] != IndicationType.READY.name:
                error_msg = "App %s state isn't READY." % (appInstanceId)
                error = Forbidden(error_msg)
                return error.message()

        query = {"appInstanceId": appInstanceId}
        
        result = cherrypy.thread_data.db.query_col(
            "trafficRules", 
            query=query,
            fields=dict(appInstanceId=0)
        )
        
        
        cherrypy.response.status = 200
        return list(result)

    @json_out(cls=NestedEncoder)
    def traffic_rule_get_with_traffic_rule_id(self, appInstanceId: str, trafficRuleId: str, **kwargs):
                
        if kwargs != {}:
            error_msg = "Invalid attribute(s): %s" % (str(kwargs))
            error = BadRequest(error_msg)
            return error.message()


        appStatus = cherrypy.thread_data.db.query_col(
            "appStatus",
            query=dict(appInstanceId=appInstanceId),
            find_one=True,
        )

        # If app exists in db
        if appStatus is None:
            error_msg = "Application %s does not exist." % (appInstanceId)
            error = NotFound(error_msg)
            return error.message()
    
        if appStatus['indication'] != IndicationType.READY.name:
                error_msg = "App %s state isn't READY." % (appInstanceId)
                error = Forbidden(error_msg)
                return error.message()

        query = {"trafficRuleId": trafficRuleId}
        
        result = cherrypy.thread_data.db.query_col(
            "trafficRules", 
            query=query,
            fields=dict(appInstanceId=0),
            find_one=True
        )

        # If trafficrule exists in db
        if result is None:
            error_msg = "Traffic rule %s does not exist." % (trafficRuleId)
            error = NotFound(error_msg)
            return error.message()
        
        cherrypy.response.status = 200
        return result


    @cherrypy.tools.json_in()
    @json_out(cls=NestedEncoder)
    def traffic_rules_put(self, appInstanceId: str, trafficRuleId: str):
        
        # config.load_incluster_config()
        # v1 = client.CoreV1Api()
        # print("Listing pods with their IPs:")
        # ret = v1.list_pod_for_all_namespaces(watch=False)
        # for i in ret.items:
        #     print("%s\t%s\t%s" %
        #         (i.status.pod_ip, i.metadata.namespace, i.metadata.name))

        data = cherrypy.request.json
        try:
            trafficRule = TrafficRule.from_json(data)

        except (TypeError, jsonschema.exceptions.ValidationError) as e:
            error = BadRequest(e)
            return error.message()
        
        trafficRule = trafficRule.to_json()
        if trafficRule["trafficRuleId"] != trafficRuleId:
            error_msg = "TrafficRuleId in request body must match the one in URI."
            error = BadRequest(error_msg)
            return error.message()

        appStatus = cherrypy.thread_data.db.query_col(
            "appStatus",
            query=dict(appInstanceId=appInstanceId),
            find_one=True,
        )

        # If app exists in db
        if appStatus is None:
            error_msg = "Application %s does not exist." % (appInstanceId)
            error = NotFound(error_msg)
            return error.message()
    
        if appStatus['indication'] != IndicationType.READY.name:
                error_msg = "App %s state isn't READY." % (appInstanceId)
                error = Forbidden(error_msg)
                return error.message()

        # If trafficrule exists in db
        if trafficRuleId not in appStatus["trafficRules"]:
            error_msg = "Traffic rule %s does not exist." % (trafficRuleId)
            error = NotFound(error_msg)
            return error.message()

        
        query = {"trafficRuleId": trafficRuleId}
        
        result = cherrypy.thread_data.db.query_col("trafficRules", query)


        diff = DeepDiff(result, trafficRule, ignore_order=True)

        # If something changed in the service, must update db
        if (len(diff) > 0):
            # At least one attribute of the service other than state was changed. The change may or may not include changing the state.        
            cherrypy.thread_data.db.update(
                "trafficRules",
                query=query,
                newdata=object_to_mongodb_dict(trafficRule)
            )
        
        
        cherrypy.response.status = 200
        return trafficRule

