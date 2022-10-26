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

import cherrypy

sys.path.append("../../")
from mp1.models import *
import uuid
from .callbacks_controller import CallbackController
import jsonschema
from deepdiff import DeepDiff

class ApplicationServicesController:
    @json_out(cls=NestedEncoder)
    def applications_services_get(
        self,
        appInstanceId: str,
        ser_instance_id: List[str] = None,
        ser_name: List[str] = None,
        ser_category_id: str = None,
        scope_of_locality: str = None,
        consumed_local_only: bool = None,
        is_local: bool = None,
        **kwargs,
    ):
        """
        This method retrieves information about a list of mecService resources. This method is typically used in "service availability query" procedure
        Required params
        :param appInstanceId: Represents a MEC application instance. Note that the appInstanceId is allocated by the MEC platform manager.
        :type appInstanceId: String
        Query Params
        :param ser_instance_id: A MEC application instance may use multiple ser_instance_ids as an input parameter to query the availability of a list of MEC service instances. Either "ser_instance_id" or "ser_name" or "ser_category_id" or none of them shall be present.
        :type ser_instance_id: List[String]
        :param ser_name: A MEC application instance may use multiple ser_names as an input parameter to query the availability of a list of MEC service instances. Either "ser_instance_id" or "ser_name" or "ser_category_id" or none of them shall be present.
        :type ser_name: List[String]
        :param ser_category_id: A MEC application instance may use ser_category_id as an input parameter to query the availability of a list of MEC service instances in a serCategory. Either "ser_instance_id" or "ser_name" or "ser_category_id" or none of them shall be present.
        :type ser_category_id: String
        :param consumed_local_only: Indicate whether the service can only be consumed by the MEC applications located in the same locality (as defined by scopeOfLocality) as this service instance.
        :type consumed_local_only: boolean
        :param is_local: Indicate whether the service is located in the same locality (as defined by scopeOfLocality) as the consuming MEC application.
        :type is_local: boolean
        :param scope_of_locality: A MEC application instance may use scope_of_locality as an input parameter to query the availability of a list of MEC service instances with a certain scope of locality.
        :type scope_of_locality: String
        :note: ser_name, ser_category_id, ser_instance_id are mutually-exclusive only one should be used
        :return: ProblemDetails or ServiceInfo
        HTTP STATUS CODE: 200, 400, 403, 404, 414
        """
        if kwargs != {}:
            error_msg = "Invalid attribute(s): %s" % (str(kwargs))
            error = BadRequest(error_msg)
            return error.message()

        appReg = cherrypy.thread_data.db.query_col(
                "appStatus",
                query=dict(appInstanceId=appInstanceId),
                find_one=True,)

        # if app doesn't exist in db
        if appReg is None:
            error_msg = "Invalid 'appInstanceId'. Value not found."
            error = BadRequest(error_msg)
            return error.message()
        # if app exists but is not READY
        elif appReg["indication"] != IndicationType.READY.name:
            error_msg = "App %s isn't in READY state." % (appInstanceId)
            error = Forbidden(error_msg)
            return error.message()
        # if app exists, is ready, but with no services
        elif len(appReg['services']) == 0:
            return list()
        
        # App has services
        inst_ids_lst = []
        for service in appReg['services']:
            inst_ids_lst.append(service['serInstanceId'])
        
        try:
            query = ServiceGet(
                        ser_instance_id=ser_instance_id,
                        ser_name=ser_name,
                        ser_category_id=ser_category_id,
                        scope_of_locality=scope_of_locality,
                        consumed_local_only=consumed_local_only,
                        is_local=is_local)
            
            query = query.to_query()

            if ser_instance_id != None:
                try:
                    inst_ids_arg_lst = ser_instance_id.split(",")
                    for instance_id in inst_ids_arg_lst:
                        uuid.UUID(str(instance_id))
                    
                except ValueError:
                    error_msg = f"'ser_instance_id' attempted with invalid format with the value {instance_id}." \
                                " Value is required in UUID format."
                    error = BadRequest(error_msg)
                    return error.message()

                instance_ids_lst = list(set(inst_ids_arg_lst) & set(inst_ids_lst))
                query['serInstanceId'] = instance_ids_lst
            else:
                query['serInstanceId'] = inst_ids_lst
            
            result = cherrypy.thread_data.db.query_col("services", query)

        except jsonschema.exceptions.ValidationError as e:
            if "is not of type" in str(e.message):
                error_msg = "Invalid type in '"                                 \
                            + str(camel_to_snake(e.json_path.replace("$.",""))) \
                            + "' attribute: "+str(e.message)
            else:
                error_msg = "Either 'ser_instance_id' or 'ser_name' or "        \
                        "'ser_category_id' or none of them shall be present."
            error = BadRequest(error_msg)
            return error.message()

        return list(result)


    @cherrypy.tools.json_in()
    @json_out(cls=NestedEncoder)
    def applications_services_post(self, appInstanceId: str):
        """
        This method is used to create a mecService resource. This method is typically used in "service availability update and new service registration" procedure
        :param appInstanceId: Represents a MEC application instance. Note that the appInstanceId is allocated by the MEC platform manager.
        :type appInstanceId: String
        :return: ServiceInfo or ProblemDetails
        HTTP STATUS CODE: 201, 400, 403, 404
        """
        # TODO ADD RATE LIMITING OTHERWISE APP CAN CONTINOUSLY GENERATE NEW SERVICES
        # TODO NEEDS TO BE RATE LIMIT SINCE AN APP CAN HAVE N SERVICES
        data = cherrypy.request.json
        # The process of generating the class allows for "automatic" validation of the json
        try:
            serviceInfo = ServiceInfo.from_json(data)

            # checks if there is a service info in the request, if it does not have it, create one
            # Add serInstanceId (uuid) to serviceInfo according to Section 8.1.2.2
            # serInstaceId is used as serviceId appServices
            if serviceInfo.serInstanceId is None:
                serviceInfo.serInstanceId = str(uuid.uuid4())

            # Add _links data to serviceInfo
            server_self_referencing_uri = cherrypy.url(
                qs=cherrypy.request.query_string, relative="server"
            )
            _links = Links(
                liveness=LinkType(
                    f"/mec_service_mgmt/v1/liveness/{appInstanceId}/{serviceInfo.serInstanceId}"
                )
            )
            serviceInfo._links = _links
            notify_changeType = None

            if serviceInfo.livenessInterval is None:
                serviceInfo.livenessInterval = 0

            # TODO serCategory IF NOT PRESENT NEEDS TO BE SET BY MEP (SOMEHOW TELL ME ETSI)
            # Should receive it from MEPM

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

        # if app exists and is READY
        if appStatus['indication'] == IndicationType.READY.name:

            # Checks if service already exists or if it is a new one
            hasService = False
            for appService in appStatus["services"]:
                if appService["serName"] == serviceInfo.serName:
                    hasService = True
                    appService["state"] = serviceInfo.state.name

                    break

            # If it already exists updates service state
            if hasService:
                service = cherrypy.thread_data.db.query_col(
                    "services",
                    query=dict(serInstanceId=appService["serInstanceId"]),
                    find_one=True,
                )

                serviceInfo.serInstanceId = appService["serInstanceId"]

                diff = DeepDiff(service, object_to_mongodb_dict(serviceInfo), ignore_order=True)

                # If something changed in the service, must update db
                if (len(diff) > 0):

                    # At least one attribute of the service other than state was changed. The change may or may not include changing the state.
                    notify_changeType = ChangeType.ATTRIBUTES_CHANGED

                    # Only the state of the service was changed.
                    if len(diff) == 1 and 'values_changed' in diff and "root['state']" in diff[
                        'values_changed'] and len(diff['values_changed']) == 1:
                        notify_changeType = ChangeType.STATE_CHANGED

                    # Checks new service state and updates
                    cherrypy.thread_data.db.update(
                        "services",
                        query=dict(serName=serviceInfo.serName),
                        newdata=object_to_mongodb_dict(serviceInfo)
                    )

                    cherrypy.thread_data.db.update(
                        "appStatus",
                        query=dict(appInstanceId=appInstanceId),
                        newdata=dict(services=appStatus["services"])
                    )

                    cherrypy.log(
                        "Application %s service %s updated:\n %s."
                        % (appInstanceId, appService["serInstanceId"], diff)
                    )

            # If it is new, creates
            else:
                # The service was newly added.
                notify_changeType = ChangeType.ADDED

                appStatus["services"].append({"serName": serviceInfo.serName,
                                              "serInstanceId": serviceInfo.serInstanceId,
                                              "state": serviceInfo.state.name,
                                              "liveness": {
                                                    "interval": serviceInfo.livenessInterval,
                                                    "update": 0
                                              }, 
                                              "timeStamp": {
                                                    "seconds": 0,
                                                    "nanoseconds": 0
                                                }
                                              })

                # updates appStatus with new service
                cherrypy.thread_data.db.update(
                    "appStatus",
                    query=dict(appInstanceId=appInstanceId),
                    newdata=dict(services=appStatus["services"])
                )

                # Store new service into the database
                cherrypy.thread_data.db.create(
                    "services", object_to_mongodb_dict(serviceInfo)
                )

                cherrypy.log(
                    "Application %s created a new service:\n %s."
                    % (appInstanceId, json.dumps(object_to_mongodb_dict(serviceInfo)))
                )

            # TODO TEST ALL THIS SUBSCRIPTION AND NOTIFICATION PART WHEN SERVICE AND APP ARE AVAILABLE
            if notify_changeType is not None:
                # Obtain all the Subscriptions that match the newly added/updated service
                # Generate query that allows for all possible criteria using the $and and $or mongo operators
                query = serviceInfo.to_filtering_criteria_json()
                # cherrypy.log(json.dumps(query, cls=NestedEncoder))
                subscriptions = cherrypy.thread_data.db.query_col("subscriptions", query)
                subscriptions = list(subscriptions)
                # Before creating the object transform the serviceInfo into a json list since it is
                # expecting a list of services in json
                # We don't use the original data because it is missing parameters that are introduced internally
                serviceInfoData = [json.loads(json.dumps(serviceInfo, cls=NestedEncoder))]

                # TODO CHANGETYPE ADDED, STATE_CHANGED, ATRIBUTES_CHANGED
                serviceNotification = (
                    ServiceAvailabilityNotification.from_json_service_list(
                        data=serviceInfoData, changeType=notify_changeType.name
                    )
                )
                # If some subscriptions matches with the newly added service we need to notify them of this change
                if len(subscriptions) > 0:
                    availability_notifications = []
                    # Transform each subscription into a ServiceNotificationSubscription class for easier usage
                    for subscription in list(subscriptions):
                        appInstanceId = subscription.pop("appInstanceId")
                        subscriptionId = subscription.pop("subscriptionId")
                        # Remove subscriptionType from subscription due to the fact that SerAvailabilityNotificationSubscription
                        # Is created usually from user input and we don't want him to control that parameter
                        subscription.pop("subscriptionType")
                        availability_notification = (
                            SerAvailabilityNotificationSubscription.from_json(subscription)
                        )
                        availability_notification.appInstanceId = appInstanceId
                        availability_notification.subscriptionId = subscriptionId
                        availability_notifications.append(availability_notification)
                    # Call the callback with the list of SerAvailabilityNotificationSubscriptions
                    # Use a sleep_time of 0 (the subscriber is already up and waiting for subscriptions)
                    CallbackController.execute_callback(
                        availability_notifications=availability_notifications,
                        data=serviceNotification,
                        sleep_time=0,
                    )

            cherrypy.response.headers["location"] = serviceInfo.serCategory.href
            cherrypy.response.status = 201
            return serviceInfo

        # If app existis and is not READY
        else:
            error_msg = "Application %s is in %s state. This operation not allowed in this state." % (
            appInstanceId, appStatus["indication"])
            error = Forbidden(error_msg)
            return error.message()

    @json_out(cls=NestedEncoder)
    def applicaton_services_get_with_service_id(
        self, 
        appInstanceId: str, 
        serviceId: str,
        **kwargs
    ):
        """
        This method retrieves information about a mecService resource. This method is typically used in "service availability query" procedure
        :param appInstanceId: Represents a MEC application instance. Note that the appInstanceId is allocated by the MEC platform manager.
        :type appInstanceId: String
        :param serviceId: Represents a MEC service instance.
        :type serviceId: String
        :return: ServiceInfo or ProblemDetails
        HTTP STATUS CODE: 200, 400, 403, 404
        """
        if kwargs != {}:
            error_msg = "Invalid attribute(s): %s" % (str(kwargs))
            error = BadRequest(error_msg)
            return error.message()

        appReg = cherrypy.thread_data.db.query_col(
                "appStatus",
                query=dict(appInstanceId=appInstanceId),
                find_one=True,)

        # if app doesn't exist in db
        if appReg is None:
            error_msg = "Invalid 'appInstanceId'. Value not found."
            error = BadRequest(error_msg)
            return error.message()
        # if app exists but is not READY
        elif appReg["indication"] != IndicationType.READY.name:
            error_msg = "App %s state isn't READY." % (appInstanceId)
            error = Forbidden(error_msg)
            return error.message()
        
        try:
            uuid.UUID(str(serviceId))
        except ValueError:
            error_msg = "Attempted 'serviceId' with invalid format." \
                        " Value is required in UUID format."
            error = BadRequest(error_msg)
            return error.message() 

        inst_ids_lst = []
        for service in appReg['services']:
            inst_ids_lst.append(service['serInstanceId'])
        
        if serviceId in inst_ids_lst:
            query = dict(serInstanceId=str(serviceId),)
            data = cherrypy.thread_data.db.query_col("services", query)
            return list(data)
        else:
            return list()
        

    @cherrypy.tools.json_in()
    @json_out(cls=NestedEncoder)
    def application_services_put(self, appInstanceId: str, serviceId: str):
        """
                This method updates the information about a mecService resource
                :param appInstanceId: Represents a MEC application instance. Note that the appInstanceId is allocated by the MEC platform manager.
                :type appInstanceId: String
                :param serviceId: Represents a MEC service instance.
                :type serviceId: String
        2
                :request body: New ServiceInfo with updated "state" is included as entity body of the request
                :return: ServiceInfo or ProblemDetails
                HTTP STATUS CODE: 200, 400, 403, 404, 412
        """
        # TODO PUT ONLY NEEDS TO RECEIVE ONE UPDATABLE CRITERIA
        data = cherrypy.request.json

        # The process of generating the class allows for "automatic" validation of the json
        try:
            flag_links = False
            flag_id = False

            for key in data.keys():
                if key == '_links':
                    flag_links = True

                if key == 'serInstanceId':
                    flag_id = True

            if(flag_links):
                data.pop('_links')

            if(flag_id):
                data.pop('serInstanceId')


            serviceInfo = ServiceInfo.from_json(data)
            # Add _links data to serviceInfo
            server_self_referencing_uri = cherrypy.url(
                qs=cherrypy.request.query_string, relative="server"
            )
            _links = Links(
                liveness=LinkType(
                    f"{server_self_referencing_uri}/liveness"
                )
            )
            serviceInfo._links = _links
            notify_changeType = None
            # TODO serCategory IF NOT PRESENT NEEDS TO BE SET BY MEP (SOMEHOW TELL ME ETSI)

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

        # if app exists and is READY
        if appStatus['indication'] == IndicationType.READY.name:

            # Checks if service already exists or if it is a new one
            hasService = False
            for appService in appStatus["services"]:
                if appService["serInstanceId"] == serviceId:
                    hasService = True
                    appService["state"] = serviceInfo.state.name
                    break

            # If it already exists updates service state
            if hasService:
                service = cherrypy.thread_data.db.query_col(
                    "services",
                    query=dict(serInstanceId=serviceId),
                    find_one=True,
                )

                serviceInfo.serInstanceId = appService["serInstanceId"]

                diff = DeepDiff(service, object_to_mongodb_dict(serviceInfo), ignore_order=True)

                # If something changed in the service, must update db
                if (len(diff) > 0):

                    # At least one attribute of the service other than state was changed. The change may or may not include changing the state.
                    notify_changeType = ChangeType.ATTRIBUTES_CHANGED

                    # Only the state of the service was changed.
                    if len(diff) == 1 and 'values_changed' in diff and "root['state']" in diff[
                        'values_changed'] and len(diff['values_changed']) == 1:
                        notify_changeType = ChangeType.STATE_CHANGED

                    # Checks new service state and updates
                    cherrypy.thread_data.db.update(
                        "services",
                        query=dict(serName=serviceInfo.serName),
                        newdata=object_to_mongodb_dict(serviceInfo)
                    )

                    cherrypy.thread_data.db.update(
                        "appStatus",
                        query=dict(appInstanceId=appInstanceId),
                        newdata=dict(services=appStatus["services"])
                    )

                    cherrypy.log(
                        "Application %s service %s updated:\n %s."
                        % (appInstanceId, appService["serInstanceId"], diff)
                    )

            # If it is new, creates
            else:
                error_msg = "Service %s does not exist." % (
                            serviceId)
                error = NotFound(error_msg)
                return error.message()

            # TODO TEST ALL THIS SUBSCRIPTION AND NOTIFICATION PART WHEN SERVICE AND APP ARE AVAILABLE
            if notify_changeType is not None:
                # Obtain all the Subscriptions that match the newly added/updated service
                # Generate query that allows for all possible criteria using the $and and $or mongo operators
                query = serviceInfo.to_filtering_criteria_json()
                # cherrypy.log(json.dumps(query, cls=NestedEncoder))
                subscriptions = cherrypy.thread_data.db.query_col("subscriptions", query)
                subscriptions = list(subscriptions)
                # Before creating the object transform the serviceInfo into a json list since it is
                # expecting a list of services in json
                # We don't use the original data because it is missing parameters that are introduced internally
                serviceInfoData = [json.loads(json.dumps(serviceInfo, cls=NestedEncoder))]

                # TODO CHANGETYPE ADDED, STATE_CHANGED, ATRIBUTES_CHANGED
                serviceNotification = (
                    ServiceAvailabilityNotification.from_json_service_list(
                        data=serviceInfoData, changeType=notify_changeType.name
                    )
                )
                # If some subscriptions matches with the newly added service we need to notify them of this change
                if len(subscriptions) > 0:
                    availability_notifications = []
                    # Transform each subscription into a ServiceNotificationSubscription class for easier usage
                    for subscription in list(subscriptions):
                        appInstanceId = subscription.pop("appInstanceId")
                        subscriptionId = subscription.pop("subscriptionId")
                        # Remove subscriptionType from subscription due to the fact that SerAvailabilityNotificationSubscription
                        # Is created usually from user input and we don't want him to control that parameter
                        subscription.pop("subscriptionType")
                        availability_notification = (
                            SerAvailabilityNotificationSubscription.from_json(subscription)
                        )
                        availability_notification.appInstanceId = appInstanceId
                        availability_notification.subscriptionId = subscriptionId
                        availability_notifications.append(availability_notification)
                    # Call the callback with the list of SerAvailabilityNotificationSubscriptions
                    # Use a sleep_time of 0 (the subscriber is already up and waiting for subscriptions)
                    CallbackController.execute_callback(
                        availability_notifications=availability_notifications,
                        data=serviceNotification,
                        sleep_time=0,
                    )

            cherrypy.response.headers["location"] = serviceInfo.serCategory.href
            cherrypy.response.status = 200
            return serviceInfo

        # If app existis and is not READY
        else:
            error_msg = "Application %s is in %s state. This operation not allowed in this state." % (
            appInstanceId, appStatus["indication"])
            error = Forbidden(error_msg)
            return error.message()


    @json_out(cls=NestedEncoder)
    def application_services_delete(self, appInstanceId: str, serviceId: str):
        """
        This method deletes a mecService resource. This method is typically used in the service deregistration procedure.

        :param appInstanceId: Represents a MEC application instance. Note that the appInstanceId is allocated by the MEC platform manager.
        :type appInstanceId: String
        :param serviceId: Represents a MEC service instance.
        :type serviceId: String


        :return: No Content or ProblemDetails
        HTTP STATUS CODE: 204, 403, 404,
        """

        appStatus = cherrypy.thread_data.db.query_col(
            "appStatus",
            query=dict(appInstanceId=appInstanceId),
            find_one=True,
        )

        #verify if appInstanceId is in db
        if appStatus is None:
            error_msg = "Application %s was not found." % (appInstanceId)
            error = NotFound(error_msg)
            return error.message()
        #

        # if app exists and is READY
        if appStatus['indication'] == IndicationType.READY.name:

            # Checks if service already exists
            hasService = False
            position = 0
            for appService in appStatus["services"]:
                if appService["serInstanceId"] == serviceId:
                    hasService = True
                    break
                position+=1

            # if the services exist - remove the SerId of the collection services and remove from the list of appStatus["service"]
            if hasService:
                #remove the service of service collection
                cherrypy.thread_data.db.remove(col= "services",   query=dict(serInstanceId=appService["serInstanceId"]))

                #remove the service info from the services list in appStatus collection
                appStatus["services"].pop(position)
                cherrypy.thread_data.db.update(
                    "appStatus",
                    query=dict(appInstanceId=appInstanceId),
                    newdata=appStatus
                )
                cherrypy.response.status = 204
                return None



            # If the services does not exist - report 404 error code
            else:
                error_msg = "Service %s was not found." % (serviceId)
                error = NotFound(error_msg)
                return error.message()

        #
        # If app existis and is not READY
        else:
            error_msg = "Application %s is in %s state. This operation not allowed in this state." % (
            appInstanceId, appStatus["indication"])
            error = Forbidden(error_msg)
            return error.message()

    ##