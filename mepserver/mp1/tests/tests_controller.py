import sys
import jsonschema
import requests

sys.path.append("../../")
from mp1.models import *
from hashlib import md5

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

        # Generate hash
        rule = json.dumps(new_rec)
        new_etag = md5(rule.encode('utf-8')).hexdigest()
        print(f"\nPOST new_etag: {new_etag}")

        # Add headers
        cherrypy.response.headers['ETag'] = new_etag
        lastModified = cherrypy.response.headers['Date']
        cherrypy.response.headers['Last-Modified'] = lastModified


        query = dict(appInstanceId=appInstanceId, dnsRuleId=dnsRuleId)

        # to assure correct document override
        if cherrypy.thread_data.db.count_documents("dnsRules", query) > 0:
            cherrypy.thread_data.db.remove("dnsRules", query)

        ##########  CORE DNS  ##########
        # Create dns rule via coredns api
        if new_rec["state"] == "ACTIVE":
            domain = new_rec["domainName"]
            ip = new_rec["ipAddress"]
            ttl = new_rec["ttl"]

            headers = {"Content-Type": "application/json"}
            query = {"name": domain, "ip": ip, "ttl": ttl}

            dict_dns = cherrypy.config.get("dns")
            url_0 = 'http://%s:%s/dns_support/v1/api/%s/record' % (dict_dns["dnsHost"], dict_dns["dnsPort"], dict_dns["dnsZone"])
            response = requests.post(
                        url_0,
                        headers=headers,
                        params=query
                        )
            print(f"\n# DNS rule creation #\nresponse: {response.json()}\n")

        ##############################

        new_rec = {
            "appInstanceId": appInstanceId, 
            "lastModified": lastModified,
            } | new_rec
        cherrypy.thread_data.db.create("dnsRules", new_rec)
   
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

