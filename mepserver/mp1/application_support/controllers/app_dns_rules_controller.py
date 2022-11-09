import sys
import cherrypy
import json
import jsonschema
import requests

sys.path.append("../../")
from mp1.models import *
from deepdiff import DeepDiff
from hashlib import md5





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
        app_status = cherrypy.thread_data.db.query_col("appStatus", 
                                                    query, 
                                                    find_one=True)
        # If App exists
        if app_status:
            # App READY
            if app_status['indication'] == IndicationType.READY.name:
                query = query | {"dnsRuleId": dnsRuleId}
                result = cherrypy.thread_data.db.query_col("dnsRules", 
                                                            query,
                                                            find_one=True)
                # If Rule exists
                if result:
                    # dnsRuleId ACTIVE 
                    if result['state'] == StateType.ACTIVE.name:
                        last_modified = result['lastModified']

                        del result['lastModified'], result['appInstanceId']

                        # Generate hash
                        rule = json.dumps(result)
                        new_etag = md5(rule.encode('utf-8')).hexdigest()
                        print(f"\nGET new_etag: {new_etag}")

                        # Add headers
                        cherrypy.response.headers['ETag'] = new_etag
                        cherrypy.response.headers['Last-Modified'] = last_modified

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
        prev_dns_rule = cherrypy.thread_data.db.query_col(
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
        
        elif prev_dns_rule is None:
            error_msg = "DNS rule %s was not found." % (dnsRuleId)
            error = NotFound(error_msg)
            return error.message()

        else:
            ##
            prev_state = prev_dns_rule["state"]
            new_state = new_rec["state"]

            if prev_state != new_state:
                dict_dns = cherrypy.config.get("dns")

                if new_state == "ACTIVE":
                    print("Activating DNS rule...")

                    domain = prev_dns_rule["domainName"]
                    ip = prev_dns_rule["ipAddress"]
                    ttl = prev_dns_rule["ttl"]

                    # Create dns rule via api
                    headers = {"Content-Type": "application/json"}
                    query = {"name": domain, "ip": ip, "ttl": ttl}
                    
                    url_0 = 'http://%s:%s/dns_support/v1/api/%s/record' %(dict_dns['dnsHost'], dict_dns['dnsPort'], dict_dns['dnsZone'])
                    response = requests.post(
                                url_0,
                                headers=headers,
                                params=query
                                )
                    print(response.json())


                elif new_state == "INACTIVE":
                    print("Deactivating DNS rule...")
                    
                    domain = prev_dns_rule["domainName"]

                    # Delete dns rule via api
                    headers = {"Content-Type": "application/json"}
                    url = 'http://%s:%s/dns_support/v1/api/%s/record?name=%s' %(dict_dns['dnsHost'], dict_dns['dnsPort'], dict_dns['dnsZone'], domain)
                    response = requests.delete(
                                url,
                                headers=headers,
                                )
                    print(response.json())


            ##

            last_modified = prev_dns_rule['lastModified']
            print(f"\nPOST last_modified {last_modified}")
            del prev_dns_rule['appInstanceId'], prev_dns_rule['lastModified']

            dns_rule_dict = object_to_mongodb_dict(prev_dns_rule)

            # ETag of previous document
            prev_rule = json.dumps(dns_rule_dict)
            prev_etag = md5(prev_rule.encode('utf-8')).hexdigest()
            print(f"\nPOST prev_etag {prev_etag}")
            
            try:
                cherrypy.response.headers['ETag'] = prev_etag
                cherrypy.lib.cptools.validate_etags()
            except cherrypy.HTTPError as e:
                error_msg = "ETag mismatch. Please try again." + str(e)
                error = Precondition(error_msg)
                return error.message()

            try:
                cherrypy.response.headers['Last-Modified'] = last_modified
                cherrypy.lib.cptools.validate_since()
            except cherrypy.HTTPError as e:
                error_msg = "Mismatch on last modification date. Please try again." + str(e)
                error = Precondition(error_msg)
                return error.message()

            if ("dnsRuleId" in new_rec):
                del new_rec["dnsRuleId"]

            new_date = cherrypy.response.headers['Date']
            cherrypy.thread_data.db.update("dnsRules",
                                            query=dns_rule_query,
                                            newdata=new_rec|{"lastModified": new_date})
            
            diff = DeepDiff(new_rec, dns_rule_dict, ignore_order=True)
            cherrypy.log("Dns Rule %s from app %s updated:\n%s"
                        %(dnsRuleId, appInstanceId, diff))

            cherrypy.response.status = 200
            dns_rule_dict.update(new_rec)

            cherrypy.response.body = dns_rule_dict

            cherrypy.response.headers['Last-Modified'] = cherrypy.response.headers['Date']

            new_rule = json.dumps(dns_rule_dict)
            new_etag = md5(new_rule.encode('utf-8')).hexdigest()
            print(f"\nPOST new_etag: {new_etag}")
            cherrypy.response.headers['ETag'] = new_etag
            
            
            return dns_rule_dict

        # TODO: 412 Precondition Failed

       
