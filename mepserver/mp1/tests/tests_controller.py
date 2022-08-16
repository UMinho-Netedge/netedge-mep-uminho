import sys
import jsonschema


sys.path.append("../../")
from mp1.models import *

class TestsController:
    @cherrypy.tools.json_in()
    @json_out(cls=NestedEncoder)
    def mecAppStatus_update(self, appInstanceId: str):
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

        
        ## Do the terminationNotification task of change app status
        ## (to remove after terminationNotification is implemented)
        appInstanceDict = dict(appInstanceId=appInstanceId)
        appStatusDict = dict(
            {"indication" : appTerminationConfirmation.operationAction.name}
        )
        updateStatus = cherrypy.thread_data.db.update(
            "appStatus", 
            appInstanceDict, 
            appStatusDict
            )

        # AppStatus confirmation of indication change
        print(f"\n# AppStatus confirmation #\nAppStatus of appInstanceId {appInstanceId}:")
        pprint.pprint(cherrypy.thread_data.db.query_col("appStatus", dict(appInstanceId=appInstanceId), find_one=True,))
        print(f"updateStatus.modified_count {updateStatus.modified_count}")
        print(f"updateStatus.matched_count {updateStatus.matched_count}\n")
        
        return list()
