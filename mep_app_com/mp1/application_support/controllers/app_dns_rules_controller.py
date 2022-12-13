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
        """
        This method retrieves information about all the DNS rules associated with 
        a MEC application instance, which follows the resource data type of 
        "DnsRule" as specified in clause 7.1.2.3.
        
        :param appInstanceId: Identifier of the MEC application instance.
        :type appInstanceId: str
        :rtype: DnsRule

        HTTP Success Responses:
            200: OK
        :return: A list of DNS rules associated with the MEC application instance.
        :rtype: List[DnsRule]

        HTTP Error Responses:
            400: Bad Request
            404: Not Found
            403: Forbidden
        :return: Error message
        :rtype: ProblemDetails
        """
        
        # Check if there is any paramater that is not expected
        if kwargs != {}:
            error_msg = "Invalid attribute(s): %s" % (str(kwargs))
            error = BadRequest(error_msg)
            return error.message()

        # Check if the appInstanceId exists in "appStatus" collection (mongodb)
        query = dict(appInstanceId=appInstanceId)
        result = cherrypy.thread_data.db.query_col("appStatus", 
                                                    query, 
                                                    find_one=True)
        if result:
            # Check if the app is READY. If not, return 403 Forbidden
            if result['indication'] != IndicationType.READY.name:
                error_msg = "App %s state isn't READY." % (appInstanceId)
                error = Forbidden(error_msg)
                return error.message()
        else:
            # If the appInstanceId doesn't exist, return 404 Not Found
            error_msg = "Application %s was not found." % (appInstanceId)
            error = NotFound(error_msg)
            return error.message()

        # The app is READY. So, we can get the "ACTIVE" DNS rules associated 
        # with the appInstanceId and return them
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
        """
        This method retrieves information about a DNS rule associated with a MEC
        application instance.

        :param appInstanceId: Identifier of the MEC application instance.
        :type appInstanceId: str
        :param dnsRuleId: Identifier of the DNS rule.
        :type dnsRuleId: str

        HTTP Success Responses:
            200: OK
        :return: The DNS rule with the given Id associated with the MEC application instance Id also given.
        :rtype: DnsRule

        HTTP Error Responses:
            400: Bad Request
            404: Not Found
            403: Forbidden
        :return: Error message
        :rtype: ProblemDetails
        """

        # Check if there is any paramater that is not expected
        if kwargs != {}:
            error_msg = "Invalid attribute(s): %s" % (str(kwargs))
            error = BadRequest(error_msg)
            return error.message()

        # Check if the appInstanceId exists in "appStatus" collection (mongodb)
        query = dict(appInstanceId=appInstanceId)
        app_status = cherrypy.thread_data.db.query_col("appStatus", 
                                                    query, 
                                                    find_one=True)
        if app_status:
            # Check if the app is READY. If not, return 403 Forbidden
            if app_status['indication'] == IndicationType.READY.name:
                # Check if exists the DNS rule with the given dnsRuleId and 
                # appInstanceId in "dnsRules" collection (mongodb)
                query = query | {"dnsRuleId": dnsRuleId}
                result = cherrypy.thread_data.db.query_col("dnsRules", 
                                                            query,
                                                            find_one=True)
                if result:
                    # Check if the DNS rule is ACTIVE. If not, return 403 Forbidden
                    if result['state'] == StateType.ACTIVE.name:
                        last_modified = result['lastModified']
                        
                        # Generate ETag from the DNS rule
                        del result['lastModified'], result['appInstanceId']
                        rule = json.dumps(result)
                        new_etag = md5(rule.encode('utf-8')).hexdigest()

                        # Add headers to response with the ETag and Last-Modified 
                        # values of the DNS rule
                        cherrypy.response.headers['ETag'] = new_etag
                        cherrypy.response.headers['Last-Modified'] = last_modified

                        cherrypy.response.status = 200
                        return result
                    else:
                        # If the DNS rule is not ACTIVE, return 403 Forbidden
                        error_msg = "DNS rule %s state is not ACTIVE." % (dnsRuleId)
                        error = Forbidden(error_msg)
                        return error.message()
                else:
                    # If the DNS rule doesn't exist, return 404 Not Found
                    error_msg = "DNS rule %s was not found." % (dnsRuleId)
                    error = NotFound(error_msg)
                    return error.message()

            else:
                # If the app is not READY, return 403 Forbidden
                error_msg = "Application %s state isn't READY." % (appInstanceId)
                error = Forbidden(error_msg)
                return error.message()

        else:
            # If the appInstanceId doesn't exist, return 404 Not Found
            error_msg = "Application %s was not found." % (appInstanceId)
            error = NotFound(error_msg)
            return error.message()


    @cherrypy.tools.json_in()
    @json_out(cls=NestedEncoder)
    def dns_rules_put(self, appInstanceId: str, dnsRuleId: str):
        """
        This method activates, de-activates or updates a DNS rule.

        :param appInstanceId: Identifier of the MEC application instance.
        :type appInstanceId: str
        :param dnsRuleId: Identifier of the DNS rule.
        :type dnsRuleId: str

        HTTP Success Responses:
            200: OK
        :return: The DNS rule updated.
        :rtype: DnsRule

        HTTP Error Responses:
            400: Bad Request
            404: Not Found
            403: Forbidden
            412: Precondition Failed
        :return: Error message
        :rtype: ProblemDetails
        """
        
        # Get the request body
        data = cherrypy.request.json

        # Validate the request body with the DnsRule schema
        try:
            dnsRule = DnsRule.from_json(data, schema=dns_rule_put_schema)
        except (TypeError, jsonschema.exceptions.ValidationError) as e:
            error = BadRequest(e)
            return error.message()

        # Check if dnsRuleId in URI is the same as the one in the request body
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
            # If appInstanceId doesn't exist in "appStatus" collection, returns 404 Not Found
            error_msg = "Application %s was not found." % (appInstanceId)
            error = NotFound(error_msg)
            return error.message()

        elif appStatus["indication"] != IndicationType.READY.name:
            # If app is not READY, returns 403 Forbidden
            error_msg = "App %s isn't in READY state." % (appInstanceId)
            error = Forbidden(error_msg)
            return error.message()
        
        elif prev_dns_rule is None:
            # If dnsRuleId doesn't exist in "dnsRules" collection, returns 404 Not Found
            error_msg = "DNS rule %s was not found." % (dnsRuleId)
            error = NotFound(error_msg)
            return error.message()

        else:
            # App is READY and dnsRuleId exists in "dnsRules" collection
            
            prev_state = prev_dns_rule["state"]
            new_state = new_rec["state"]

            if prev_state != new_state:
                # If there is a change in the state of the DNS rule, check if it is valid

                #dict_dns = cherrypy.config.get("dns")
                dnsApiServer = cherrypy.config.get("dns_api_server")

                # If the DNS rule state changed from INACTIVE to ACTIVE
                if new_state == "ACTIVE":
                    domain = prev_dns_rule["domainName"]
                    ip = prev_dns_rule["ipAddress"]
                    ttl = prev_dns_rule["ttl"]

                    # Create DNS rule in the DNS server (via API)
                    dnsApiServer.create_record(domain, ip, ttl)
                    cherrypy.log("Activated DNS rule %s, associated with app %s, in DNS server: %s" % (dnsRuleId, appInstanceId, domain))

                # If the DNS rule state changed from ACTIVE to INACTIVE
                elif new_state == "INACTIVE":
                    print("Deactivating DNS rule...")
                    
                    domain = prev_dns_rule["domainName"]

                    # Delete DNS rule in the DNS server (via API)
                    dnsApiServer.delete_record(domain)
                    cherrypy.log("Deactivated DNS rule %s, associated with app %s, in DNS server: %s" % (dnsRuleId, appInstanceId, domain))

            # Check if conditional requests (ETag and Last-Modified) are satisfied
            # avoiding write conflicts
            last_modified = prev_dns_rule['lastModified']
            del prev_dns_rule['appInstanceId'], prev_dns_rule['lastModified']

            dns_rule_dict = object_to_mongodb_dict(prev_dns_rule)

            # ETag of previous rule
            prev_rule = json.dumps(dns_rule_dict)
            prev_etag = md5(prev_rule.encode('utf-8')).hexdigest()
            
            # Validate ETag conditional request
            try:
                cherrypy.response.headers['ETag'] = prev_etag
                cherrypy.lib.cptools.validate_etags()
            except cherrypy.HTTPError as e:
                error_msg = "ETag mismatch. Please try again." + str(e)
                error = Precondition(error_msg)
                return error.message()

            # Validate Last-Modified conditional request
            try:
                cherrypy.response.headers['Last-Modified'] = last_modified
                cherrypy.lib.cptools.validate_since()
            except cherrypy.HTTPError as e:
                error_msg = "Mismatch on last modification date. Please try again." + str(e)
                error = Precondition(error_msg)
                return error.message()

            if ("dnsRuleId" in new_rec):
                del new_rec["dnsRuleId"]

            # Update the DNS rule in the database with the new "lastModified" date
            # and add it to the response
            new_date = cherrypy.response.headers['Date']
            cherrypy.thread_data.db.update("dnsRules",
                                            query=dns_rule_query,
                                            newdata=new_rec|{"lastModified": new_date})
            cherrypy.response.headers['Last-Modified'] = new_date

            """
            diff = DeepDiff(new_rec, dns_rule_dict, ignore_order=True)
            cherrypy.log("Dns Rule %s from app %s updated:\n%s"
                        %(dnsRuleId, appInstanceId, diff))
            """

            # Return the updated DNS rule in the response body
            dns_rule_dict.update(new_rec)
            cherrypy.response.body = dns_rule_dict

            # Generate the new ETag and add it to the response headers
            new_rule = json.dumps(dns_rule_dict)
            new_etag = md5(new_rule.encode('utf-8')).hexdigest()
            cherrypy.response.headers['ETag'] = new_etag
            
            cherrypy.response.status = 200
            
            return dns_rule_dict

       
