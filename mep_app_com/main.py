# Copyright 2022 Centro ALGORITMI - University of Minho and Instituto de Telecomunicações - Aveiro
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

# Service Management Controllers
from mp1.service_mgmt.controllers.app_service_subscriptions_controller          \
    import (ApplicationServicesSubscriptionsController,)
from mp1.service_mgmt.controllers.app_services_controller                       \
    import (ApplicationServicesController,)
from mp1.service_mgmt.controllers.services_controller                           \
    import (ServicesController,)
from mp1.service_mgmt.controllers.transports_controller                         \
    import (TransportsController,)
from mp1.service_mgmt.controllers.individual_mecservice_liveness                \
    import (InvidualMecServiceLivenessController,)

# Application Support Controllers
from mp1.application_support.controllers.app_traffic_rules_controller           \
    import (AppTrafficRulesController,)
from mp1.application_support.controllers.app_confirmation_controller            \
    import (ApplicationConfirmationController,)
from mp1.application_support.controllers.app_dns_rules_controller               \
    import (AppDnsRulesController,)
from mp1.application_support.controllers.app_timing_controller                  \
    import (AppTimingController,)
from mp1.application_support.controllers.app_traffic_rules_controller           \
    import (AppTrafficRulesController,)
from mp1.application_support.controllers.app_subscriptions_controller           \
    import (ApplicationSubscriptionsController)
from mp1.application_support.controllers.app_token_controller                   \
    import (AppTokenController,)


from mp1.databases.database_base import DatabaseBase
from mp1.databases.dbmongo import MongoDb
from typing import Type
import cherrypy
from mp1.utils import check_port
from mp1.models import *
import json
import os

@json_out(cls=NestedEncoder)
def main(database: Type[DatabaseBase]):

    ##################################
    # Application support interface  #
    ##################################

    support_dispatcher = cherrypy.dispatch.RoutesDispatcher()

    #####################################
    # Application ready and termination #
    #####################################
    support_dispatcher.connect(
        name="Application Ready Notification",
        action="application_confirm_ready",
        controller=ApplicationConfirmationController,
        route="/applications/:appInstanceId/confirm_ready",
        conditions=dict(method=["POST"]),
    )

    support_dispatcher.connect(
        name="Application termination request",
        action="application_confirm_termination",
        controller=ApplicationConfirmationController,
        route="/applications/:appInstanceId/confirm_termination",
        conditions=dict(method=["POST"]),
    )

    #######################################
    # Application Subscription Controller #
    #######################################

    support_dispatcher.connect(
        name="Get an applicationInstanceId Subscriptions",
        action="applications_subscriptions_get",
        controller=ApplicationSubscriptionsController,
        route="/applications/:appInstanceId/subscriptions",
        conditions=dict(method=["GET"]),
    )

    support_dispatcher.connect(
        name="Get an applicationInstanceId Subscriptions",
        action="applications_subscriptions_get_with_subscription_id",
        controller=ApplicationSubscriptionsController,
        route="/applications/:appInstanceId/subscriptions/:subscriptionId",
        conditions=dict(method=["GET"]),
    )

    support_dispatcher.connect(
        name="Create applicationInstanceId Subscriptions",
        action="applications_subscriptions_post",
        controller=ApplicationSubscriptionsController,
        route="/applications/:appInstanceId/subscriptions",
        conditions=dict(method=["POST"]),
    )

    support_dispatcher.connect(
        name="Delete applicationInstanceID Subscriptions with subscriptionId",
        action="applications_subscriptions_delete",
        controller=ApplicationSubscriptionsController,
        route="/applications/:appInstanceId/subscriptions/:subscriptionId",
        conditions=dict(method=["DELETE"]),
    )


    #################################
    # App Traffic Rules Controller  #
    #################################
    support_dispatcher.connect(
        name="Get Traffic Rules",
        action="traffic_rules_get",
        controller=AppTrafficRulesController,
        route="/applications/:appInstanceId/traffic_rules",
        conditions=dict(method=["GET"]),
    )

    support_dispatcher.connect(
        name="Get Traffic Rule with trafficRuleId",
        action="traffic_rule_get_with_traffic_rule_id",
        controller=AppTrafficRulesController,
        route="/applications/:appInstanceId/traffic_rules/:trafficRuleId",
        conditions=dict(method=["GET"]),
    )

    support_dispatcher.connect(
        name="Put data into existing traffic rule",
        action="traffic_rules_put",
        controller=AppTrafficRulesController,
        route="/applications/:appInstanceId/traffic_rules/:trafficRuleId",
        conditions=dict(method=["PUT"]),
    )

    #############################
    # App DNS Rules Controller  #
    #############################
    support_dispatcher.connect(
        name="Get DNS Rules",
        action="dns_rules_get",
        controller=AppDnsRulesController,
        route="/applications/:appInstanceId/dns_rules",
        conditions=dict(method=["GET"]),
    )

    support_dispatcher.connect(
        name="Get DNS Rule with DnsRuleId",
        action="dns_rule_get_with_dns_rule_id",
        controller=AppDnsRulesController,
        route="/applications/:appInstanceId/dns_rules/:dnsRuleId",
        conditions=dict(method=["GET"]),
    )

    support_dispatcher.connect(
        name="Put data into existing DNS rule",
        action="dns_rules_put",
        controller=AppDnsRulesController,
        route="/applications/:appInstanceId/dns_rules/:dnsRuleId",
        conditions=dict(method=["PUT"]),
    )

    #########################
    # App Timing Controller #
    #########################
    support_dispatcher.connect(
        name="Get Timing Capabilites",
        action="timing_capabilites_get",
        controller=AppTimingController,
        route="/timing/timing_caps",
        conditions=dict(method=["GET"]),
    )

    support_dispatcher.connect(
        name="Get Current Time",
        action="current_time_get",
        controller=AppTimingController,
        route="/timing/current_time",
        conditions=dict(method=["GET"]),
    )

    #########################
    # App Token Controller  #
    #########################
    support_dispatcher.connect(
        name="Get App Instance Token",
        action="get_credentials",
        controller=AppTokenController,
        route="/credentials/",
        conditions=dict(method=["POST"]),
    )


    #############################################
    # Application service management interface  #
    #############################################

    mgmt_dispatcher = cherrypy.dispatch.RoutesDispatcher()
    # Todo load from config file
    
    #######################################
    # Application Subscription Controller #
    #######################################

    mgmt_dispatcher.connect(
        name="Get an applicationInstanceId Subscriptions",
        action="applications_subscriptions_get",
        controller=ApplicationServicesSubscriptionsController,
        route="/applications/:appInstanceId/subscriptions",
        conditions=dict(method=["GET"]),
    )

    mgmt_dispatcher.connect(
        name="Get an applicationInstanceId Subscriptions",
        action="applications_subscriptions_get_with_subscription_id",
        controller=ApplicationServicesSubscriptionsController,
        route="/applications/:appInstanceId/subscriptions/:subscriptionId",
        conditions=dict(method=["GET"]),
    )

    mgmt_dispatcher.connect(
        name="Create applicationInstanceId Subscriptions",
        action="applications_subscriptions_post",
        controller=ApplicationServicesSubscriptionsController,
        route="/applications/:appInstanceId/subscriptions",
        conditions=dict(method=["POST"]),
    )

    mgmt_dispatcher.connect(
        name="Delete applicationInstanceID Subscriptions with subscriptionId",
        action="applications_subscriptions_delete",
        controller=ApplicationServicesSubscriptionsController,
        route="/applications/:appInstanceId/subscriptions/:subscriptionId",
        conditions=dict(method=["DELETE"]),
    )

    ###################################
    # Application Services Controller #
    ###################################

    mgmt_dispatcher.connect(
        name="Get service from InstanceId and parameters",
        action="applications_services_get",
        controller=ApplicationServicesController,
        route="/applications/:appInstanceId/services",
        conditions=dict(method=["GET"]),
    )

    mgmt_dispatcher.connect(
        name="Create service for InstanceId",
        action="applications_services_post",
        controller=ApplicationServicesController,
        route="/applications/:appInstanceId/services",
        conditions=dict(method=["POST"]),
    )

    mgmt_dispatcher.connect(
        name="Get service from InstanceId and ServiceId",
        action="applicaton_services_get_with_service_id",
        controller=ApplicationServicesController,
        route="/applications/:appInstanceId/services/:serviceId",
        conditions=dict(method=["GET"]),
    )

    mgmt_dispatcher.connect(
        name="Put data into existing service",
        action="application_services_put",
        controller=ApplicationServicesController,
        route="/applications/:appInstanceId/services/:serviceId",
        conditions=dict(method=["PUT"]),
    )

    mgmt_dispatcher.connect(
        name="Delete service",
        action="application_services_delete",
        controller=ApplicationServicesController,
        route="/applications/:appInstanceId/services/:serviceId",
        conditions=dict(method=["DELETE"]),
    )

    #######################
    # Services Controller #
    #######################

    mgmt_dispatcher.connect(
        name="Get services",
        action="services_get",
        controller=ServicesController,
        route="/services",
        conditions=dict(method=["GET"]),
    )

    mgmt_dispatcher.connect(
        name="Get services with serviceId",
        action="services_get_with_serviceId",
        controller=ServicesController,
        route="/services/:serviceId",
        conditions=dict(method=["GET"]),
    )

    ########################
    # Transport Controller #
    ########################
    mgmt_dispatcher.connect(
        name="Get transports",
        action="transports_get",
        controller=TransportsController,
        route="/transports",
        conditions=dict(method=["GET"]),
    )

    ###################################
    # IndividualMecService Controller #
    ###################################
    mgmt_dispatcher.connect(
        name="Get MEC Service Liveness",
        action="mecServiceLiveness_get",
        controller=InvidualMecServiceLivenessController,
        route="/liveness/:appInstanceId/:serviceId",
        conditions=dict(method=["GET"]),
    )

    mgmt_dispatcher.connect(
        name="Update MEC Service Liveness",
        action="mecServiceLiveness_update",
        controller=InvidualMecServiceLivenessController,
        route="/liveness/:appInstanceId/:serviceId",
        conditions=dict(method=["PATCH"]),
    )


    cherrypy.config.update(
        {"server.socket_host": "0.0.0.0", "server.socket_port": 8080}
    )

    supp_conf = {"/": {"request.dispatch": support_dispatcher}}
    cherrypy.tree.mount(None, "/mec_app_support/v1", config=supp_conf)
    mgmt_conf = {"/": {"request.dispatch": mgmt_dispatcher}}
    cherrypy.tree.mount(None, "/mec_service_mgmt/v1", config=mgmt_conf)



    # Config 404 and 403 landing pages
    cherrypy.config.update({'error_page.404': error_page_404})
    cherrypy.config.update({'error_page.403': error_page_403})
    cherrypy.config.update({'error_page.400': error_page_400})


    ######################################
    # Database Connection to all threads #
    ######################################
    if isinstance (database, DatabaseBase):
        cherrypy.engine.subscribe('start_thread', database.connect)
        cherrypy.engine.start()
    else:
        cherrypy.log("Invalid database provided to MEP. Shutting down.")

@json_out(cls=NestedEncoder)
def error_page_404(status, message, traceback, version):
    error_msg = "URI %s cannot be mapped to a valid resource." % cherrypy.request.path_info
    error = NotFound(error_msg)
    # cherrypy.response.headers["Content-Type"] = "application/problem+json"
    return error.message()

@json_out(cls=NestedEncoder)
def error_page_403(status, message, traceback, version):
    error_msg = "The operation is not allowed given the current status of the resource."
    error = Forbidden(error_msg)
    # cherrypy.response.headers['Content-Type'] = "application/problem+json"
    return error.message()

@json_out(cls=NestedEncoder)
def error_page_400(status, message, traceback, version):
    error_msg = "The operation is not allowed given the current status of the resource."
    error = BadRequest(error_msg)
    # cherrypy.response.headers['Content-Type'] = "application/problem+json"
    return error.message()


if __name__ == "__main__":
    mongodb_addr = os.environ.get("ME_CONFIG_MONGODB_SERVER")
    mongodb_port = os.environ.get("ME_CONFIG_MONGODB_PORT")
    mongodb_username = os.environ.get("ME_CONFIG_MONGODB_ADMINUSERNAME")
    mongodb_password = os.environ.get("ME_CONFIG_MONGODB_ADMINPASSWORD")
    mongodb_database = os.environ.get("ME_CONFIG_MONGODB_DATABASE")

    database = MongoDb(mongodb_addr, mongodb_port, mongodb_username, mongodb_password, mongodb_database)
    
    oauth_addr = os.environ.get("OAUTH_SERVER")
    oauth_port = os.environ.get("OAUTH_PORT")
    oauthServer = OAuthServer(oauth_addr, oauth_port)
    cherrypy.config.update({"oauth_server": oauthServer})

    dns_api_addr = os.environ.get("DNS_API_SERVER")
    dns_api_port = os.environ.get("DNS_API_PORT")
    dnsApiServer = DnsApiServer(dns_api_addr, dns_api_port)
    cherrypy.config.update({"dns_api_server": dnsApiServer})

    mepconfig_url = os.environ.get("MEPCONFIG_SERVER")
    mepconfig_port = os.environ.get("MEPCONFIG_PORT")
    cherrypy.config.update({"mepconfig": (mepconfig_url, mepconfig_port)})

    with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace") as namespace_file:
        cherrypy.config.update({"namespace":namespace_file.read()}) 
    
    main(database)
