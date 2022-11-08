import sys
import jsonschema
from urllib import request, parse
sys.path.append("../../")
from mp1.models import *
from hashlib import md5
from datetime import datetime
import uuid
from mp1.application_support.controllers.app_callback_controller import *

class MecPlatformMgMtController:

    @json_out(cls=NestedEncoder)
    def mecApp_configure(self, appInstanceId: str, **kwargs,):
        #ConfigPlatform for App Request
        
        cherrypy.log("Received request to configure app %s" %appInstanceId)

        appStatus = cherrypy.thread_data.db.query_col(
            "appStatus",
            query=dict(appInstanceId=appInstanceId),
            find_one=True,
        )

        # If app exists in db
        if appStatus is not None:
            error_msg = "Application %s already existis." % (appInstanceId)
            error = Conflict(error_msg)
            return error.message()

        if kwargs != {}:
            error_msg = "Invalid attribute(s): %s" % (str(kwargs))
            error = BadRequest(error_msg)
            return error.message()

        try:
            httpreq = request.Request("http://oauth:5001/register", method="GET")
            response = request.urlopen(httpreq)
            jsonobject = json.loads(response.read())
            print(jsonobject)

            credentials = dict(grant_type="client_credentials", client_id=jsonobject["client_id"], client_secret=jsonobject["client_secret"])

            httpreq = request.Request("http://oauth:5001/token", data=parse.urlencode(credentials).encode('utf-8'), method="POST")
            # print(credentials)
            # httpreq = request.Request("http://oauth:5001/token", method="POST")
            # httpreq.add_header('Content-Type', 'application/json')
            response = request.urlopen(httpreq)
            jsonobject = json.loads(response.read())
            print(jsonobject)
            credentials["access_token"] = jsonobject["access_token"]
            print(credentials)

        except:
            error_msg = "OAuth server is not available, please try again in a few minutes."
            error = Forbidden(error_msg)
            return error.message()
        
        appStatusDict = dict(
            appInstanceId=appInstanceId, 
            indication="STARTING", 
            services=[], 
            oauth=credentials
        )

        cherrypy.thread_data.db.create("appStatus", appStatusDict)

        cherrypy.response.status = 201
        return None

    @cherrypy.tools.json_in()
    @json_out(cls=NestedEncoder)
    def mecAppStatus_update(self, appInstanceId: str):

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

        
        ## Do the terminationNotification task of change app status
        subscription = cherrypy.thread_data.db.query_col(
            "appSubscriptions",
            query=dict(appInstanceId=appInstanceId),
            fields=dict(subscriptionId=0),
            find_one=True,
        )
        
        subscription = AppTerminationNotificationSubscription.from_json(subscription)

        if updateState.changeStateTo.name == ChangeStateTo.STOPPED.name:
            operationAction = OperationActionType.STOPPING
        ## Do the terminationNotification task of change app status
        CallbackController.execute_callback(
            subscription=subscription,
            notification=AppTerminationNotification(
                operationAction=operationAction, 
                maxGracefulTimeout=updateState.gracefulStopTimeout,
                _links=subscription._links
            )
        )
        ## (to remove after terminationNotification is implemented)

        appInstanceDict = dict(appInstanceId=appInstanceId)
        appStatusDict = dict(
            {"indication" : updateState.changeStateTo.name}
        )
        updateStatus = cherrypy.thread_data.db.update(
            "appStatus", 
            appInstanceDict, 
            appStatusDict
        )

        lifecycleOperationOccurrenceId = str(uuid.uuid4())
        
        lcmOperationOccurence = dict(
            lifecycleOperationOccurrenceId=lifecycleOperationOccurrenceId,
            appInstanceId=appInstanceId, 
            operation=updateState.changeStateTo.name,
            operationStatus=OperationStatus.PROCESSING.name
        )

        cherrypy.thread_data.db.create("lcmOperations", lcmOperationOccurence)

        # AppStatus confirmation of indication change
        print(f"\n# AppStatus confirmation #\nAppStatus of appInstanceId {appInstanceId}:")
        pprint.pprint(cherrypy.thread_data.db.query_col("appStatus", dict(appInstanceId=appInstanceId), find_one=True,))
        print(f"updateStatus.modified_count {updateStatus.modified_count}")
        print(f"updateStatus.matched_count {updateStatus.matched_count}\n")
        
        return dict(lifecycleOperationOccurrenceId=lifecycleOperationOccurrenceId)

    @cherrypy.tools.json_in()
    @json_out(cls=NestedEncoder)
    def mecApp_terminate(self, appInstanceId: str):

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
            termination = TerminateAppInstance.from_json(data)

        except (TypeError, jsonschema.exceptions.ValidationError) as e:
            error = BadRequest(e)
            return error.message()

        subscription = cherrypy.thread_data.db.query_col(
            "appSubscriptions",
            query=dict(appInstanceId=appInstanceId),
            fields=dict(subscriptionId=0),
            find_one=True,
        )
        
        subscription = AppTerminationNotificationSubscription.from_json(subscription)
        #  Send the terminationNotification 
        #  Must update the lcmOperations state after the response and conclude the app configuration removal
        CallbackController.execute_callback(
            subscription=subscription,
            notification=AppTerminationNotification(
                operationAction=OperationActionType.TERMINATING, 
                maxGracefulTimeout=termination.gracefulStopTimeout,
                _links=subscription._links
            )
        )

        appInstanceDict = dict(appInstanceId=appInstanceId)
        appStatusDict = dict(
            {"indication" : OperationActionType.TERMINATING.name}
        )
        updateStatus = cherrypy.thread_data.db.update(
            "appStatus", 
            appInstanceDict, 
            appStatusDict
        )

        lifecycleOperationOccurrenceId = str(uuid.uuid4())
        
        lcmOperationOccurence = dict(
            lifecycleOperationOccurrenceId=lifecycleOperationOccurrenceId,
            appInstanceId=appInstanceId, 
            operation=OperationActionType.TERMINATING.name,
            operationStatus=OperationStatus.PROCESSING.name
        )

        cherrypy.thread_data.db.create("lcmOperations", lcmOperationOccurence)

        # AppStatus confirmation of indication change
        print(f"\n# AppStatus confirmation #\nAppStatus of appInstanceId {appInstanceId}:")
        pprint.pprint(cherrypy.thread_data.db.query_col("appStatus", dict(appInstanceId=appInstanceId), find_one=True,))
        print(f"updateStatus.modified_count {updateStatus.modified_count}")
        print(f"updateStatus.matched_count {updateStatus.matched_count}\n")
        
        return dict(lifecycleOperationOccurrenceId=lifecycleOperationOccurrenceId)

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

            # config.load_incluster_config()
            # api_instance = client.NetworkingV1Api()
            # namespace = 'default' 
            # metadata = client.V1ObjectMeta(name=trafficRuleId)
            # expressions = client.V1LabelSelectorRequirement()
            # podselector = client.V1LabelSelector(match_labels={"app":appInstanceId})
            # policyType = "Ingress"

            # ports=[client.V1NetworkPolicyPort(end_port=8080, protocol="TCP")]
            # ingress = client.V1NetworkPolicyIngressRule(ports=ports)
            
            # spec = client.V1NetworkPolicySpec(pod_selector=podselector, policy_types=[policyType]) # , ingress=ingress)
            # status = client.V1Condition(status='True', last_transition_time=datetime.now(), message="teste", reason="ConfigureApplication", type="AppActivation")
            # body = client.V1NetworkPolicy(metadata=metadata, spec=spec, status=status) # V1NetworkPolicy | 
            # pretty = 'true' # str | If 'true', then the output is pretty printed. (optional)
            
            # dry_run = 'dry_run_example' # str | When present, indicates that modifications should not be persisted. An invalid or unrecognized dryRun directive will result in an error response and no further processing of the request. Valid values are: - All: all dry run stages will be processed (optional)
            
            # field_manager = 'mepserver' # str | fieldManager is a name associated with the actor or entity that is making these changes. The value must be less than or 128 characters long, and only contain printable characters, as defined by https://golang.org/pkg/unicode/#IsPrint. (optional)
            
            # field_validation = 'field_validation_example' # str | fieldValidation instructs the server on how to handle objects in the request (POST/PUT/PATCH) containing unknown or duplicate fields, provided that the `ServerSideFieldValidation` feature gate is also enabled. Valid values are: - Ignore: This will ignore any unknown fields that are silently dropped from the object, and will ignore all but the last duplicate field that the decoder encounters. This is the default behavior prior to v1.23 and is the default behavior when the `ServerSideFieldValidation` feature gate is disabled. - Warn: This will send a warning via the standard warning response header for each unknown field that is dropped from the object, and for each duplicate field that is encountered. The request will still succeed if there are no other errors, and will only persist the last of any duplicate fields. This is the default when the `ServerSideFieldValidation` feature gate is enabled. - Strict: This will fail the request with a BadRequest error if any unknown fields would be dropped from the object, or if any duplicate fields are present. The error returned from the server will contain all unknown and duplicate fields encountered. (optional)
            
            # api_response = api_instance.create_namespaced_network_policy(namespace, body, pretty=pretty, field_manager=field_manager)
            # print(api_response)


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
            
            # CallbackController.configure_trafficRules(
            #     appInstanceId=appInstanceId,
            #     trafficRules=[trafficRule],
            #     sleep_time=0)

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

            # configure traffic rule
            # CallbackController.configure_trafficRules(
            #     appInstanceId=appInstanceId,
            #     trafficRules=trafficRules,
            #     sleep_time=0)

            # Add trafficRuleId in appStatus -> appInstanceId for internal usage

            for rule in trafficRules:    
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
        print(f"\nPOST new_etag: {new_etag}")

        # Add headers
        cherrypy.response.headers['ETag'] = new_etag
        lastModified = cherrypy.response.headers['Date']
        cherrypy.response.headers['Last-Modified'] = lastModified


        query = dict(appInstanceId=appInstanceId, dnsRuleId=dnsRuleId)

        # to assure correct document override
        if cherrypy.thread_data.db.count_documents("dnsRules", query) > 0:
            cherrypy.thread_data.db.remove("dnsRules", query)

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
            print(f"\nPOST new_etag: {new_etag}")

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

    @json_out(cls=NestedEncoder)
    def remove_db_collections(self):
        app = cherrypy.thread_data.db.remove_many("appStatus", {})
        serv = cherrypy.thread_data.db.remove_many("services", {})
        dns = cherrypy.thread_data.db.remove_many("dnsRules", {})

        return {"appStatus": app.deleted_count,
                "services": serv.deleted_count,
                "dnsRules": dns.deleted_count}

