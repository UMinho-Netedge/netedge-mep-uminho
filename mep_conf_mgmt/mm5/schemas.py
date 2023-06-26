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


########################################################################
# This file serves the purpose to validate POST/PUT/PATCH HTTP METHODS #
# from a mec app. These schemas are json schemas that represent valid  #
# inputs that a mec app can execute                                    #
########################################################################
linktype_schema = {
    "type": "object",
    "properties": {
        "href": {"type": "string"},
    },
    "required": ["href"],
    "additionalProperties": False,
}

subscription_schema = {
    "type": "object",
    "properties": {"href": {"type": "string"}, "subscriptionType": {"type": "string"}},
    "required": ["href"],
    "additionalProperties": False,
}

links_schema = {
    "type": "object",
    "properties": {
        "self": linktype_schema,
        "subscriptions": {"type": "array", "items": subscription_schema},
        "liveness": linktype_schema, #não encontrei no MEC011
    },
    "required": ["self"],
    "additionalProperties": False,
}

mecservicemgmtapisubscriptionlinklist_schema = {
    "type": "object",
    "properties": {"_links": links_schema},
    "required": ["_links"],
    "additionalProperties": False,
}

categoryref_schema = {
    "type": "object",
    "properties": {
        "href": {"type": "string"},
        "id": {"type": "string"},
        "name": {"type": "string"},
        "version": {"type": "string"},
    },
    "required": ["href", "id", "name", "version"],
    "additionalProperties": False,
}

# This approach is weird but "additionalProperties" wasn't cutting it and neither was required which forced
# one of the mutually exclusive but not required methods to be present
# the dependentschema might also fix this issue should be, if time allows, checked in the future

filteringcriteria_schema = {
    "type": "object",
    "properties": {
        "states": {
            "type": "array",
            "items": {"type": "string", "enum": ["ACTIVE", "INACTIVE", "SUSPENDED"]},
        },
        "isLocal": {"type": "boolean"},
        "serNames": {"type": "array", "items": {"type": "string"}},
        "serInstanceIds": {"type": "array", "items": {"type": "string"}},
        "serCategories": {"type": "array", "items": categoryref_schema},
    },
    "oneOf": [
        {
            "not": {
                "anyOf": [
                    {"required": ["serNames", "serInstancesId", "serCategories"]},
                ]
            }
        },
        {"required": ["serNames", "serInstanceIds", "serCategories"]},
    ],
    "additionalProperties": False,
}


seravailabilitynotificationsubscription_schema = {
    "type": "object",
    "properties": {
        "subscriptionType": {"type": "string"},
        "callbackReference": {"type": "string"},
        "_links": links_schema, #changed
        "filteringCriteria": filteringcriteria_schema,
    },
    "additionalProperties": False,
    "required": ["callbackReference"],
}
oauth2info_schema = {
    "type": "object",
    "properties": {
        "grantTypes": {
            "type": "array",
            "items": {
                "enum": [
                    "OAUTH2_AUTHORIZATION_CODE",
                    "OAUTH2_IMPLICIT_GRANT",
                    "OAUTH2_RESOURCE_OWNER",
                    "OAUTH2_CLIENT_CREDENTIALS",
                ]
            },
            "uniqueItems": True,
            "minItems": 1,
            "maxItems": 4,
        },
        "tokenEndpoint": {"type": "string"},
    },
    "required": ["grantTypes"],
    "additionalProperties": False,
}

securityinfo_schema = {
    "type": "object",
    "properties": {"oAuth2Info": oauth2info_schema},
    "required": ["oAuth2Info"],
    "additionalProperties": False,
}

endpointinfo_address_schema = {
    "type": "object",
    "properties": {"host": {"type": "string"}, "port": {"type": "integer"}},
    "required": ["host", "port"],
    "additionalProperties": False,
}

endpointinfo_addresses_schema = {
    "type": "object",
    "properties": {
        "addresses": {
            "type": "array",
            "items": endpointinfo_address_schema,
            "minItems": 1,
        }
    },
    "required": ["addresses"],
    "additionalProperties": False,
}

endpointinfo_uris_schema = {
    "type": "object",
    "properties": {
        "uris": {"type": "array", "items": {"type": "string"}, "minItems": 1}
    },
    "required": ["uris"],
    "additionalProperties": False,
}

implSpecificInfo_schema = {
    "type": "object",
    "properties": {"description": {"type": "string"}},
    "additionalProperties": False,
}

transportinfo_schema = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "name": {"type": "string"},
        "type": {
            "enum": [
                "REST_HTTP",
                "MB_TOPIC_BASED",
                "MB_ROUTING",
                "MB_PUBSUB",
                "RPC",
                "RPC_STREAMING",
                "WEBSOCKET",
            ]
        },
        "version": {"type": "string"},
        "endpoint": {
            "oneOf": [endpointinfo_addresses_schema, endpointinfo_uris_schema]
        },
        "security": securityinfo_schema,
        "description": {"type": "string"},
        "implSpecificInfo": implSpecificInfo_schema,
        "protocol": {"type": "string"},
    },
    "required": ["id", "name", "type", "protocol", "version", "endpoint", "security"],
    "additionalProperties": False,
}

serviceinfo_schema = {
    "type": "object",
    "properties": {
        "version": {"type": "string"},
        "transportInfo": transportinfo_schema,
        "serializer": {"enum": ["JSON", "XML", "PROTOBUF3"]},
        "livenessInterval": {"type": "integer"},
        "consumedLocalOnly": {"type": "boolean"},
        "isLocal": {"type": "boolean"},
        "scopeOfLocality": {
            "enum": [
                "MEC_SYSTEM",
                "MEC_HOST",
                "NFVI_POP",
                "ZONE",
                "ZONE_GROUP",
                "NFVI_NODE",
            ]
        },
        "state": {"enum": ["ACTIVE", "INACTIVE", "SUSPENDED"]},
        "serName": {"type": "string"},
        "serCategory": categoryref_schema,
    },
    "required": ["version", "state", "serializer", "serName"],
    "additionalProperties": False,
}

appreadyconfirmation_schema = {
    "type": "object",
    "properties": {"indication": {"type": "string"}},
    "required": ["indication"],
    "additionalProperties": False,
}

appterminationconfirmation_schema = {
    "type": "object",
    "properties": {
        "operationAction": {
            "enum": [
                "STOPPING",
                "TERMINATING"
                ]
        }
    },
    "required": ["operationAction"],
    "additionalProperties": False,
}

appTerminationNotificationSubscription_schema = {
    "type": "object",
    "properties": {
        "subscriptionType": {"type": "string"},
        "callbackReference": {"type": "string"},
        "_links": links_schema,
        "appInstanceId": {"type": "string"},
    },
    "additionalProperties": False,
    "required": ["subscriptionType","callbackReference","appInstanceId"],
}

service_get_schema = {
    "type": "object",
    "properties": {
        "serInstanceId": {"type": "string"},
        "serName": {"type": "string"},
        "serCategory": {"type": "string"}, #just the ser_category_id
        "scopeOfLocality": {
            "enum": [
                "MEC_SYSTEM",
                "MEC_HOST",
                "NFVI_POP",
                "ZONE",
                "ZONE_GROUP",
                "NFVI_NODE",
            ]
        },
        "consumedLocalOnly": {"type": "boolean"},
        "isLocal": {"type": "boolean"} 
    },
    "dependentSchemas": {
        "serInstanceId": {
            "not": {"required": ["serName"]}
            },
        "serName": {
            "not": {"required": ["serCategory"]}
            },
        "serCategory": {
            "not": {"required": ["serInstanceId"]}
            }
    },
    "additionalProperties": False,
}

dns_rule_schema = {
    "type": "object",
    "properties": {
        "dnsRuleId": {"type": "string"},
        "domainName": {"type": "string"},
        "ipAddressType": {
            "enum": [
                "IP_V6",
                "IP_V4"
                ]
        },
        "ipAddress": {"type": "string"},
        "ttl": {"type": "integer"},
        "state": {
            "enum": [
                "ACTIVE",
                "INACTIVE"
                ]
        }
    },
    "required": ["dnsRuleId", "domainName", "ipAddressType", "state"],
    "additionalProperties": False,
}

dns_rule_put_schema = {
    "type": "object",
    "properties": {
        "dnsRuleId": {"type": "string"},
        "domainName": {"type": "string"},
        "ipAddressType": {
            "enum": [
                "IP_V6",
                "IP_V4"
                ]
        },
        "ipAddress": {"type": "string"},
        "ttl": {"type": "integer"},
        "state": {
            "enum": [
                "ACTIVE",
                "INACTIVE"
                ]
        }
    },
    "anyOf": [
        {"required": ["dnsRuleId"]},
        {"required": ["domainName"]},
        {"required": ["ipAddressType"]},
        {"required": ["ipAddress"]},
        {"required": ["ttl"]},
        {"required": ["state"]}
    ],
    "additionalProperties": False,
}

current_time_schema = {
    "type": "object",
    "properties": {
        "seconds": {"type": "integer"},
        "nanoseconds": {"type": "integer"},
        "timeSourceStatus": {
            "enum": [
                "TRACEABLE",
                "NONTRACEABLE"
                ]
        }
    },
    "required": ["seconds", "nanoseconds", "timeSourceStatus"],
    "additionalProperties": False,
}

timeStamp_schema = {
    "type": "object",
    "properties": {
        "seconds": {"type": "integer"},
        "nanoseconds": {"type": "integer"}
    },
    "required": ["seconds", "nanoseconds"],
    "additionalProperties": False,
}

serviceLivenessInfo_schema = {
    "type": "object",
    "properties": {
        "state": {
            "enum": [
                "ACTIVE",
                "INACTIVE",
                "SUSPENDED"
            ]
        },
        "timeStamp": timeStamp_schema,
        "interval": {"type": "integer"}
    },
    "required": ["state", "timeStamp", "interval"],
    "additionalProperties": False,
}

serviceLivenessUpdate_schema = {
    "type": "object",
    "properties": {
        "state": {
            "enum": [
                "ACTIVE",
                "INACTIVE",
                "SUSPENDED"
            ]
        }
    },
    "required": ["state"],
    "additionalProperties": False,
}


trafficFilter_schema = {
    "type": "object",
    "properties": {
        "srcAddress": {
            "type": "array",
            "items": {"type": "string"},
        },
        "dstAddress": {
            "type": "array",
            "items": {"type": "string"},
        },
        "srcPort": {
            "type": "array",
            "items": {"type": "string"},
        },        
        "dstPort": {
            "type": "array",
            "items": {"type": "string"},
        },
        "protocol": {
            "type": "array",
            "items": {"type": "string"},
        },
        "tag": {
            "type": "array",
            "items": {"type": "string"},
        },
        "srcTunnelAddress": {
            "type": "array",
            "items": {"type": "string"},
        },
        "tgtTunnelAddress": {
            "type": "array",
            "items": {"type": "string"},
        },
        "srcTunnelPort": {
            "type": "array",
            "items": {"type": "string"},
        },
        "dstTunnelPort": {
            "type": "array",
            "items": {"type": "string"},
        },
        "qCI": {"type": "integer"},
        "dSCP": {"type": "integer"},
        "tC": {"type": "integer"},
    },
    "required": [],
    "additionalProperties": False,
}

tunnelInfo_schema = {
    "type": "object",
    "properties": {
        "tunnelType": {
            "enum":[
                "GTP_U",
                "GRE"
            ]
        },
        "tunnelDstAddress": {"type": "string"},
        "tunnelSrcAddress": {"type": "string"},
    },
    "required": ["tunnelType"],
    "additionalProperties": False,
}

destinationInterface_schema = {
    "type": "object",
    "properties": {
        "interfaceType": {
            "enum":[
                "TUNNEL",
                "MAC",
                "IP"
            ]
        },
        "tunnelInfo": tunnelInfo_schema,
        "srcMacAddress": {"type": "string"},
        "dstMacAddress": {"type": "string"},
        "dstIpAddress": {"type": "string"},
    },
    "required": ["interfaceType"],
    "additionalProperties": False,
}


trafficRule_schema = {
    "type": "object",
    "properties": {
        "trafficRuleId": {"type": "string"},
        "filterType": {
            "enum":[
                "FLOW",
                "PACKET"
            ]
        },
        "priority": {"type": "integer"},
        "trafficFilter": {
            "type": "array",
            "items": trafficFilter_schema,
            "minItems": 1
        },
        "action": {
            "enum": [
                "DROP",
                "FORWARD_DECAPSULATED",
                "FORWARD_ENCAPSULATED",
                "PASSTHROUGH",
                "DUPLICATE_DECAPSULATED",
                "DUPLICATE_ENCAPSULATED"
            ]
        },
        "dstInterface": {
            "type": "array",
            "items": destinationInterface_schema,
            "maxItems": 2
        },
        "state": {
            "enum": [
                "ACTIVE",
                "INACTIVE"
            ]
        }
    },
    "required": ["trafficRuleId", "filterType", "priority", "trafficFilter", "action", "state"],
    "additionalProperties": False,
}

trafficRuleDescriptor_schema = {
    "type": "object",
    "properties": {
        "trafficRuleId": {"type": "string"},
        "filterType": {
            "enum":[
                "FLOW",
                "PACKET"
            ]
        },
        "priority": {"type": "integer"},
        "trafficFilter": {
            "type": "array",
            "items": trafficFilter_schema,
            "minItems": 1
        },
        "action": {
            "enum": [
                "DROP",
                "FORWARD_DECAPSULATED",
                "FORWARD_ENCAPSULATED",
                "PASSTHROUGH",
                "DUPLICATE_DECAPSULATED",
                "DUPLICATE_ENCAPSULATED"
            ]
        },
        "dstInterface": {
            "type": "array",
            "items": destinationInterface_schema,
            "maxItems": 2
        }
    },
    "required": ["trafficRuleId", "filterType", "priority", "trafficFilter", "action", "state"],
    "additionalProperties": False,
}

changeAppInstanceState_schema = {
    "type": "object",
    "properties": {
        "appInstanceId": {"type": "string"},
        "changeStateTo": {
            "enum":[
                "STARTED",
                "STOPPED"
            ]
        },
        "stopType": {
            "enum":[
                "FORCEFUL",
                "GRACEFUL"
            ]
        },
        "gracefulStopTimeout": {"type": "integer"} 
    },
    "required": ["appInstanceId", "changeStateTo"],
    "aditionalProperties": False,
}

terminateAppInstance_schema = {
    "type": "object",
    "properties": {
        "appInstanceId": {"type": "string"},
        "terminationType": {
            "enum":[
                "FORCEFUL",
                "GRACEFUL"
            ]
        },
        "gracefulStopTimeout": {"type": "integer"} 
    },
    "required": ["appInstanceId", "terminationType"],
    "aditionalProperties": False,
}

# New schemas for MM5 and MM3*

transportDescriptor_schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "description": {"type": "string"},
        "type": {
            "enum": [
                "REST_HTTP",
                "MB_TOPIC_BASED",
                "MB_ROUTING",
                "MB_PUBSUB",
                "RPC",
                "RPC_STREAMING",
                "WEB_SOCKET"
            ]
        },
        "protocol": {"type": "string"},
        "version": {"type": "string"},
        "security": securityinfo_schema,
        "implSpecificInfo": {"type": "string"}
    },
    "required": ["name", "type", "protocol", "version", "security"],
    "additionalProperties": False,
}


transports_schema = {
    "type": "object",
    "properties": {
        "transport": transportDescriptor_schema,
        "serializers": {
            "type": "array",
            "items": {
                "enum": [
                    "JSON",
                    "XML",
                    "PROTOBUF3"
                ]
            }
        }
    },
    "required": ["transport", "serializers"],
    "additionalProperties": False,
}


transportDependency_schema = {
    "type": "object",
    "properties": {
        "transport": transportDescriptor_schema,
        "serializers": {
            "type": "array",
            "items": {
                "enum": [
                    "JSON",
                    "XML",
                    "PROTOBUF3"
                ]
            }
        },
        "labels": {"type": "array", "items": {"type": "string"}}
    },
    "required": ["transport", "serializers", "labels"],
    "additionalProperties": False,
}


serviceDependency_schema = {
    "type": "object",
    "properties": {
        "serName": {"type": "string"},
        "serCategory": categoryref_schema,
        "version": {"type": "string"},
        "serTransportDependencies": {"type": "array", "items": transportDependency_schema},
        "requestedPermissions": {"type": "array", "items": {"type": "string"}}
    },
    "required": ["serName", "version"],
    "additionalProperties": False,
}


featureDependency_schema = {
    "type": "object",
    "properties": {
        "featureName": {"type": "string"},
        "version": {"type": "string"}
    },
    "required": ["featureName", "version"],
    "additionalProperties": False,
}


userContextTransferCapility_schema = {
    "type": "object",
    "properties": {
        "statefulApplication": {"type": "boolean"},
        "userContextTransferSupport": {"type": "boolean"}
    },
    "required": ["statefulApplication"],
    "additionalProperties": False,
}


steeringPolicy_schema = {
    "type": "object",
    "properties": {
        "cellularNetwork": {"type": "boolean"},
        "wifiNetwork": {"type": "boolean"},
        "fixedAccessNetwork": {"type": "boolean"},
    },
    "required": [],
    "additionalProperties": False,
}


appNetworkPolicy_schema = {
    "type": "object",
    "properties": {
        "steeredNetwork": steeringPolicy_schema,
    },
    "required": ["steeredNetwork"],
    "additionalProperties": False,
}


serviceDescriptor_schema = {
    "type": "object",
    "properties": {
        "serName": {"type": "string"},
        "serCategory": categoryref_schema,
        "version": {"type": "string"},
        "transportsSupported": {"type": "array", "items": transports_schema}
    },
    "required": ["serName", "version"],
    "additionalProperties": False,
}