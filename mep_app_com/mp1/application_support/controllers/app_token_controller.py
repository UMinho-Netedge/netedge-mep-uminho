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
from time import sleep
import cherrypy

sys.path.append("../../")
from mp1.models import *
import jsonschema
from kubernetes import client, config

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
            # THIS PART SHOULD BE REMOVED AS SOON AS AN MEPM IS PROVIDED
            # config.load_incluster_config()
            # k8s_client = client.CoreV1Api()
            # pod_spec = k8s_client.list_pod_for_all_namespaces(label_selector='pod-template-hash=%s' %appInstanceId).items
            # if not pod_spec:
            error_msg = "Application was not provided by OSM. Unauthorized access."
            error = Unauthorized(error_msg)
            return error.message()

            # mepconfig_url, mepconfig_port = cherrypy.config.get('mepconfig')
            # response = requests.post('http://%s:%s/mec_platform_mgmt/v1/app_instances/%s/configure_platform_for_app' %(mepconfig_url, mepconfig_port, appInstanceId), json={})
            # cherrypy.log(response.text)
            # sleep(5)

        appStatus = cherrypy.thread_data.db.query_col(
            "appStatus",
            query=dict(appInstanceId=appInstanceId),
            find_one=True,
        )

        credentials = appStatus["oauth"]
        
        return credentials