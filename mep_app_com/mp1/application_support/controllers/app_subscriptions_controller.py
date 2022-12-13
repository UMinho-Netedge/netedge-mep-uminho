# Copyright 2022 Centro ALGORITMI - University of Minho and Instituto de Telecomunicações - Aveiro
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
import uuid
import jsonschema
from bson.json_util import dumps, loads

sys.path.append("../../")
from mp1.models import *
from .app_callback_controller import CallbackController


class ApplicationSubscriptionsController:
    @json_out(cls=NestedEncoder)
    def applications_subscriptions_get(self, appInstanceId: str, **kwargs):
        """
        The GET method may be used to request information about all subscriptions for this requestor. Upon success, the response contains entity body with all the subscriptions for the requestor.

        :param appInstanceId: Represents a MEC application instance. Note that the appInstanceId is allocated by the MEC platform manager.
        :type appInstanceId: str

        :return: MecServiceMgmtApiSubscriptionLinkList or ProblemDetails
        HTTP STATUS CODE: 200, 400, 403, 404
        """
        # Obtain the subscriptionIds that match the appInstanceId
        # TODO validate the authorization to get the subscriptions of the appinstanceid (i.e if this person can query for this appinstanceid)

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

        result =  cherrypy.thread_data.db.query_col(
            "appSubscriptions", 
            query=query,
            fields=dict(subscriptionId=0)
        )

        
        cherrypy.response.status = 200
        return list(result)


    @cherrypy.tools.json_in()
    @json_out(cls=NestedEncoder)
    def applications_subscriptions_post(self, appInstanceId: str):
        """
        The GET method may be used to request information about all subscriptions for this requestor. Upon success, the response contains entity body with all the subscriptions for the requestor.

        :param appInstanceId: Represents a MEC application instance. Note that the appInstanceId is allocated by the MEC platform manager.
        :type appInstanceId: str

        :request body: Entity body in the request contains a subscription to the MEC application termination notifications that is to be created.

        :return: SerAvailabilityNotificationSubscription or ProblemDetails
        HTTP STATUS CODE: 201, 400, 403, 404
        """
        # Validating that appinstanceid exists
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
        # The process of generating the class allows for "automatic" validation of the json and
        # for filtering after saving to the database
        try:
            # Verify the requestion body if its correct about its schema:
            terminationNotificationSubscription = AppTerminationNotificationSubscription.from_json(data)

        except (TypeError, jsonschema.exceptions.ValidationError) as e:
            error = BadRequest(e)
            return error.message()

        # Verification of MEC App status:
        if appStatus['indication'] == IndicationType.READY.name:

            # Add subscriptionId required for the Subscriptions Method specified in Section 8.2.9.2
            # subscriptionID generation is inside the class
            subscriptionId = str(uuid.uuid4())
            # Verify if exists a previous links in requisition body:
            if terminationNotificationSubscription._links == None:
                # Add _links to class before sending
                server_self_referencing_uri = cherrypy.url(
                    qs=cherrypy.request.query_string, relative="server"
                )
                _links = Links(
                        _self=LinkType(f"{server_self_referencing_uri}/{subscriptionId}")
                )
                terminationNotificationSubscription._links = _links

            # Add appInstanceId for internal usage
            cherrypy.thread_data.db.create(
                "appSubscriptions",
                object_to_mongodb_dict(
                    terminationNotificationSubscription,
                    extra=dict(subscriptionId=subscriptionId, appInstanceId=appInstanceId), ),
            )

            cherrypy.response.headers["location"] = terminationNotificationSubscription._links.self.href
            cherrypy.response.status = 201
            return terminationNotificationSubscription.to_json()

        # If the AppStatus is not Ready:
        else:
            error_msg = "Application %s is in %s state. This operation not allowed in this state." % (
            appInstanceId, appStatus["indication"])
            error = Forbidden(error_msg)
            return error.message()

    @json_out(cls=NestedEncoder)
    def applications_subscriptions_get_with_subscription_id(
        self, appInstanceId: str, subscriptionId: str, **kwargs
    ):
        """
        The GET method requests information about a subscription for this requestor. Upon success, the response contains entity body with the subscription for the requestor.

        :param appInstanceId:  Represents a MEC application instance. Note that the appInstanceId is allocated by the MEC platform manager.
        :type appInstanceId: str
        :param subscriptionId: Represents a subscription to the notifications from the MEC platform.
        :type subscriptionId: str

        :return: SerAvailabilityNotificationSubscription or ProblemDetails
        HTTP STATUS CODE: 200, 400, 403, 404
        """
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

        query = {"subscriptionId": subscriptionId}

        result =  cherrypy.thread_data.db.query_col(
            "appSubscriptions", 
            query=query,
            fields=dict(subscriptionId=0),
            find_one=True
            )

        if result is None:
            error_msg = "Subscription %s was not found." % (subscriptionId)
            error = NotFound(error_msg)
            return error.message()

        cherrypy.response.status = 200
        return result

    @json_out(cls=NestedEncoder)
    def applications_subscriptions_delete(
        self, appInstanceId: str, subscriptionId: str
    ):
        """
        This method deletes a mecSrvMgmtSubscription. This method is typically used in "Unsubscribing from service availability event notifications" procedure.

        :param appInstanceId: Represents a MEC application instance. Note that the appInstanceId is allocated by the MEC platform manager.
        :type appInstanceId: str
        :param subscriptionId: Represents a subscription to the notifications from the MEC platform.
        :type subscriptionId: str

        :return: No Content or ProblemDetails
        HTTP STATUS CODE: 204, 403, 404
        """
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

        
        query = {"subscriptionId": subscriptionId}


        result =  cherrypy.thread_data.db.query_col(
            "appSubscriptions", 
            query=query,
            fields=dict(subscriptionId=0),
            find_one=True
            )

        if result is None:
            error_msg = "Subscription %s was not found." % (subscriptionId)
            error = NotFound(error_msg)
            return error.message()

        # remove the subscription of the collection
        cherrypy.thread_data.db.remove(col="appSubscriptions", query=dict(subscriptionId=subscriptionId))
        cherrypy.response.status = 204
        return None