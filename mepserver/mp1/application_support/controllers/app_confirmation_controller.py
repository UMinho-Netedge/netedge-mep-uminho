import json
import sys

import cherrypy

sys.path.append("../../")
from mp1.models import *
from mp1.enums import IndicationType


class ApplicationConfirmationController:
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
    def application_confirm_termination(self, appInstanceId: str):
        """
        This method is used to confirm the application level termination of an application instance.
        :param appInstanceId: Represents a MEC application instance. Note that the appInstanceId is allocated by the MEC platform manager.
        :type appInstanceId: str

        HTTP STATUS CODE: 204, 401, 403, 404, 409, 429
        """
        # TODO notification to MEC app instance indicating it will be terminated
        # or stopped soon. In the notification 

        try:
            appTerminationConfirmation = AppTerminationConfirmation.from_json(
                cherrypy.request.json
            )

        except:
            print("Exception launched!")

        query_appStatus = dict(appInstanceId=appInstanceId)
        appStatus = cherrypy.thread_data.db.query_col(
            "appStatus",
            query_appStatus,
            find_one=True,
        )

        if appStatus:
            if len(appStatus['services']) > 0:
                serv_lst = []
                for serv in appStatus['services']:
                    serv_lst.append(serv['serInstanceId'])
                
                if len(serv_lst) > 0:
                    in_serv_lst = {}
                    in_serv_lst['$in'] = serv_lst
                    query_services = dict(serInstanceId=in_serv_lst)
                    print("\nQUERYYYY")
                    pprint.pprint(query_services)
                    # cherrypy.thread_data.db.remove("services", query_services)
                    cherrypy.thread_data.db.remove_many('services', query_services)
            cherrypy.thread_data.db.remove("appStatus", query_appStatus)
        
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