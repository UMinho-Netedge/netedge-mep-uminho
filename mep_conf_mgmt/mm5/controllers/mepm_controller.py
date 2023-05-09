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
import jsonschema
import uuid
import base64
import copy

sys.path.append("../../")
from mm5.models import *
from hashlib import md5
from mm5.controllers.app_callback_controller import *

class MecPlatformMgMtController:

    @cherrypy.tools.json_in()
    @json_out(cls=NestedEncoder)
    def mecApp_configure(self, appInstanceId: str):
        #ConfigPlatform for App Request
        
        cherrypy.log("Received request to configure app %s" %appInstanceId)

        appStatus = cherrypy.thread_data.db.query_col(
            "appStatus",
            query=dict(appInstanceId=appInstanceId),
            find_one=True,
        )

        # If app exists in db return error
        if appStatus is not None:
            error_msg = "Application %s already exists." % (appInstanceId)
            error = Conflict(error_msg)
            return error.message()

        try:
            oauth = cherrypy.config.get("oauth_server")
            credentials = oauth.register()
            token = oauth.get_token(credentials["client_id"], credentials["client_secret"])
            credentials["access_token"] = token            
                    
        except:
            error_msg = "OAuth server is not available, please try again in a few minutes."
            error = Forbidden(error_msg)
            return error.message()

        data = cherrypy.request.json

        try:
            configRequest = ConfigPlatformForAppRequest.from_json(data)
        except (TypeError, jsonschema.exceptions.ValidationError) as e:
            error = BadRequest(e)
            return error.message()  

        # Configure Traffic Rules
        if configRequest.appTrafficRule is not None:
            for ruleDescriptor in configRequest.appTrafficRule:

                rule = ruleDescriptor.trafficRule
                    
                CallbackController.execute_callback(
                    args=[appInstanceId, rule],
                    func=CallbackController._configureTrafficRule,
                    sleep_time=0
                )

                cherrypy.thread_data.db.create(
                    "trafficRules",
                    object_to_mongodb_dict(
                    rule,
                    extra=dict(appInstanceId=appInstanceId)
                    )
                )
        
        # Configure DNS Rules
        if configRequest.appDNSRule is not None:
            for ruleDescriptor in configRequest.appDNSRule:

                rule = ruleDescriptor.dnsRule
                    
                CallbackController.execute_callback(
                    args=[appInstanceId, rule],
                    func=CallbackController._configureDnsRule,
                    sleep_time=0
                )

                lastModified = cherrypy.response.headers['Date']

                new_rec = {
                    "appInstanceId": appInstanceId, 
                    "lastModified": lastModified,
                    } | rule.to_json()
                cherrypy.thread_data.db.create("dnsRules", new_rec)

        appState  = AppInstanceState(InstantiationState.INSTANTIATED.value, OperationalState.STARTED.value)
        appStatusDict = dict(
            appInstanceId=appInstanceId,
            state = appState.to_json(),
            indication="STARTING",
            services=[], 
            oauth=credentials
        )

        cherrypy.thread_data.db.create("appStatus", appStatusDict)

        lifecycleOperationOccurrenceId = str(uuid.uuid4())
        lastModified = cherrypy.response.headers['Date']
    
        lcmOperationOccurence = dict(
            lifecycleOperationOccurrenceId=lifecycleOperationOccurrenceId,
            appInstanceId=appInstanceId, 
            stateEnteredTime=lastModified,
            operation="STARTING",
            operationStatus=OperationStatus.PROCESSING.name
        )

        cherrypy.thread_data.db.create("lcmOperations", lcmOperationOccurence)

        cherrypy.response.status = 201
        return dict(lifecycleOperationOccurrenceId=lifecycleOperationOccurrenceId)


    @cherrypy.tools.json_in()
    @json_out(cls=NestedEncoder)
    def mecApp_updateState(self, appInstanceId: str):

        cherrypy.log("Received request to change app %s state" %appInstanceId)

        appStatus = cherrypy.thread_data.db.query_col(
            "appStatus",
            query=dict(appInstanceId=appInstanceId),
            find_one=True,
        )

        # If app exists in db
        if appStatus is None:
            error_msg = "Application %s not instantiated." % (appInstanceId)
            error = Conflict(error_msg)
            return error.message()

        data = cherrypy.request.json
        # The process of generating the class allows for "automatic" validation of the json and
        # for filtering after saving to the database
        try:
            # Verify the requestion body if its correct about its schema:
            updateState = ChangeAppInstanceState.from_json(data)

        except (TypeError, jsonschema.exceptions.ValidationError) as e:
            error = BadRequest(e)
            return error.message()

        # if updateState.changeStateTo.value == appStatus["state"]["operationalState"].value:
        # AttributeError: 'str' object has no attribute 'value'
        if updateState.changeStateTo.value == appStatus["state"]["operationalState"]:
            error_msg = "Application %s already in state %s." % (appInstanceId, updateState.changeStateTo.value)
            error = Conflict(error_msg)
            return error.message()


        if updateState.changeStateTo.value == ChangeStateTo.STOPPED.value:
            operationAction = OperationActionType.STOPPING

            ## Do the terminationNotification task of change app status
            subscription = cherrypy.thread_data.db.query_col(
                "appSubscriptions",
                query=dict(appInstanceId=appInstanceId),
                fields=dict(subscriptionId=0),
                find_one=True,
            )
            
            subscription = AppTerminationNotificationSubscription.from_json(subscription)

            ## Do the terminationNotification task of change app status
            notification = AppTerminationNotification(
                    operationAction=operationAction, 
                    maxGracefulTimeout=updateState.gracefulStopTimeout,
                    _links=subscription._links
                )
            CallbackController.execute_callback(
                args=[subscription, notification],
                func=CallbackController._callback_function,
                sleep_time=10
            )

        appState  = AppInstanceState(InstantiationState.INSTANTIATED, OperationalState.STOPPED)

        appInstanceDict = dict(appInstanceId=appInstanceId)
        appStatusDict = dict(
            indication=updateState.changeStateTo.name,
            state=appState.to_json()
        )

        cherrypy.thread_data.db.update(
            "appStatus", 
            appInstanceDict, 
            appStatusDict
        )

        lifecycleOperationOccurrenceId = str(uuid.uuid4())
        lastModified = cherrypy.response.headers['Date']

        lcmOperationOccurence = dict(
            lifecycleOperationOccurrenceId=lifecycleOperationOccurrenceId,
            appInstanceId=appInstanceId, 
            stateEnteredTime=lastModified,
            operation=updateState.changeStateTo.name,
            operationStatus=OperationStatus.PROCESSING.name
        )

        cherrypy.thread_data.db.create("lcmOperations", lcmOperationOccurence)
       
        return dict(lifecycleOperationOccurrenceId=lifecycleOperationOccurrenceId)


    @cherrypy.tools.json_in()
    @json_out(cls=NestedEncoder)
    def mecApp_terminate(self, appInstanceId: str):

        cherrypy.log("Received request to terminate app %s state" %appInstanceId)

        appStatus = cherrypy.thread_data.db.query_col(
            "appStatus",
            query=dict(appInstanceId=appInstanceId),
            find_one=True,
        )

        # If app does not exist in db
        if appStatus is None:
            error_msg = "Application %s not instantiated." % (appInstanceId)
            error = Conflict(error_msg)
            return error.message()

        data = cherrypy.request.json

        # The process of generating the class allows for "automatic" validation of the json and
        # for filtering after saving to the database
        try:
            # Verify the requestion body if its correct about its schema:
            termination = TerminateAppInstance.from_json(copy.deepcopy(data))

        except (TypeError, jsonschema.exceptions.ValidationError) as e:
            error = BadRequest(e)
            return error.message()

        if data['appInstanceId'] != appInstanceId:
            error_msg = "Application in body %s does not match the one in the URL %s." % (data['appInstanceId'], appInstanceId)
            error = BadRequest(error_msg)
            return error.message()

        if termination.terminationType == TerminationType.GRACEFUL:
            subscription = cherrypy.thread_data.db.query_col(
                "appSubscriptions",
                query=dict(appInstanceId=appInstanceId),
                fields=dict(subscriptionId=0),
                find_one=True,
            )
            
            subscription = AppTerminationNotificationSubscription.from_json(subscription)
            #  Send the terminationNotification 
            #  Must update the lcmOperations state after the response and conclude the app configuration removal
            notification = AppTerminationNotification(
                    operationAction=OperationActionType.TERMINATING, 
                    maxGracefulTimeout=termination.gracefulStopTimeout,
                    _links=subscription._links
                )

            CallbackController.execute_callback(
                args=[subscription, notification],
                func=CallbackController._notifyTermination,
                sleep_time=0
            )

            appInstanceDict = dict(appInstanceId=appInstanceId)
            appStatusDict = dict(
                {"indication" : OperationActionType.TERMINATING.name}
            )
            
            cherrypy.thread_data.db.update(
                "appStatus",
                appInstanceDict,
                appStatusDict
            )

            lifecycleOperationOccurrenceId = str(uuid.uuid4())
            lastModified = cherrypy.response.headers['Date']

            lcmOperationOccurence = dict(
                lifecycleOperationOccurrenceId=lifecycleOperationOccurrenceId,
                appInstanceId=appInstanceId, 
                stateEnteredTime=lastModified,
                operation=OperationActionType.TERMINATING.name,
                operationStatus=OperationStatus.PROCESSING.name
            )

            time.sleep(termination.gracefulStopTimeout)
            # CallbackController.execute_callback(
            #     args=[appInstanceId, lifecycleOperationOccurrenceId],
            #     func=CallbackController._gracefulTerminationChecker,
            #     sleep_time=termination.gracefulStopTimeout
            # )
            

            # cherrypy.thread_data.db.create("lcmOperations", lcmOperationOccurence)

            # return dict(lifecycleOperationOccurrenceId=lifecycleOperationOccurrenceId)

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


        # remove application subscriptions of the collection
        result =  cherrypy.thread_data.db.query_col(
            "appSubscriptions", 
            query=query,
            fields=appInstanceDict,
        )

        for subscription in result:
            cherrypy.thread_data.db.remove(col="appSubscriptions", query=dict(subscriptionId=subscription["subscriptionId"]))


        lifecycleOperationOccurrenceId = str(uuid.uuid4())
        lastModified = cherrypy.response.headers['Date']
            
        lcmOperationOccurence = dict(
                lifecycleOperationOccurrenceId=lifecycleOperationOccurrenceId,
                appInstanceId=appInstanceId, 
                stateEnteredTime=lastModified,
                operation=OperationActionType.TERMINATING.name,
                operationStatus=OperationStatus.SUCCESSFULLY_DONE.name
            )
        cherrypy.thread_data.db.create("lcmOperations", lcmOperationOccurence)

        return dict(lifecycleOperationOccurrenceId=lifecycleOperationOccurrenceId)


    @cherrypy.tools.json_in()
    @json_out(cls=NestedEncoder)
    def mecApp_update_config(self, appInstanceId: str):
        #Update App configuration
        
        cherrypy.log("Received request to reconfigure app %s" %appInstanceId)

        appStatus = cherrypy.thread_data.db.query_col(
            "appStatus",
            query=dict(appInstanceId=appInstanceId),
            find_one=True,
        )

        # If app exists in db
        if appStatus is None or appStatus['state'] == "NOT_INSTANTIATED":
            error_msg = "Application %s does not exist." % (appInstanceId)
            error = Conflict(error_msg)
            return error.message()

        data = cherrypy.request.json

        try:
            configRequest = ConfigPlatformForAppRequest.from_json(data)
        except (TypeError, jsonschema.exceptions.ValidationError) as e:
            error = BadRequest(e)
            return error.message()  

        # Configure Traffic Rules
        for ruleDescriptor in configRequest.appTrafficRule:

            rule = ruleDescriptor.trafficRule
                
            CallbackController.execute_callback(
                args=[appInstanceId, rule],
                func=CallbackController._configureTrafficRule,
                sleep_time=0
            )

            cherrypy.thread_data.db.create(
                "trafficRules",
                object_to_mongodb_dict(
                rule,
                extra=dict(appInstanceId=appInstanceId)
                )
            )
        
        # Configure DNS Rules
        for ruleDescriptor in configRequest.appDNSRule:

            rule = ruleDescriptor.dnsRule
                
            CallbackController.execute_callback(
                args=[appInstanceId, rule],
                func=CallbackController._configureDnsRule,
                sleep_time=0
            )

            lastModified = cherrypy.response.headers['Date']

            new_rec = {
                "appInstanceId": appInstanceId, 
                "lastModified": lastModified,
                } | rule.to_json()
            cherrypy.thread_data.db.create("dnsRules", new_rec)

        cherrypy.response.status = 204
        return None


    # TODO: CHECK IF THIS IS CORRECT
    # INCOMPLETE
    @cherrypy.tools.json_in()
    @json_out(cls=NestedEncoder)
    def mecApp_config_get(self, appInstanceId: str):
        #Get App configuration
        
        cherrypy.log("Received request to get app %s configuration" %appInstanceId)

        appStatus = cherrypy.thread_data.db.query_col(
            "appStatus",
            query=dict(appInstanceId=appInstanceId),
            find_one=True,
        )

        # If app exists in db
        if appStatus is None or appStatus['state'] == "NOT_INSTANTIATED":
            error_msg = "Application %s does not exist." % (appInstanceId)
            error = Conflict(error_msg)
            return error.message()

        # Get Traffic Rules
        traffic_rules = cherrypy.thread_data.db.query_col(
            "trafficRules",
            query=dict(appInstanceId=appInstanceId)
        )

        traffic_rules = [TrafficRuleDescriptor(trafficRule=TrafficRule.from_json(rule)) for rule in traffic_rules]

        # Get DNS Rules
        dns_rules = cherrypy.thread_data.db.query_col(
            "dnsRules",
            query=dict(appInstanceId=appInstanceId)
        )

        dns_rules = [DNSRuleDescriptor(dnsRule=dns_rules.from_json(rule)) for rule in dns_rules]

        return ConfigPlatformForAppRequest(appTrafficRule=traffic_rules, appDNSRule=dns_rules)


    @json_out(cls=NestedEncoder)
    def lcmOpp_get_all(self, **kwargs):
        """
        Get the status of all LCM operations
        """
        
        if kwargs != {}:
            error_msg = "Invalid attribute(s): %s" % (str(kwargs))
            error = BadRequest(error_msg)
            return error.message()

        result = cherrypy.thread_data.db.query_col("lcmOperations", query={})
        res = list(result)
        
        if len(res) == 0:
            error = NotFound("No LCM operation found")
            return error.message()
        
        return res


    @json_out(cls=NestedEncoder)
    def lcmOpp_get(self, appLcmOpOccId:str, **kwargs):
        """
        Get the status of a LCM operation
        """

        if kwargs != {}:
            error_msg = "Invalid attribute(s): %s" % (str(kwargs))
            error = BadRequest(error_msg)
            return error.message()

        query = dict(
            lifecycleOperationOccurrenceId=appLcmOpOccId
        )
        result = cherrypy.thread_data.db.query_col(
            "lcmOperations", query=query, find_one=True
        )
        if result is None:
            error = NotFound("No LCM operation found with the given id")
            return error.message()
        return result


    @cherrypy.tools.json_in()
    @json_out(cls=NestedEncoder)
    def traffic_rule_post_with_traffic_rule_id(self, appInstanceId: str, trafficRuleId: str):
        cherrypy.log("Request to configure traffic rule %s received" %appInstanceId)
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

        data = cherrypy.request.json
        try:
            trafficRule = TrafficRule.from_json(data)

        except (TypeError, jsonschema.exceptions.ValidationError) as e:
            error = BadRequest(e)
            return error.message()

        if appStatus['indication'] == IndicationType.READY.name or appStatus['indication'] == "STARTING":

            # Check if the traffic rule already exists and return error message
            result = cherrypy.thread_data.db.query_col(
                "trafficRules", 
                query=dict(trafficRuleId=trafficRuleId),
                fields=dict(appInstanceId=0),
                find_one=True
            )

            # If trafficrule does not exist in db
            if result is not None:
                error_msg = "Traffic rule %s already configured." % (trafficRuleId)
                error = NotFound(error_msg)
                return error.message()           
            

            CallbackController.execute_callback(
                args=[appInstanceId, trafficRule],
                func=CallbackController._configureTrafficRule,
                sleep_time=5
            )

            cherrypy.thread_data.db.create(
                "trafficRules",
                object_to_mongodb_dict(
                trafficRule,
                extra=dict(appInstanceId=appInstanceId)
                )
            )

            cherrypy.response.status = 201
            return trafficRule


        else:
            error_msg = "Application %s is in %s state. This operation not allowed in this state." % (
            appInstanceId, appStatus["indication"])
            error = Forbidden(error_msg)
            return error.message()


    @cherrypy.tools.json_in()
    @json_out(cls=NestedEncoder)
    def traffic_rules_post(self, appInstanceId: str):

        cherrypy.log("Request to configure traffic rules for App %s received" %appInstanceId)
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

        data = cherrypy.request.json
        trafficRules = []
        for rule in data:
            try:
                trafficRuleId = rule["trafficRuleId"]
                # Check if the traffic rule already exists and return error message
                result = cherrypy.thread_data.db.query_col(
                    "trafficRules", 
                    query=dict(trafficRuleId=trafficRuleId),
                    fields=dict(appInstanceId=0),
                    find_one=True
                )

                # If trafficrule exists in db
                if result is not None:
                    error_msg = "Traffic rule %s already configured." % (trafficRuleId)
                    error = NotFound(error_msg)
                    return error.message()
                
                trafficRule = TrafficRule.from_json(rule)
                trafficRules.append(trafficRule)

            except (TypeError, jsonschema.exceptions.ValidationError) as e:
                error = BadRequest(e)
                return error.message()

        if appStatus['indication'] == IndicationType.READY.name or appStatus['indication'] == "STARTING":

            for rule in trafficRules:
                
                CallbackController.execute_callback(
                    args=[appInstanceId, rule],
                    func=CallbackController._configureTrafficRule,
                    sleep_time=5
                )

                cherrypy.thread_data.db.create(
                    "trafficRules",
                    object_to_mongodb_dict(
                    rule,
                    extra=dict(appInstanceId=appInstanceId)
                    )
                )

            cherrypy.response.status = 201
            return trafficRules


        else:
            error_msg = "Application %s is in %s state. This operation not allowed in this state." % (
            appInstanceId, appStatus["indication"])
            error = Forbidden(error_msg)
            return error.message()


    @cherrypy.tools.json_in()
    @json_out(cls=NestedEncoder)
    def dns_rule_post_with_dns_rule_id(self, appInstanceId: str, dnsRuleId: str):
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

        #print(f"tests_controller new_rec:\n{new_rec}")

        # Generate hash
        rule = json.dumps(new_rec)
        new_etag = md5(rule.encode('utf-8')).hexdigest()
        # print(f"\nPOST new_etag: {new_etag}")

        # Add headers
        cherrypy.response.headers['ETag'] = new_etag
        lastModified = cherrypy.response.headers['Date']
        cherrypy.response.headers['Last-Modified'] = lastModified


        query = dict(appInstanceId=appInstanceId, dnsRuleId=dnsRuleId)

        # to assure correct document override
        if cherrypy.thread_data.db.count_documents("dnsRules", query) > 0:
            cherrypy.thread_data.db.remove("dnsRules", query)

        dnsApiServer = cherrypy.config.get("dns_api_server")

        dnsApiServer.create_record(new_rec["domainName"], new_rec["ipAddress"], new_rec["ttl"])

        new_rec = {
            "appInstanceId": appInstanceId, 
            "lastModified": lastModified,
            } | new_rec
        cherrypy.thread_data.db.create("dnsRules", new_rec)
   
        cherrypy.response.status = 200
        return dnsRule


    @cherrypy.tools.json_in()
    @json_out(cls=NestedEncoder)
    def dns_rules_post(self, appInstanceId: str):

        cherrypy.log("Request to configure dns rules for App %s received" %appInstanceId)
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

        data = cherrypy.request.json

        for rule in data:
            try:
                dnsRule = DnsRule.from_json(rule)
            except (TypeError, jsonschema.exceptions.ValidationError) as e:
                error = BadRequest(e)
                return error.message()

            new_rec = dnsRule.to_json()

            #print(f"tests_controller new_rec:\n{new_rec}")

            # Generate hash
            rule = json.dumps(new_rec)
            new_etag = md5(rule.encode('utf-8')).hexdigest()
            # print(f"\nPOST new_etag: {new_etag}")

            # Add headers
            cherrypy.response.headers['ETag'] = new_etag
            lastModified = cherrypy.response.headers['Date']
            cherrypy.response.headers['Last-Modified'] = lastModified


            query = dict(appInstanceId=appInstanceId, dnsRuleId=new_rec["dnsRuleId"])

            # to assure correct document override
            if cherrypy.thread_data.db.count_documents("dnsRules", query) > 0:
                cherrypy.thread_data.db.remove("dnsRules", query)

            new_rec = {
                "appInstanceId": appInstanceId, 
                "lastModified": lastModified,
                } | new_rec
            cherrypy.thread_data.db.create("dnsRules", new_rec)
   
        cherrypy.response.status = 200
        return data


