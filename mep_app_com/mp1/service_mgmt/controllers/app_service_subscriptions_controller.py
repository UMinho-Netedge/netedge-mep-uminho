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
from .services_callbacks_controller import CallbackController


class ApplicationServicesSubscriptionsController:
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

        # Verification of kwargs existance:
        if kwargs != {}:
            error_msg = "Invalid attribute(s): %s" % (str(kwargs))
            error = BadRequest(error_msg)
            return error.message()

        # Verify if AppInstanceId is instantiated in db:
        appStatus = cherrypy.thread_data.db.query_col(
            "appStatus",
            query=dict(appInstanceId=appInstanceId),
            find_one=True, )

        # Error generating if AppInstanceId does not exist in db:
        if appStatus is None:
            error_msg = "Invalid 'appInstanceId'. Value not found."
            error = BadRequest(error_msg)
            return error.message()

        # Verification of MEC App status:
        if appStatus['indication'] == IndicationType.READY.name:

            # Catch all subscriptions in the collection
            subscriptionIds = cherrypy.thread_data.db.query_col(
                "subscriptions",
                query=dict(appInstanceId=appInstanceId),
                fields=dict(subscriptionId=1),
            )

            # Generate dict and then validate via the already existing models
            # Takes all subscriptions created by appInstanceId and generates a list of subscriptions
            subscriptionlinklist = {
                "_links": {
                    "self": {
                        "href": cherrypy.url(
                            qs=cherrypy.request.query_string, relative="server"
                        )
                    },
                    "subscriptions": [],
                }
            }

            # Iterate the cursor and add to the linklist
            for subId in subscriptionIds:
                serverSelfReferencingUri = cherrypy.url(
                    qs=cherrypy.request.query_string, relative="server"
                )
                href = {"href": f"{serverSelfReferencingUri}/{subId['subscriptionId']}"}
                subscriptionlinklist["_links"]["subscriptions"].append(href)

            return MecServiceMgmtApiSubscriptionLinkList.from_json(subscriptionlinklist)

        else:
            error_msg = "Application %s is in %s state. This operation not allowed in this state." % (
            appInstanceId, appStatus["indication"])
            error = Forbidden(error_msg)
            return error.message()


    @cherrypy.tools.json_in()
    @json_out(cls=NestedEncoder)
    def applications_subscriptions_post(self, appInstanceId: str, **kwargs):
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

        # Validate token
        # TODO: When OAuth gets updated one should request, when it's a new 
        # service, a request body with correspondent parameters to check if this
        # app have permission to subscript notifications
        try:
            access_token = kwargs["access_token"]
        except KeyError:
            error_msg = "No access token provided."
            error = Unauthorized(error_msg)
            return error.message()

        if access_token is None:
            error_msg = "No access token provided."
            error = Unauthorized(error_msg)
            return error.message()
        
        oauth = cherrypy.config.get("oauth_server")
        if oauth.validate_token(access_token) is False:
            error_msg = "Invalid access token."
            error = Unauthorized(error_msg)
            return error.message()

        # Obtain the request body
        data = cherrypy.request.json

        # The process of generating the class allows for "automatic" validation of the json and
        # for filtering after saving to the database
        try:
            if("subscriptionType" in data.keys()):
                data.pop("subscriptionType")

            # Verify the requestion body if its correct about its schema:
            availability_notification = SerAvailabilityNotificationSubscription.from_json(data)

        except (TypeError, jsonschema.exceptions.ValidationError) as e:
            error = BadRequest(e)
            return error.message()

        # Verification of MEC App status:
        if appStatus['indication'] == IndicationType.READY.name:

            # Add subscriptionId required for the Subscriptions Method specified in Section 8.2.9.2
            # subscriptionID generation is inside the class
            subscriptionId = str(uuid.uuid4())

            # Add appInstanceId for internal usage
            cherrypy.thread_data.db.create(
                "subscriptions",
                object_to_mongodb_dict(
                    availability_notification,
                    extra=dict(appInstanceId=appInstanceId, subscriptionId=subscriptionId), ),
            )

            # After generating the subscription we need to, according to the users filtering criteria,
            # get the services that match the filtering criteria.
            # Afterwards, execute a callback in order for the client to know which services are up and running

            # verification of filtering criteria:
            if availability_notification.filteringCriteria:

                # Obtain the notification filtering criteria
                query = availability_notification.filteringCriteria.to_query()
                # Query the database for services that are already registered and that match the filtering criteria
                data = cherrypy.thread_data.db.query_col("services", query)
                # Transform cursor into a list
                data = list(data)
                # From the existing services that match the subscription criteria generate the notifications
                # According to Section 8.1.4.2-1 of MEC 011 _links contains hyperlinks to the related subscription
                if len(data) > 0:
                    subscription = (
                        f"/applications/{appInstanceId}/subscriptions/{subscriptionId}"
                    )
                    serviceNotification = (
                        ServiceAvailabilityNotification.from_json_service_list(
                            data=data, subscription=subscription, changeType="ADDED"
                        )
                    )
                    # Execute the callback with the data to be sent
                    # default sleep_time is 10 due to the fact that the subscriber hasn't receive his request response
                    # stating that he will receive subscription notifications
                    CallbackController.execute_callback(
                        availability_notifications=availability_notification,
                        data=serviceNotification,
                    )


            # Verify if exists a previous links in requisition body:
            if availability_notification._links == None:
                # Return the data that was sent via the post message with added _links that references to current subscriptionId
                server_self_referencing_uri = cherrypy.url(
                    qs=cherrypy.request.query_string, relative="server"
                )

                _links = Links(
                    _self=LinkType(f"{server_self_referencing_uri}/{subscriptionId}")
                )
                availability_notification._links = _links


            cherrypy.response.status = 201
            return availability_notification

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
        # Obtain the subscriptionIds that match the appInstanceId and subscriptionId
        # TODO validate the authorization to get the subscriptions of the appinstanceid (i.e if this person can query for this appinstanceid)
        # Only one result is expected so use find_one to limit the database search and decrease response time

        # Verification of kwargs existance:
        if kwargs != {}:
            error_msg = "Invalid attribute(s): %s" % (str(kwargs))
            error = BadRequest(error_msg)
            return error.message()

        # Verify if AppInstanceId is instantiated in db:
        appStatus = cherrypy.thread_data.db.query_col(
            "appStatus",
            query=dict(appInstanceId=appInstanceId),
            find_one=True, )

        # Error generating if AppInstanceId does not exist in db:
        if appStatus is None:
            error_msg = "Invalid 'appInstanceId'. Value not found."
            error = BadRequest(error_msg)
            return error.message()


        # Verification of MEC App status:
        if appStatus['indication'] == IndicationType.READY.name:

            # Verification if SubscriptionId exists in db:
            subscription = cherrypy.thread_data.db.query_col(
                "subscriptions",
                query=dict(appInstanceId=appInstanceId, subscriptionId=subscriptionId),
                fields=dict(subscriptionId=0),
                find_one=True,
            )

            if(subscription == None):
                error_msg = "Subscription %s was not found." % (subscriptionId)
                error = NotFound(error_msg)
                return error.message()

            else:
                # In the database we also save the appInstanceId but it isn't supposed to be returned or used to create the object
                subscription.pop("appInstanceId")
                subscription.pop("subscriptionType")

                availability_notification = SerAvailabilityNotificationSubscription.from_json(
                    subscription
                )

                # Verify if exists a previous links in requisition body:
                if availability_notification._links == None:

                    # Add _links to class before sending
                    server_self_referencing_uri = cherrypy.url(
                        qs=cherrypy.request.query_string, relative="server"
                    )
                    _links = Links(
                        _self=LinkType(f"{server_self_referencing_uri}/{subscriptionId}")
                    )
                    availability_notification._links = _links

                return availability_notification

        else:
            error_msg = "Application %s is in %s state. This operation not allowed in this state." % (
            appInstanceId, appStatus["indication"])
            error = Forbidden(error_msg)
            return error.message()



    @json_out(cls=NestedEncoder)
    def applications_subscriptions_delete(
        self, appInstanceId: str, subscriptionId: str, **kwargs
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
        # Validate token
        try:
            access_token = kwargs["access_token"]
        except KeyError:
            error_msg = "No access token provided."
            error = Unauthorized(error_msg)
            return error.message()
            
        if access_token is None:
            error_msg = "No access token provided."
            error = Unauthorized(error_msg)
            return error.message()
        
        oauth = cherrypy.config.get("oauth_server")
        if oauth.validate_token(access_token) is False:
            error_msg = "Invalid access token."
            error = Unauthorized(error_msg)
            return error.message()

        appStatus = cherrypy.thread_data.db.query_col(
            "appStatus",
            query=dict(appInstanceId=appInstanceId),
            find_one=True,
        )

        # Verify if appInstanceId is in db
        if appStatus is None:
            error_msg = "Application %s was not found." % (appInstanceId)
            error = NotFound(error_msg)
            return error.message()
        #

        # if app exists and is READY
        if appStatus['indication'] == IndicationType.READY.name:

            # Checks if service already exists
            subscription = cherrypy.thread_data.db.query_col(
                "subscriptions",
                query=dict(appInstanceId=appInstanceId, subscriptionId=subscriptionId),
                fields=dict(subscriptionId=0),
                find_one=True,
            )

            # if the services exist - remove the SerId of the collection subscriptions:
            if subscription != None:
                # remove the subscription of the collection
                cherrypy.thread_data.db.remove(col="subscriptions", query=dict(subscriptionId=subscriptionId))
                cherrypy.response.status = 204
                return None

            # If the services does not exist - report 404 error code
            else:
                error_msg = "Subscription %s was not found." % (subscriptionId)
                error = NotFound(error_msg)
                return error.message()

        #
        # If app existis and is not READY
        else:
            error_msg = "Application %s is in %s state. This operation not allowed in this state." % (
                appInstanceId, appStatus["indication"])
            error = Forbidden(error_msg)
            return error.message()

