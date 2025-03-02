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
import jsonschema
import cherrypy
import time
import datetime
sys.path.append("../../")
from mp1.models import *
from mp1.enums import IndicationType
from mp1.application_support.controllers.app_callback_controller import *
from ratelimit import limits, RateLimitException, sleep_and_retry
from threading import Lock
from json.decoder import JSONDecodeError
from functools import wraps

ATTEMPT_LIM = 1  # maximum no. of attempts in TIME_RESET seconds 
TIME_RESET = 5  # in seconds
RATE_LIM = ATTEMPT_LIM/TIME_RESET

class ApplicationConfirmationController:
    
    lock = Lock()
    attemps_dict = dict()

    @classmethod
    def add_app_if_not_exists(cls, appInstanceId: str):
        # acquire the lock and release automatically
        with cls.lock:
            if appInstanceId not in ApplicationConfirmationController.attemps_dict.keys():
                    ApplicationConfirmationController.attemps_dict[appInstanceId] = [1, time.time()]
                    print(f"\nadd_app_if_not_exists: {ApplicationConfirmationController.attemps_dict[appInstanceId]}")
                    return 1
            print(f"\nadd_app_if_not_exists: already exists!")
            return 0

    @classmethod
    def add_attempt(cls, appInstanceId: str, error_msg: str):
        with cls.lock:
            att_dict = ApplicationConfirmationController.attemps_dict
            # increments attempt and returns the respective pair
            att_dict[appInstanceId][0] += 1
            
            # rate = (no. of app attempts) / (seconds passed since first attempt)
            time_diff = time.time() - att_dict[appInstanceId][1]
            rate = att_dict[appInstanceId][0] / time_diff
            print(f"time_diff = {time.time()} - {att_dict[appInstanceId][1]} = {time_diff}")
            print(f"rate = {rate} | RATE_LIM = {RATE_LIM}")
            if time_diff >= TIME_RESET:
                # reset app attempts
                att_dict[appInstanceId] = [1, time.time()]
            elif rate >= RATE_LIM:
                #print(f"rate >= RATE_LIM {rate >= RATE_LIM}")
                error = TooManyRequests(error_msg)
                return error.message()
            
            return None

    @classmethod
    def increment_attempt(cls, appInstanceId: str):
        # acquire the lock and release automatically
        with cls.lock:
            ApplicationConfirmationController.attemps_dict[appInstanceId][0] += 1
            print(f"\nincrement_attempt: ApplicationConfirmationController.attemps_dict[appInstanceId]\n{ApplicationConfirmationController.attemps_dict[appInstanceId]}\n")
            return ApplicationConfirmationController.attemps_dict[appInstanceId]

    @classmethod
    def delete_app_attempts(cls, appInstanceId: str):
        with cls.lock:
            del ApplicationConfirmationController.attemps_dict[appInstanceId]

    @classmethod
    def delete_if_exists(cls, appInstanceId: str):
        with cls.lock:
            if appInstanceId in ApplicationConfirmationController.attemps_dict.keys():
                del ApplicationConfirmationController.attemps_dict[appInstanceId]
    

    def exception_handler(func):
        def inner_function(*args, **kwargs):
            try:
                f = func(*args, **kwargs)
                return f
            except RateLimitException:
                error_msg = "Too many requests have been sent. Try again soon."
                error = TooManyRequests(error_msg)
                return error.message()
        return inner_function


    def validate_token(func):
        @wraps(func)
        def check_token(*args, **kwargs):
            cherrypy.log('Received request. Validating token.')
            # Validate client credentials
            try:
                auth_header = cherrypy.request.headers['Authorization']
            except KeyError:
                error_msg = "No access token provided."
                error = Unauthorized(error_msg)
                return error.message()

            if auth_header is None:
                error_msg = "No access token provided."
                error = Unauthorized(error_msg)
                return error.message()
            
            oauth = cherrypy.config.get("oauth_server")
            access_token = auth_header.split(' ')[1]
            cherrypy.log('Access token: ' + access_token)
            if oauth.validate_token(access_token) is False:
                error_msg = "Invalid access token."
                error = Unauthorized(error_msg)
                return error.message()

            return func(*args, **kwargs)
        
        return check_token

    @cherrypy.tools.json_in()
    @json_out(cls=NestedEncoder)
    @exception_handler
    @limits(calls=ATTEMPT_LIM, period=TIME_RESET)
    @validate_token
    def application_confirm_ready(self, appInstanceId: str, **kwargs):
        """
        This method may be used by the MEC application instance to notify the MEC platform that it is up and running.
        :param appInstanceId: Represents a MEC application instance. Note that the appInstanceId is allocated by the MEC platform manager.
        :type appInstanceId: str

        HTTP STATUS CODE: 204, 401, 403, 404, 409, 429
        """
        appStatus = cherrypy.thread_data.db.query_col(
            "appStatus",
            query=dict(appInstanceId=appInstanceId),
            find_one=True,
        )

        # If app does not exist in db
        if appStatus is None:
            error_msg = "Application %s does not exist." % (appInstanceId)
            error = NotFound(error_msg)
            return error.message()

        # Create AppReadyConfirmation from json to validate the input
        try:
            appConfirmReady = AppReadyConfirmation.from_json(cherrypy.request.json)
        except (TypeError, jsonschema.exceptions.ValidationError) as e:
            error = BadRequest(e)
            return error.message()  

        # Before attempting to insert data into the collection check if the app hasn't already registered itself
        if appStatus['indication'] == IndicationType.READY.name:
            #error_msg = "Application %s is in %s state. This operation not allowed in this state." % (
            #appInstanceId, appStatus["indication"])
            #error = Forbidden(error_msg)
            cherrypy.response.status = 204
            #return error.message()
            return None

        else:
            appInstanceDict = dict(appInstanceId=appInstanceId)
            appStatusDict = dict({"indication": IndicationType.READY.name})
            cherrypy.thread_data.db.update("appStatus", appInstanceDict, appStatusDict)
            appInstanceDict = dict(appInstanceId=appInstanceId, operation="STARTING")
            lcmOperationStatusDict = dict({"operationStatus": OperationStatus.SUCCESSFULLY_DONE.name})
            cherrypy.thread_data.db.update("lcmOperations", appInstanceDict, lcmOperationStatusDict)
            cherrypy.response.status = 204
            return None

    @cherrypy.tools.json_in()
    @json_out(cls=NestedEncoder)
    @validate_token
    def application_confirm_termination(self, appInstanceId: str, **kwargs):
        """
        This method is used to confirm the application level termination of an application instance.
        :param appInstanceId: Represents a MEC application instance. Note that the appInstanceId is allocated by the MEC platform manager.
        :type appInstanceId: str

        HTTP STATUS CODE: 204, 401, 403, 404, 409, 429

        Section 7.2.11.3.4
        """
        
        try:
            appTerminationConfirmation = AppTerminationConfirmation.from_json(
                cherrypy.request.json
            )
        except (jsonschema.exceptions.ValidationError, json.decoder.JSONDecodeError, TypeError):
            error_msg = "Request body must have only the 'operationAction' "   \
                        "attribute which can only have one of two possible "   \
                        "values: TERMINATING or STOPPING."
            error = BadRequest(error_msg)
            return error.message()


        query_appStatus = dict(appInstanceId=appInstanceId)
        appStatus = cherrypy.thread_data.db.query_col(
            "appStatus",
            query_appStatus,
            find_one=True,
        )

        # At this point the app appInstanceId was already notified with 
        # terminationNotification by MEP which:
        # * change the app status ("indication") on database
        # * notifies subscripted apps
        # * notifies the producer app of status modification

        # The service producing App should deregister its produced services
        # before the time expires.

        if appStatus is None:
            error_msg = "The application instance resource is not instantiated."
            error = Conflict(error_msg)
            return error.message()

        # At this point, in appStatus collection, "indication" has already 
        # been changed to "TERMINATING" or "STOPPING". This attribute must match
        # that sent in AppTerminationConfirmation, raising an error otherwise.
        operationAction = str(appTerminationConfirmation.operationAction)

        if appStatus['indication'] != operationAction:
            # First attempt #
            # if true: add new element in class dict. 
            # otherwise: do nothing and passes to else
            if ApplicationConfirmationController.add_app_if_not_exists(appInstanceId):
                pass

            # Next attempts #
            # Add 1 more attempt to correspondent dict pair and tests for 
            # attempt rate limit
            else:
                # return TooManyRequests error with gived msg if RATE_LIM is excedeed
                error_msg = f"Too many requests have been sent. Try again soon."
                error = ApplicationConfirmationController.add_attempt(appInstanceId, error_msg)
                if error is not None:
                    return error

            error_msg = f"There is no {operationAction.lower()} operation ongoing."
            error = Conflict(error_msg)
            return error.message()

        # if appStatus['indication'] == operationAction
        # First attempt
        if ApplicationConfirmationController.add_app_if_not_exists(appInstanceId):
                pass

        # Next attempts
        else:
            # return TooManyRequests error with gived msg if RATE_LIM is excedeed
            error_msg = f"{operationAction.lower()} is already being handled."
            error = ApplicationConfirmationController.add_attempt(appInstanceId, error_msg)
            if error is not None:
                    return error
        '''
        # Note:
            All TODO tasks might be already in course if time interval definied
            in termination notification has expired
        '''

        oauth = cherrypy.config.get("oauth_server")

        oauth.delete_client(appStatus['oauth']['client_id'], appStatus['oauth']['client_secret'])

        query = {"appInstanceId": appInstanceId}
        
        result = cherrypy.thread_data.db.query_col(
            "trafficRules", 
            query=query,
            fields=dict(appInstanceId=0)
        )

        for rule in result:

            CallbackController.execute_callback(
                args=[appInstanceId, rule],
                func=CallbackController._removeTrafficRule,
                sleep_time=0
            )
            
            cherrypy.thread_data.db.remove(col= "trafficRules",
            query=dict(trafficRuleId=rule['trafficRuleId']))
            

        query = dict(appInstanceId=appInstanceId, state="ACTIVE")

        result = cherrypy.thread_data.db.query_col("dnsRules", query)

        for rule in result:
            CallbackController.execute_callback(
                args=[appInstanceId, rule],
                func=CallbackController._removeDnsRule,
                sleep_time=0
            )
            
            cherrypy.thread_data.db.remove(col= "dnsRules",
            query=dict(dnsRuleId=rule['dnsRuleId']))           


        appInstanceDict = dict(appInstanceId=appInstanceId)
        cherrypy.thread_data.db.remove("appStatus", appInstanceDict)


        lastModified = cherrypy.response.headers['Date']
            
        query = dict(
                appInstanceId=appInstanceId, 
                operation=OperationActionType.TERMINATING.name,
        )

        lcmOperationStatusDict = dict({"stateEnteredTime": lastModified, "operationStatus": OperationStatus.SUCCESSFULLY_DONE.name})
        cherrypy.thread_data.db.update(
            "lcmOperations", 
            query, 
            lcmOperationStatusDict
        )

        # TODO sending service availability notification to the MEC apps
        # that consumes the services produced by the terminating/stopping
        # MEC app instance (if app didn't started service deregistration yet)
        
        time.sleep(1)  # to test TooManyRequests error

        # TODO distinguish "TERMINATING" behaviour from "STOPPING".
        # (?) TERMINATING: remove app and its services from appStatus and services collection (respectively)
        # (?) STOPPING: keep app and services but change services "state" to INACTIVE or SUSPENDED
        if (operationAction == "TERMINATING") or (operationAction == "STOPPING"):
            if len(appStatus['services']) > 0:
                # list app services
                serv_lst = []
                for serv in appStatus['services']:
                    serv_lst.append(serv['serInstanceId'])
                

                # TODO remove the MEC app instance from the list of instances
                # to be notified about service availability (subscriptions)
                # if not done yet


                # app services removal from services collection
                if serv_lst:
                    in_serv_lst = dict()
                    in_serv_lst['$in'] = serv_lst
                    query_services = dict(serInstanceId=in_serv_lst)
                    cherrypy.thread_data.db.remove_many('services', query_services)

            # app removal from appStatus collection
            cherrypy.thread_data.db.remove("appStatus", query_appStatus)

        

        # remove appInstanceId from class dictionary
        ApplicationConfirmationController.delete_app_attempts(appInstanceId)

        cherrypy.response.status = 204
        return None

        '''
        if appTerminationConfirmation.operationAction in [
            OperationActionType.TERMINATING,
            OperationActionType.STOPPING,
        ]:
            appInstanceDict = dict(appInstanceId=appInstanceId)
            # Create a dict to be saved th
            appStatusDict = dict(
                {"indication" : appTerminationConfirmation.operationAction.name}
            )

            # TODO CURRENTLY ONLY CHANGING APPSTATUS
            # THIS SHOULD BE PERFORMED IN THE FIRST AppTerminationNotification POST to the callbackReference
            # DOING IT HERE TO HELP TESTING APPSTATUS CHECKS
            # THIS SHOULD BE ERASED IN THE FUTURE, CHECK SECTION 7.2.11.3.4
            updateStatus = cherrypy.thread_data.db.update("appStatus", appInstanceDict ,appStatusDict)
            if updateStatus.modified_count == 1:
                cherrypy.response.status = 204
                return None

            # TODO REMOVE THE REST OF THE DATA AND CREATE CALLBACK
            # NOTIFY EVERY SUBSCRIBER

            # result = cherrypy.thread_data.db.remove(
            #     "appStatus", dict(appInstanceId=appInstanceId)
            # )
            # # If our remove query failed it returns 0
            # if result.deleted_count == 0:
            #     # TODO RETURN PROBLEM DETAILS
            #     pass
            # Set header to 204 - No Content

        '''