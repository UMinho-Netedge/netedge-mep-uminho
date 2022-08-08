import json
import sys
import jsonschema
import cherrypy
import time

sys.path.append("../../")
from mp1.models import *
from mp1.enums import IndicationType
from threading import Lock


ATTEMPT_RATE_LIM = 0.5


class ApplicationConfirmationController:
    
    lock = Lock()
    attemps_dict = dict()

    @classmethod
    def add_app_if_not_exists(cls, appInstanceId: str):
        # acquire the lock and release automatically
        with cls.lock:
            if appInstanceId not in ApplicationConfirmationController.attemps_dict.keys():
                    ApplicationConfirmationController.attemps_dict[appInstanceId] = [1, time.time()]
                    print(f"\nadd_app_if_not_exists: \n{ApplicationConfirmationController.attemps_dict[appInstanceId]}")
                    return 1
            print(f"\nadd_app_if_not_exists: already exists")
            return 0

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
    

    @cherrypy.tools.json_in()
    def application_confirm_ready(self, appInstanceId: str):
        """
        This method may be used by the MEC application instance to notify the MEC platform that it is up and running.
        :param appInstanceId: Represents a MEC application instance. Note that the appInstanceId is allocated by the MEC platform manager.
        :type appInstanceId: str

        HTTP STATUS CODE: 204, 401, 403, 404, 409, 429
        """
        # TODO confirm the provided appInstanceId with the mongodb
        # TODO PROPER PROBLEM DETAILS
        # Create AppReadyConfirmation from json to validate the input
        appConfirmReady = AppReadyConfirmation.from_json(cherrypy.request.json)
        cherrypy.log(appConfirmReady.indication.name)
        if appConfirmReady.indication == IndicationType.READY:
            # Before attempting to insert data into the collection check if the app hasn't already registered itself
            if (
                cherrypy.thread_data.db.count_documents(
                    "appStatus", dict(appInstanceId=appInstanceId)
                )
                > 0
            ):
                # TODO CAN'T STORE BECAUSE APPINSTANCE ID ALREADY EXISTS
                return

            # Create a dict to be saved in the database
            appStatusDict = dict(
                appInstanceId=appInstanceId, **appConfirmReady.to_json()
            )

            appStatusDict = appStatusDict | {"services":[]}
            # Indication is still and object and not the value
            # We could use the json_out internal function but it is overkill for this instance
            appStatusDict["indication"] = appStatusDict["indication"].name
            cherrypy.thread_data.db.create("appStatus", appStatusDict)
            # Set header to 204 - No Content
            cherrypy.response.status = 204
            return None

    @cherrypy.tools.json_in()
    @json_out(cls=NestedEncoder)
    def application_confirm_termination(self, appInstanceId: str):
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
        except jsonschema.exceptions.ValidationError:
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

        
        if appStatus:
            # MEC Platform has already notified MEC App that it will be 
            # terminated or stopped soon (AppTerminationNotification). 
            # At that point, in appStatus collection, app's indication attribute
            # is changed to "TERMINATING" or "STOPPING". This attribute must match
            # that sent in AppTerminationConfirmation raising an error otherwise.
            operationAction = str(appTerminationConfirmation.operationAction)

            ######################################
            ## Fake/induced appStatus indication. 
            ## Just for test while AppTerminationNotification doesn't change status
            #appStatus['indication'] = "TERMINATING"
            #appStatus['indication'] = "STOPPING"

            #'''
            ## Do the terminationNotification task of change app status
            ## (to remove after terminationNotification is implemented)
            appInstanceDict = dict(appInstanceId=appInstanceId)
            appStatusDict = dict(
                {"indication" : appTerminationConfirmation.operationAction.name}
            )
            cherrypy.thread_data.db.update(
                "appStatus", 
                appInstanceDict, 
                appStatusDict
                )

            # AppStatus confirmation of indication change
            print(f"\n# AppStatus confirmation #\nAppStatus of appInstanceId {appInstanceId}:")
            pprint.pprint(cherrypy.thread_data.db.query_col("appStatus", dict(appInstanceId=appInstanceId), find_one=True,))

            #'''
            ######################################

            # [Case 1] AppTerminationNotification didn't change app status yet
            # (e.g. app time for stop/termination didn't expire yet)
            if appStatus['indication'] != operationAction:
                # First attempt #
                # Create new dict element with appInstanceId as key and a pair 
                # with no. of attempts in 1st position and time of first attempt
                # in 2nd position
                '''
                if str(appInstanceId) not in ApplicationConfirmationController.attemps_dict.keys():
                    ApplicationConfirmationController.attemps_dict[str(appInstanceId)] = (1, time.time())
                '''
                # if true: add new element in class dict. 
                # otherwise: do nothing and passes to else
                if ApplicationConfirmationController.add_app_if_not_exists(appInstanceId):
                    pass

                # Next attempts #
                # Add 1 more attempt to correspondent dict pair and tests for 
                # attempt rate limit
                else:
                    '''
                    ApplicationConfirmationController.attemps_dict[str(appInstanceId)].first += 1
                    app_attmpt_info = ApplicationConfirmationController.attemps_dict[str(appInstanceId)]

                    '''
                    # increments attempt and returns the respective pair
                    app_attmpt_info = ApplicationConfirmationController.increment_attempt(appInstanceId)
                    
                    # (no. of attempts to this app) / (seconds passed since first attempt)
                    rate = app_attmpt_info[0] / (time.time() - app_attmpt_info[1])
                    if rate >= ATTEMPT_RATE_LIM:
                        error_msg = f"Too many requests have been sent. Try again soon."
                        error = TooManyRequests(error_msg)
                        return error.message()

                error_msg = f"There is no {operationAction.lower()} operation ongoing."
                error = Conflict(error_msg)
                return error.message()

            """
            if app_exists:
                del ApplicationConfirmationController.attemps_dict[str(appInstanceId)]
            """
            # terminationNotification already changed the app status
            # If there were previous attempts, without appStatus matching, we 
            # have to del app in attemps_dict so it doesn't get false 
            # TooManyRequests error
            ApplicationConfirmationController.delete_if_exists(appInstanceId)

            # [Case 2] AppTerminationNotification changed app status already
            # First attempt
            '''
            if str(appInstanceId) not in ApplicationConfirmationController.attemps_dict.keys():
                ApplicationConfirmationController.attemps_dict[str(appInstanceId)] = (1, time.time())
            '''
            if ApplicationConfirmationController.add_app_if_not_exists(appInstanceId):
                    pass
            # Next attempts
            else:
                error_msg = f"{operationAction.lower()} is already being handled."
                error = TooManyRequests(error_msg)
                return error.message()
            
            '''
            # Note:
                All TODO tasks might be already in course if time interval definied
                in termination notification has expired
            '''

            # TODO deactivate traffic rules

            # TODO deactivate dns rules

            # TODO sending service availability notification to the MEC apps
            # that consumes the services produced by the terminating/stopping
            # MEC app instance


            if operationAction == "TERMINATING":
                if len(appStatus['services']) > 0:
                    # list app services
                    serv_lst = []
                    for serv in appStatus['services']:
                        serv_lst.append(serv['serInstanceId'])
                    

                    # TODO remove the MEC app instance from the list of instances
                    # to be notified about service availability (subscriptions)


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
            #del ApplicationConfirmationController.attemps_dict[str(appInstanceId)]

        else:
            error_msg = "The application instance resource is not instantiated."
            error = Conflict(error_msg)
            return error.message()

        cherrypy.response.status = 204


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