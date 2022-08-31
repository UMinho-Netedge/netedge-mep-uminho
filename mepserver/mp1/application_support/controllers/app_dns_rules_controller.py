import sys
import cherrypy
import json
import jsonschema

sys.path.append("../../")
from mp1.models import *
from deepdiff import DeepDiff


class AppDnsRulesController:

    @json_out(cls=NestedEncoder)
    def dns_rules_get(
        self, 
        appInstanceId: str, 
        **kwargs):
        
        if kwargs != {}:
            error_msg = "Invalid attribute(s): %s" % (str(kwargs))
            error = BadRequest(error_msg)
            return error.message()

        query = dict(appInstanceId=appInstanceId)
        result = cherrypy.thread_data.db.query_col("appStatus", 
                                                    query, 
                                                    find_one=True)
        if result:  # app exists
            print(f"result length: {len(result)} # result: {result}")
            if result['indication'] != IndicationType.READY.name:
                error_msg = "App %s state isn't READY." % (appInstanceId)
                error = Forbidden(error_msg)
                return error.message()
        else:
            error_msg = "Application %s was not found." % (appInstanceId)
            error = NotFound(error_msg)
            return error.message()

        query = query | {"state": "ACTIVE"}
        result = cherrypy.thread_data.db.query_col("dnsRules", query)
        
        cherrypy.response.status = 200
        return list(result)


    @json_out(cls=NestedEncoder)
    def dns_rule_get_with_dns_rule_id(
        self, 
        appInstanceId: str, 
        dnsRuleId: str,
        **kwargs
        ):
        if kwargs != {}:
            error_msg = "Invalid attribute(s): %s" % (str(kwargs))
            error = BadRequest(error_msg)
            return error.message()

        query = dict(appInstanceId=appInstanceId)
        result = cherrypy.thread_data.db.query_col("appStatus", 
                                                    query, 
                                                    find_one=True)
        # If App exists
        if result:
            # App READY
            if result['indication'] == IndicationType.READY.name:
                query = query | {"dnsRuleId": dnsRuleId}
                result = cherrypy.thread_data.db.query_col("dnsRules", 
                                                            query,
                                                            find_one=True)
                # If Rule exists
                if result:
                    # dnsRuleId ACTIVE 
                    if result['state'] == StateType.ACTIVE.name:
                        cherrypy.response.status = 200
                        return result
                    else:
                        error_msg = "DNS rule %s state is not ACTIVE." % (dnsRuleId)
                        error = Forbidden(error_msg)
                        return error.message()
                else:
                    error_msg = "DNS rule %s was not found." % (dnsRuleId)
                    error = NotFound(error_msg)
                    return error.message()

            else:
                error_msg = "Application %s state isn't READY." % (appInstanceId)
                error = Forbidden(error_msg)
                return error.message()

        else:
            error_msg = "Application %s was not found." % (appInstanceId)
            error = NotFound(error_msg)
            return error.message()


    @cherrypy.tools.json_in()
    @json_out(cls=NestedEncoder)
    def dns_rules_put(self, appInstanceId: str, dnsRuleId: str):
        
        data = cherrypy.request.json

        try:
            dnsRule = DnsRule.from_json(data, schema=dns_rule_put_schema)
        except (TypeError, jsonschema.exceptions.ValidationError) as e:
            error = BadRequest(e)
            return error.message()

        new_rec = dnsRule.to_json()
        if ("dnsRuleId" in new_rec) and (new_rec["dnsRuleId"]!= dnsRuleId):
            error_msg = "dnsRuleId in request body must match the one in URI."
            error = BadRequest(error_msg)
            return error.message()

        appStatus = cherrypy.thread_data.db.query_col(
            "appStatus",
            query=dict(appInstanceId=appInstanceId),
            find_one=True,)
        
        dns_rule_query = dict(appInstanceId=appInstanceId, dnsRuleId=dnsRuleId)
        dnsRules = cherrypy.thread_data.db.query_col(
            "dnsRules",
            query=dns_rule_query,
            find_one=True,)
        
        if appStatus is None:
            error_msg = "Application %s was not found." % (appInstanceId)
            error = NotFound(error_msg)
            return error.message()

        elif appStatus["indication"] != IndicationType.READY.name:
            error_msg = "App %s isn't in READY state." % (appInstanceId)
            error = Forbidden(error_msg)
            return error.message()
        
        elif dnsRules is None:
            error_msg = "DNS rule %s was not found." % (dnsRuleId)
            error = NotFound(error_msg)
            return error.message()

        else:
            del dnsRules['appInstanceId']
            dns_rule_dict = object_to_mongodb_dict(dnsRules)

            if ("dnsRuleId" in new_rec):
                del new_rec["dnsRuleId"]

            cherrypy.thread_data.db.update("dnsRules",
                                            query=dns_rule_query,
                                            newdata=new_rec)
            
            diff = DeepDiff(new_rec, dns_rule_dict, ignore_order=True)
            cherrypy.log("Dns Rule %s from app %s updated:\n%s"
                        %(dnsRuleId, appInstanceId, diff))

            cherrypy.response.status = 200
            dns_rule_dict.update(new_rec)
    
            return dns_rule_dict

        # TODO: 412 Precondition Failed

       
