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


    @cherrypy.tools.json_in()
    @json_out(cls=NestedEncoder)
    def dns_rule_post(self, appInstanceId: str, dnsRuleId: str):
        data = cherrypy.request.json

        try:
            dnsRule = DnsRule.from_json(data)
        except (TypeError, jsonschema.exceptions.ValidationError) as e:
            error = BadRequest(e)
            return error.message()

        new_rec = dnsRule.to_json()
        if new_rec["dnsRuleId"] != dnsRuleId:
            error_msg = "dnsRuleId in request body must match the one in URI."
            error = BadRequest(error_msg)
            return error.message()

        print(f"tests_controller new_rec:\n{new_rec}")
        query = dict(appInstanceId=appInstanceId, dnsRuleId=dnsRuleId)

        # to assure correct document override
        if cherrypy.thread_data.db.count_documents("dnsRules", query) > 0:
            cherrypy.thread_data.db.remove("dnsRules", query)

        new_rec = {"appInstanceId": appInstanceId} | new_rec
        cherrypy.thread_data.db.create("dnsRules", new_rec)

        '''
        if (cherrypy.thread_data.db.count_documents("dnsRules", query) == 0):
                new_rec = {"appInstanceId": appInstanceId} | new_rec
                cherrypy.thread_data.db.create("dnsRules", new_rec)
        else:
            error_msg = f"Dns rule {dnsRuleId} of app {appInstanceId} already exists."
            error = BadRequest(error_msg)
            return error.message()
        '''
        cherrypy.response.status = 200
        return dnsRule

    @json_out(cls=NestedEncoder)
    def remove_db_collections(self):
        app = cherrypy.thread_data.db.remove_many("appStatus", {})
        serv = cherrypy.thread_data.db.remove_many("services", {})
        dns = cherrypy.thread_data.db.remove_many("dnsRules", {})

        return {"appStatus": app.deleted_count,
                "services": serv.deleted_count,
                "dnsRules": dns.deleted_count}

