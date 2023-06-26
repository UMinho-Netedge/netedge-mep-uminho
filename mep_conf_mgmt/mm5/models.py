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

from __future__ import annotations
from os import times
import string
from typing import List, Union
from jsonschema import validate
import cherrypy
from urllib import request, parse
from .utils import *
from .enums import *
from .mepm_exceptions import *
from .schemas import *
from uuid import UUID
import requests

import pprint # Dictionaries pretty print (for testing)

####################################
# Classes used by both support and #
# management api                   #
####################################
class LinkType:
    """
    This type represents a type of link and may be referenced from data structures.
    Raises TypeError
    Section 6.3.2 - MEC 011
    """

    def __init__(self, href: str):
        self.href = href

    def to_json(self):
        return dict(href=self.href)


class ProblemDetails:
    def __init__(self, type: str, title: str, status: int, detail: str, instance: str):
        """
        :param type: A URI reference according to IETF RFC 3986 that identifies the problem type
        :param title: A short, human-readable summary of the problem type
        :param status: The HTTP status code for this occurrence of the problem
        :param detail: A human-readable explanation specific to this occurrence of the problem
        :param instance: A URI reference that identifies the specific occurrence of the problem
        """
        self.type = type
        self.title = title
        self.status = status
        self.detail = detail
        self.instance = instance

    def to_json(self):
        return dict(
            type=self.type,
            title=self.title,
            status=self.status,
            detail=self.detail,
            instance=self.instance,
        )


####################################
# Classes used by management api   #
####################################
class Subscription:
    """
    The MEC application instance's subscriptions.
    Section 6.2.2
    """

    def __init__(
            self,
            href: str,
            subscriptionType: Union[str, None] = "SerAvailabilityNotificationSubscription",
    ):
        """
        :param href: URI referring to the subscription. (isn't a real URI but the path to something in our MEP)
        :type href: str
        :param subscriptionType: Type of the subscription.
        :type subscriptionType: str
        Raises TypeError
        """
        self.href = href
        self.subscriptionType = subscriptionType

    def to_json(self):
        return ignore_none_value(
            dict(href=self.href, subscriptionType=self.subscriptionType)
        )


class Links:
    """
    Internal structure to be compliant with MEC 011
    Section 6.2.2
    """

    def __init__(
            self,
            _self: LinkType = None,
            subscriptions: List[Subscription] = None,
            liveness: LinkType = None,
    ):
        self.self = _self
        self.subscriptions = subscriptions
        self.liveness = liveness

    @staticmethod
    def from_json(data: dict) -> Links:
        validate(instance=data, schema=links_schema)
        _self = LinkType(data["self"]["href"])
        subscriptions = None
        if "subscriptions" in data and len(data["subscriptions"]) > 0:
            # cherrypy.log(json.dumps(data["subscriptions"]))
            subscriptions = [
                Subscription(**subscription) for subscription in data["subscriptions"]
            ]
        liveness = None
        if "liveness" in data:
            liveness = LinkType(data["liveness"]["href"])

        return Links(_self=_self, subscriptions=subscriptions, liveness=liveness)

    def to_json(self):
        return ignore_none_value(
            dict(
                self=self.self, subscriptions=self.subscriptions, liveness=self.liveness
            )
        )


class MecServiceMgmtApiSubscriptionLinkList:
    """
    This type represents a list of links related to currently existing subscriptions for a MEC application instance.
    This information is returned when sending a request to receive current subscriptions.
    Section 6.2.2 - MEC 011
    """

    def __init__(self, _links: Links):
        self._links = _links

    @staticmethod
    def from_json(data: dict) -> MecServiceMgmtApiSubscriptionLinkList:
        # First validate the json via jsonschema
        validate(instance=data, schema=mecservicemgmtapisubscriptionlinklist_schema)
        _links = Links.from_json(data["_links"])
        return MecServiceMgmtApiSubscriptionLinkList(_links=_links)

    def to_json(self):
        return dict(_links=self._links)


class CategoryRef:
    def __init__(self, href: str, id: str, name: str, version: str):
        """
        This type represents the category reference.
        :param href: Reference of the catalogue.
        :type href: String
        :param id: Unique identifier of the category.
        :type id: String
        :param name: Name of the category.
        :type name: String
        :param version: Category version.
        :type version: String
        Raises TypeError
        Section 8.1.5.2
        """
        self.href = validate_uri(href)
        self.id = id
        self.name = name
        self.version = version

    @staticmethod
    def from_json(data: dict) -> CategoryRef:
        validate(instance=data, schema=categoryref_schema)
        return CategoryRef(**data)

    def to_json(self):
        # All required none should have value none thus there is no need to use ignore_none_val
        return dict(href=self.href, id=self.id, name=self.name, version=self.version)

    

class FilteringCriteria:
    def __init__(
            self,
            states: List[ServiceState],
            isLocal: bool,
            serInstanceIds: List[str] = None,
            serNames: List[str] = None,
            serCategories: List[CategoryRef] = None,
    ):
        """
        :param states: States of the services about which to report events. If the event is a state change, this filter represents the state after the change
        :type states: List[ServiceState]
        :param isLocal: Restrict event reporting to whether the service is local to the MEC platform where the subscription is managed.
        :type isLocal: Boolean
        :param serInstanceIds: Identifiers of service instances about which to report events
        :type serInstanceIds: String
        :param serNames: Names of services about which to report events
        :type serNames: String
        :param serCategories: Categories of services about which to report events.
        :type serCategories: List of CategoryRef
        Note serCategories, serInstanceId and serNames are mutually-exclusive
        Raises KeyError when Invalid Enum is provided
        Raises InvalidIdentifier if no identifier is specified
        Section 8.1.3.2
        """
        self.states = states
        self.isLocal = isLocal
        self.serInstanceIds = serInstanceIds
        self.serNames = serNames
        self.serCategories = serCategories

    @staticmethod
    def from_json(data: dict) -> FilteringCriteria:
        validate(instance=data, schema=filteringcriteria_schema)
        tmp_states = data.pop("states", None)
        if tmp_states == None:
            states = None
        else:
            states = [ServiceState[state] for state in tmp_states]
        isLocal = data.pop("isLocal", None)

        # Since only one is acceptable start all as none and then set only the one presented in the data
        # the validation from json schema deals with the mutually exclusive part
        identifier_data = {
            "serCategories": None,
            "serNames": None,
            "serInstanceIds": None,
        }
        if "serCategories" in data:
            identifier_data["serCategories"] = [
                CategoryRef(**category) for category in data["serCategories"]
            ]
        elif "serNames" in data:
            identifier_data["serNames"] = data["serNames"]
        elif "serInstanceIds" in data:
            identifier_data["serInstanceIds"] = data["serInstanceId"]

        # The object is created from the two known variables and from the dictionary setting only one identifier data
        return FilteringCriteria(states=states, isLocal=isLocal, **identifier_data)

    def to_json(self):
        return ignore_none_value(
            dict(
                states=self.states,
                isLocal=self.isLocal,
                serInstanceIds=self.serInstanceIds,
                serNames=self.serNames,
                serCategories=self.serCategories,
            )
        )

    def to_query(self):
        """
        Different from to_json because it uses singular names instead of plural ones
        This is due to the fact that the filtering criteria is made with plural names while
        services in the database stores things in singular
        """
        return ignore_none_value(
            dict(
                state=self.states,
                isLocal=self.isLocal,
                serInstanceId=self.serInstanceIds,
                serName=self.serNames,
                serCategorie=self.serCategories,
            )
        )


class ServiceAvailabilityNotification:
    def __init__(
            self,
            serviceReferences: List[ServiceReferences],
            _links: Subscription,
            notificationType: str = "SerAvailabilityNotificationSubscription",
    ):
        """
        :param serviceReferences: List of links to services whose availability has changed.
        :type serviceReferences: List of ServiceReferences
        :param _links: Object containing hyperlinks related to the resource.
                        Can be None (Temporarly) in the case of a new service where the data is added during callback
        :type _links: Subscription
        :param notificationType: hall be set to "SerAvailabilityNotification"
        :type notificationType: String
        Section 8.1.4.2
        """
        self.notificationType = notificationType
        self.serviceReferences = serviceReferences
        self._links = _links

    class ServiceReferences:
        def __init__(
                self,
                link: LinkType,
                serInstanceId: str,
                state: ServiceState,
                serName: str,
                changeType: ChangeType,
        ):
            self.link = link
            self.serInstanceId = serInstanceId
            self.serName = serName
            self.state = state
            self.changeType = changeType

        @staticmethod
        def from_json(data: dict):
            """
            :param data: Data used to generate a ServiceReference
            :type data: JSON / Python Dict
            :return: ServiceReference
            """
            # Link is weird - ETSI overall structure for the _link type is really confusing
            link = LinkType(data.get("_links").get("liveness").get("href"))
            serInstanceId = data.get("serInstanceId")
            state = data.get("state")
            serName = data.get("serName")
            changeType = ChangeType(data.get("changeType"))
            return ServiceAvailabilityNotification.ServiceReferences(
                link=link,
                serInstanceId=serInstanceId,
                state=state,
                serName=serName,
                changeType=changeType,
            )

        def to_json(self):
            return dict(
                link=self.link,
                serInstanceId=self.serInstanceId,
                serName=self.serName,
                state=self.state,
                changeType=self.changeType,
            )

    @staticmethod
    def from_json_service_list(
            data: list[dict], changeType: str, subscription: str = None
    ):
        """
        :param data: List containing all services (in json form) that match the filtering criteria
        :type data: JSON / Python dictionary
        :param subscription: URL referencing the subscription resource
        :type subscription: String
        :param changeType: Type of the change being sent to the subscriber
        :type changeType: ChangeType
        :return: ServiceAvailabilityNotification
        """
        if subscription:
            _links = Subscription(href=subscription, subscriptionType=None)
        else:
            _links = None
        serviceReferences = []

        for service in data:
            service["changeType"] = changeType
            tmpReference = ServiceAvailabilityNotification.ServiceReferences.from_json(
                data=service
            )
            serviceReferences.append(tmpReference)
        return ServiceAvailabilityNotification(
            _links=_links, serviceReferences=serviceReferences
        )

    def to_json(self):
        return ignore_none_value(
            dict(
                notificationType=self.notificationType,
                _links=self._links,
                serviceReferences=self.serviceReferences,
            )
        )


class SerAvailabilityNotificationSubscription:
    def __init__(
            self,
            callbackReference: str,
            _links: Links = None,
            filteringCriteria: FilteringCriteria = None,
    ):
        """
        :param callbackReference: URI selected by the MEC application instance to receive notifications on the subscribed MEC service availability information. This shall be included in both the request and the response.".
        :type callbackReference: String
        :param _links: Object containing hyperlinks related to the resource. This shall only be included in the HTTP responses.
        :type _links: str (String is validated to be a correct URI)
        :param filteringCriteria: Filtering criteria to match services for which events are requested to be reported. If absent, matches all services. All child attributes are combined with the logical "AND" operation.
        :type filteringCriteria: FilteringCriteria
        Raises TypeError
        Section 8.1.3.2
        """
        self.callbackReference = validate_uri(callbackReference)
        self._links = _links
        self.filteringCriteria = filteringCriteria
        self.subscriptionType = "SerAvailabilityNotificationSubscription"
        """
        AppInstanceId and subscriptionId are only used internally to deal with callbacks
        """
        self.appInstanceId = None
        self.subscriptionId = None

    @staticmethod
    def from_json(data: dict) -> SerAvailabilityNotificationSubscription:
        # validate the json via jsonschema
        validate(instance=data, schema=seravailabilitynotificationsubscription_schema)
        # FilteringCriteria is not a required request body parameter
        # Using {} instead of None is due to the fact that if nothing is passed it is supposed to match everything
        # this makes it easier to query this edge case in the database
        filteringCriteria = {}
        if "filteringCriteria" in data:
            filteringCriteria = FilteringCriteria.from_json(
                data.pop("filteringCriteria")
            )
        return SerAvailabilityNotificationSubscription(
            filteringCriteria=filteringCriteria, **data
        )

    def to_json(self):
        return ignore_none_value(
            dict(
                callbackReference=self.callbackReference,
                _links=self._links,
                filteringCriteria=self.filteringCriteria,
                subscriptionType=self.subscriptionType,
            )
        )


class OAuth2Info:
    def __init__(self, grantTypes: List[GrantTypes], tokenEndpoint: str):
        """
        This type represents security information related to a transport.
        :param grantTypes: List of supported OAuth 2.0 grant types
        :type grantTypes: List[GrantTypes] Min size 1 Max Size 4
        :param tokenEndpoint: The Token Endpoint
        :type tokenEndpoint: String
        :Note: grantTypes can be between 1 and 4
        :Note: tokenEndpoint seems required in swagger but isn't in MEC011 Specification
        Section 8.1.5.4
        Raises InvalidGrantType
        """
        self.grantTypes = grantTypes
        self.tokenEndpoint = tokenEndpoint

    @staticmethod
    def from_json(data: dict) -> OAuth2Info:
        # list(set()) to ignore possible duplicates from the user
        data["grantTypes"] = list(set(data["grantTypes"]))
        if 1 > len(data["grantTypes"]) > 4:
            raise InvalidGrantType

        grantTypes = [GrantTypes(grantType) for grantType in data.pop("grantTypes")]
        return OAuth2Info(grantTypes=grantTypes, **data)

    def to_json(self):
        return dict(grantTypes=self.grantTypes, tokenEndpoint=self.tokenEndpoint)


class SecurityInfo:
    def __init__(self, oAuth2Info: OAuth2Info = None):
        """
        :param oAuth2Info: Parameters related to use of OAuth 2.0.
        Section 8.1.5.4
        """
        self.oAuth2Info = oAuth2Info

    @staticmethod
    def from_json(data: dict) -> SecurityInfo:
        oAuth2Info = OAuth2Info.from_json(data["oAuth2Info"])
        return SecurityInfo(oAuth2Info=oAuth2Info)

    def to_json(self):
        return dict(oAuth2Info=self.oAuth2Info)


class EndPointInfo:
    """
    Section 8.1.5.3
    """

    class Uris:
        def __init__(self, uris: List[str]):
            """
            :param uri: Entry point information of the service as string, formatted according to URI syntax
            :type uri: String
            Raises TypeError
            """
            self.uris = [validate_uri(uri) for uri in uris]

        def to_json(self):
            return dict(uris=self.uris)

    class Address:
        def __init__(self, host: str, port: int):
            """
            :param host: Host portion of the address.
            :type host: str
            :param port: Port portion of the address.
            :type port: int
            """
            self.host = host
            self.port = port

        def to_json(self):
            return dict(host=self.host, port=self.port)

    class Addresses:
        def __init__(self, addresses: List[object]):
            """
            :param addresses: List of EndPointInfo.Addresses
            :type addresses: List[EndpointInfo.Addresses]
            """
            self.addresses = addresses

        @staticmethod
        def from_json(data: dict) -> EndPointInfo.Addresses:
            addresses = [EndPointInfo.Address(host, port) for host, port in data]
            return EndPointInfo.Addresses(addresses)

        def to_json(self):
            return dict(addresses=self.addresses)

    class Alternative:
        # This EndPointInfo isn't specified in MEC 011
        pass

    @staticmethod
    def from_json(data: dict):
        # Check which EndPointInfo was sent
        # Address
        if "addresses" in data.keys():
            return EndPointInfo.Addresses.from_json(data["addresses"])
        if "uris" in data.keys():
            return EndPointInfo.Uris(uris=data["uris"])


class TransportInfo:
    def __init__(
            self,
            id: str,
            name: str,
            type: TransportType,
            version: str,
            endpoint: Union(EndPointInfo.Addresses, EndPointInfo.Uris, EndPointInfo.Alternative),
            security: SecurityInfo,
            description: str = "",
            implSpecificInfo: str = "",
            protocol: str = "HTTP",
    ):
        """
        :param id: The identifier of this transport.
        :type id: String
        :param name: The name of this transport.
        :type name: String
        :param type: Type of the transport.
        :type type: TransportType
        :param version: The version of the protocol used.
        :type version: String
        :param endpoint: Information about the endpoint to access the transport.
        :type endpoint: EndPointInfo
        :param security: Information about the security used by the transport.
        :type security: SecurityInfo
        :param implSpecificInfo: Additional implementation specific details of the transport.
        :type implSpecificInfo: NotSpecified
        :param protocol: The name of the protocol used. Shall be set to "HTTP" for a REST API.
        :type protocol: String
        :param description: Human-readable description of this transport.
        :type description: String
        Section 8.1.2.3
        """
        self.id = id
        self.name = name
        self.type = type
        self.protocol = protocol
        self.version = version
        self.endpoint = endpoint
        self.security = security
        self.description = description
        self.implSpecificInfo = implSpecificInfo

    @staticmethod
    def from_json(data: dict) -> TransportInfo:
        _type = TransportType(data.pop("type"))
        endpoint = EndPointInfo.from_json(data.pop("endpoint"))
        security = SecurityInfo.from_json(data.pop("security"))
        return TransportInfo(type=_type, endpoint=endpoint, security=security, **data)

    def to_json(self):
        return ignore_none_value(
            dict(
                id=self.id,
                name=self.name,
                type=self.type,
                protocol=self.protocol,
                version=self.version,
                endpoint=self.endpoint,
                security=self.security,
                description=self.description,
                implSpecificInfo=self.implSpecificInfo,
            )
        )


class ServiceInfo:
    def __init__(
        self,
        serName: str,
        version: str,
        state: ServiceState,
        serializer: SerializerType,
        serInstanceId: str = None,
        serCategory: CategoryRef = None,
        transportId: str = None,
        transportInfo: TransportInfo = None,
        scopeOfLocality: LocalityType = LocalityType.MEC_HOST,
        consumedLocalOnly: bool = True,
        isLocal: bool = True,        
        livenessInterval: int = None,
        _links: Links = None,
    ):
        """
        :param serInstanceId: Identifiers of service instances about which to report events
        :type serInstanceId: String
        :param serName: Names of services about which to report events.
        :type serName: String
        :param serCategory: Categories of services about which to report events.
        :type serCategory: String
        :param version: The version of the service.
        :type version: String
        :param state: Contains the service state.
        :type state: String
        :param transportInfo: Identifier of the platform-provided transport to be used by the service.
        :type transportInfo: String
        :param serializer: Indicate the supported serialization format of the service.
        :type serializer: String
        :param scopeOfLocality: The scope of locality as expressed by "consumedLocalOnly" and "isLocal".
        :type scopeOfLocality: LocalityType
        :param consumedLocalOnly: Indicate whether the service can only be consumed by the MEC applications located in the same locality
        :type consumedLocalOnly: Boolean
        :param isLocal: Indicate whether the service is located in the same locality as the consuming MEC application or not
        :type isLocal: Boolean
        :param _links: Links to resources related to this resource
        :type _links: Links
        :param livenessInterval: Interval (in seconds) between two consecutive "heartbeat" messages
        :type livenessInterval: Integer
        Note serCategories, serInstanceId and serNames are mutually-exclusive
        Section 8.1.2.2
        """
        self.serInstanceId = serInstanceId
        self.serName = serName
        self.serCategory = serCategory
        self.version = version
        self.state = state
        self.transportId = transportId
        self.transportInfo = transportInfo
        self.serializer = serializer
        self.scopeOfLocality = scopeOfLocality
        self.consumedLocalOnly = consumedLocalOnly
        self.isLocal = isLocal
        self.livenessInterval = livenessInterval
        self._links = _links

    @staticmethod
    def from_json(data: dict) -> ServiceInfo:
        # Validate the json via jsonschema
        validate(instance=data, schema=serviceinfo_schema)
        identifier_data = {}
        categoryref = data.pop("serCategory", None)
        if categoryref is not None:
            identifier_data["serCategory"] = CategoryRef(**categoryref)
        identifier_data["serName"] = data.pop("serName", None)

        # Each required element or element that can't be automatically generated from the unpacking is popped
        # to avoid having the function received the element twice and throwing an exception
        state = ServiceState(data.pop("state"))
        transportInfo = TransportInfo.from_json(data.pop("transportInfo"))
        serializer = SerializerType(data.pop("serializer"))
        scopeOfLocality = None
        if "scopeOfLocality" in data.keys():
            scopeOfLocality = LocalityType(data.pop("scopeOfLocality"))

        return ServiceInfo(
            state=state,
            transportInfo=transportInfo,
            serializer=serializer,
            scopeOfLocality=scopeOfLocality,
            **data,
            **identifier_data,
        )

    def to_json(self):
        return ignore_none_value(
            dict(
                version=self.version,
                serInstanceId=self.serInstanceId,
                serName=self.serName,
                serCategory=self.serCategory,
                serializer=self.serializer,
                _links=self._links,
                scopeOfLocality=self.scopeOfLocality,
                transportInfo=self.transportInfo,
                state=self.state,
                livenessInterval=self.livenessInterval,
                consumedLocalOnly=self.consumedLocalOnly,
                isLocal=self.isLocal,
            )
        )

    def to_filtering_criteria_json(self):
        """
        Used with the $or mongodb operator which requires a list of dictionaries for each "or" operation
        Example we want to get an object that can have serName="a" or serInstanceId="b"
        {$or:[{"serName":a},{"serInstanceId":"b"}]}
        Due to serInstancesIds,serNames,serCategories and states being addressable by various values we transform
        them into a list so that we can use the $in operator
        """
        tmp_ret = ignore_none_value(
            dict(
                serInstanceIds=[self.serInstanceId],
                serNames=[self.serName],
                serCategories=[self.serCategory],
                states=[self.state],
                isLocal=self.isLocal,
            )
        )

        return {
            "$and": [
                {
                    "$or": [
                        {f"filteringCriteria.{key}": {"$exists": False}},
                        {f"filteringCriteria.{key}": val},
                    ]
                }
                for key, val in list(tmp_ret.items())
            ]
        }


class ServiceGet:
    def __init__(
        self,
        ser_instance_id: List[str] = None,
        ser_name: List[str] = None,
        ser_category_id: str = '',
        scope_of_locality: LocalityType = LocalityType.MEC_HOST,
        consumed_local_only: bool = None,
        is_local: bool = None,
    ):
        """
        :param ser_instance_id: A MEC application instance may use multiple ser_instance_ids as an input parameter to query the availability of a list of MEC service instances. Either "ser_instance_id" or "ser_name" or "ser_category_id" or none of them shall be present.
        :type ser_instance_id: List[String]
        :param ser_name: A MEC application instance may use multiple ser_names as an input parameter to query the availability of a list of MEC service instances. Either "ser_instance_id" or "ser_name" or "ser_category_id" or none of them shall be present.
        :type ser_name: List[String]
        :param ser_category_id: A MEC application instance may use ser_category_id as an input parameter to query the availability of a list of MEC service instances in a serCategory. Either "ser_instance_id" or "ser_name" or "ser_category_id" or none of them shall be present.
        :type ser_category_id: String
        :param consumed_local_only: Indicate whether the service can only be consumed by the MEC applications located in the same locality (as defined by scopeOfLocality) as this service instance.
        :type consumed_local_only: boolean
        :param is_local: Indicate whether the service is located in the same locality (as defined by scopeOfLocality) as the consuming MEC application.
        :type is_local: boolean
        :param scope_of_locality: A MEC application instance may use scope_of_locality as an input parameter to query the availability of a list of MEC service instances with a certain scope of locality.
        :type scope_of_locality: String

        :note: ser_name, ser_category_id, ser_instance_id are mutually-exclusive only one should be used or none

        Raises ValidationError when invalid type is provided or mutual-exclusion failed
        Section 8.2.3.3.1
        """
        self.ser_instance_id = ser_instance_id
        self.ser_name = ser_name
        self.ser_category_id = ser_category_id
        self.scope_of_locality = scope_of_locality
        self.consumed_local_only = consumed_local_only
        self.is_local = is_local

    def __str__(self):
        return "\nser_instance_id: "+str(self.ser_instance_id)+ \
                "\nser_name: "+str(self.ser_name)+ \
                "\nser_category_id: "+str(self.ser_category_id)+ \
                "\nscope_of_locality: "+str(self.scope_of_locality)+ \
                "\nconsumed_local_only: "+str(self.consumed_local_only)+ \
                "\nis_local: "+str(self.is_local)
    
    def to_json(self):
        return ignore_none_value(
                    dict(
                        ser_instance_id=self.ser_instance_id,
                        ser_name=self.ser_name,
                        ser_category_id=self.ser_category_id,
                        scope_of_locality=self.scope_of_locality,
                        consumed_local_only=self.consumed_local_only,
                        is_local=self.is_local
                    )
                )

    def to_query(self):

        #bool_converter = {"true": True, "false": False, None: None}
        
        def bool_conv(att_value: str):
            if att_value == "true":
                return True
            if att_value == "false":
                return False
            return att_value

        query = dict(
            serInstanceId=self.ser_instance_id,
            serName=self.ser_name,
            serCategory=self.ser_category_id,
            scopeOfLocality=self.scope_of_locality,
            consumedLocalOnly=bool_conv(self.consumed_local_only),
            isLocal=bool_conv(self.is_local)
        )

        query = ignore_none_value(query)
        validate(instance=query, schema=service_get_schema)

        # Search for 'id' in the nested structure serCategory
        if self.ser_category_id is not None:
            query['serCategory.id'] = query.pop('serCategory')
        
        if self.ser_instance_id is not None:
            query['serInstanceId'] = query['serInstanceId'].split(",")
        if self.ser_name is not None:
            query['serName'] = query['serName'].split(",")

        return query

    def __str__(self):
        return "\nser_instance_id: "+str(self.ser_instance_id)+ \
                "\nser_name: "+str(self.ser_name)+ \
                "\nser_category_id: "+str(self.ser_category_id)+ \
                "\nscope_of_locality: "+str(self.scope_of_locality)+ \
                "\nconsumed_local_only: "+str(self.consumed_local_only)+ \
                "\nis_local: "+str(self.is_local)


class DnsRule:
    def __init__(
        self,
        dnsRuleId: str = None,
        domainName: str = None,
        ipAddressType: IpAddressType = None,
        ipAddress: str = None,
        ttl: int = None,
        state: StateType = None,
        ):

        self.dnsRuleId = dnsRuleId
        self.domainName = domainName
        self.ipAddressType = ipAddressType
        self.ipAddress = ipAddress
        self.ttl = ttl
        self.state = state

    @staticmethod
    def from_json(data: dict, schema=dns_rule_schema) -> DnsRule:
        # Validate the json via json schema
        validate(instance=data, schema=schema)
        
        kwargs = {}
        for attribute in data.keys():
            if attribute == "ipAddressType":
                kwargs['ipAddressType'] = IpAddressType(data["ipAddressType"])
            elif attribute == "ttl":
                kwargs['ttl'] = int(data["ttl"])
            elif attribute == "state":
                kwargs['state'] = StateType(data["state"])
            else:
                kwargs[attribute] = data[attribute]
        
        return DnsRule(**kwargs)


    def to_json(self):
        return ignore_none_value(
            dict(
                dnsRuleId = self.dnsRuleId,
                domainName = self.domainName,
                ipAddressType = self.ipAddressType.name if self.ipAddressType is not None else None,
                ipAddress = self.ipAddress,
                ttl = self.ttl,
                state = self.state.name if self.state is not None else None,
                )
            )
    
    def __str__(self):
        return str(self.ipAddressType)


####################################
# Classes used by support api      #
####################################

# In theory this class doesn't need to exist but since ETSI defined a post request body
# it may be useful in the future (i.e new indications etc...)
class AppReadyConfirmation:
    def __init__(self, indication: IndicationType):
        self.indication = indication

    @staticmethod
    def from_json(data: dict) -> AppReadyConfirmation:
        # Validate the json via json schema
        validate(instance=data, schema=appreadyconfirmation_schema)
        indication = IndicationType(data["indication"])
        return AppReadyConfirmation(indication=indication)

    def to_json(self):
        return ignore_none_value(dict(indication=self.indication))


# In theory this class doesn't need to exist but since ETSI defined a post request body
# it may be useful in the future (i.e new indications etc...)
class AppTerminationConfirmation:
    def __init__(self, operationAction: OperationActionType):
        self.operationAction = operationAction

    @staticmethod
    def from_json(data: dict) -> AppTerminationConfirmation:
        # Validate the json via json schema
        validate(instance=data, schema=appterminationconfirmation_schema)
        operationAction = OperationActionType(data["operationAction"])
        return AppTerminationConfirmation(operationAction=operationAction)

    def to_json(self):
        return ignore_none_value(dict(operationAction=self.operationAction))
    
    def __str__(self):
        return str(self.operationAction)

class AppTerminationNotificationSubscription:
    def __init__(self, callbackReference: str, _links: Links, appInstanceId: str, subscriptionType: str = "AppTerminationNotificationSubscription"):
        self.subscriptionType = subscriptionType
        self.callbackReference = callbackReference
        self._links = _links
        self.appInstanceId = appInstanceId

    def from_json(data: dict):
        validate(instance=data, schema=appTerminationNotificationSubscription_schema)
        callbackReference = data.pop("callbackReference")
        appInstanceId = data.pop("appInstanceId")
        subscriptionType = data.pop("subscriptionType")
        try:
            _links = Links.from_json(data["_links"])
        except KeyError:
            _links = None

        return AppTerminationNotificationSubscription(
            callbackReference=callbackReference,
            _links=_links,
            appInstanceId=appInstanceId,
            subscriptionType=subscriptionType
            )

    def to_json(self):
        return ignore_none_value(
            dict(
                    subscriptionType=self.subscriptionType,
                    callbackReference=self.callbackReference,
                    _links=self._links,
                    appInstanceId=self.appInstanceId

                )
            )

class AppTerminationNotification:
    def __init__(self, operationAction: OperationActionType, maxGracefulTimeout: int, _links: LinkType, notificationType: str = "AppTerminationNotification") -> None:
        self.notificationType = notificationType
        self.operationAction = operationAction
        self.maxGracefulTimeout = maxGracefulTimeout
        self._links = _links
    
    def to_json(self):
        return ignore_none_value(
            dict(
                notificationType=self.notificationType,
                operationAction=self.operationAction,
                maxGracefulTimeout=self.maxGracefulTimeout,
                _links=self._links
            )
        )

#################
# ERROR CLASSES #
#################

class Error:
    def __init__(self, type: str, title: str, status: int, detail: str, instance: str):
        self.type = type
        self.title = title
        self.status = status
        self.detail = detail
        self.instance = instance

    def message(self):
        cherrypy.response.status = self.status

        return ProblemDetails(
            type=self.type,
            title=self.title,
            status=self.status,
            detail=self.detail,
            instance=self.instance
        )


class BadRequest(Error):
    def __init__(self, e: Exception):
        Error.__init__(
            self,
            type="about:blank",
            title="Incorrect parameters were passed to the request",
            status=400,
            detail=str(e).split('\n')[0],
            instance=cherrypy.request.path_info
        )


class Forbidden(Error):
    def __init__(self, detail : str = "This operation not allowed"):
        Error.__init__(
            self,
            type="about:blank",
            title="The operation is not allowed given the current status of the resource",
            status=403,
            detail=detail,
            instance=cherrypy.request.path_info
        )

class NotFound(Error):
    def __init__(self, detail: str = "This resource was not found"):
        Error.__init__(
            self,
            type="about:blank",
            title="The URI cannot be mapped to a valid resource URI.",
            status=404,
            detail=detail,
            instance=cherrypy.request.path_info
        )


class Conflict(Error):
    def __init__(self, detail: str = "This operation not allowed"):
        Error.__init__(
            self,
            type="about:blank",
            title="The operation is not allowed due to a conflict with the state of the resource",
            status=409,
            detail=detail,
            instance=cherrypy.request.path_info
        )

class Precondition(Error):
    def __init__(self, detail: str = "Precondition Failed"):
        Error.__init__(
            self,
            type="about:blank",
            title="The operation is not allowed due to a conflict with the state of the resource",
            status=412,
            detail=detail,
            instance=cherrypy.request.path_info
        )

class URITooLong(Error):
    def __init__(self, detail : str = "The request URI is longer than the server is able to process"):
        Error.__init__(
            self,
            type="about:blank",
            title="URI is too long",
            status=414,
            detail=detail,
            instance=cherrypy.request.path_info
        )

class TooManyRequests(Error):
    def __init__(self, detail : str = "Exceeded number of requests, the rate limiter has been triggered"):
        Error.__init__(
            self,
            type="about:blank",
            title="Too many requests",
            status=429,
            detail=detail,
            instance=cherrypy.request.path_info
        )


class TrafficFilter:
    def __init__(self, srcAddress: List[str] = None,
                 dstAddress: List[str] = None,
                 srcPort: List[str] = None,
                 dstPort: List[str] = None,
                 protocol: List[str] = None,
                 token: List[str] = None,
                 srcTunnelAddress: List[str] = None,
                 tgtTunnelAddress: List[str] = None,
                 srcTunnelPort: List[str] = None,
                 dstTunnelPort: List[str] = None,
                 qCI: int = 0,
                 dSCP: int = 0,
                 tC: int = 0):

        self.srcAddress = srcAddress
        self.dstAddress = dstAddress
        self.srcPort = srcPort
        self.dstPort = dstPort
        self.protocol = protocol
        self.token = token
        self.srcTunnelAddress = srcTunnelAddress
        self.tgtTunnelAddress = tgtTunnelAddress
        self.srcTunnelPort = srcTunnelPort
        self.dstTunnelPort = dstTunnelPort
        self.qCI = qCI
        self.dSCP = dSCP
        self.tC = tC

    @staticmethod
    def from_json(data: dict) -> TrafficFilter:
        # cherrypy.log("TrafficFilter from_json data:")
        # cherrypy.log(json.dumps(data))
        # First validate the json via jsonschema
        validate(instance=data, schema=trafficFilter_schema)
        srcAddress = data.pop("srcAddress") if "srcAddress" in data else None
        dstAddress = data.pop("dstAddress") if "dstAddress" in data else None
        srcPort = data.pop("srcPort") if "srcPort" in data else None
        dstPort = data.pop("dstPort") if "dstPort" in data else None
        protocol = data.pop("protocol") if "protocol" in data else None
        token = data.pop("token") if "token" in data else None
        srcTunnelAddress = data.pop("srcTunnelAddress") if "srcTunnelAddress" in data else None
        tgtTunnelAddress = data.pop("tgtTunnelAddress") if "tgtTunnelAddress" in data else None
        srcTunnelPort = data.pop("srcTunnelPort") if "srcTunnelPort" in data else None
        dstTunnelPort = data.pop("dstTunnelPort") if "dstTunnelPort" in data else None
        qCI = data.pop("qCI") if "qCI" in data else None
        dSCP = data.pop("dSCP") if "dSCP" in data else None
        tC = data.pop("tC") if "tC" in data else None

        return TrafficFilter(srcAddress = srcAddress, dstAddress = dstAddress, srcPort = srcPort,
                             dstPort = dstPort, protocol = protocol, token = token,
                             srcTunnelAddress = srcTunnelAddress, tgtTunnelAddress = tgtTunnelAddress,
                             srcTunnelPort = srcTunnelPort, dstTunnelPort = dstTunnelPort, qCI = qCI,
                             dSCP = dSCP, tC = tC)

    def to_json(self):
        return ignore_none_value(dict(srcAddress = self.srcAddress, dstAddress = self.dstAddress, srcPort = self.srcPort,
                                      dstPort = self.dstPort, protocol = self.protocol, token = self.token,
                                      srcTunnelAddress = self.srcTunnelAddress, tgtTunnelAddress = self.tgtTunnelAddress,
                                      srcTunnelPort = self.srcTunnelPort, dstTunnelPort = self.dstTunnelPort,
                                      qCI = self.qCI, dSCP = self.dSCP, tC = self.tC))


class TunnelInfo:

    def __init__(self, tunnelType: str, tunnelDstAddress: str,
                 tunnelSrcAddress: str):

        self.tunnelType = tunnelType
        self.tunnelDstAddress = tunnelDstAddress
        self.tunnelSrcAddress = tunnelSrcAddress

    @staticmethod
    def from_json(data: dict) -> TunnelInfo:
        # First validate the json via jsonschema
        validate(instance=data, schema=tunnelInfo_schema)

        tunnelType = data.pop("tunnelType")
        tunnelDstAddress = data.pop("tunnelDstAddress") if "tunnelDstAddress" in data else None
        tunnelSrcAddress = data.pop("tunnelSrcAddress") if "tunnelSrcAddress" in data else None

        return TunnelInfo(tunnelType = tunnelType, tunnelDstAddress = tunnelDstAddress,
                          tunnelSrcAddress = tunnelSrcAddress)

    def to_json(self):
        return ignore_none_value(dict(tunnelType = self.tunnelType,
                                      tunnelDstAddress = self.tunnelDstAddress,
                                      tunnelSrcAddress = self.tunnelSrcAddress) )


class DestinationInterface:
    def __init__(self, interfaceType: str,
                 tunnelInfo: TunnelInfo = None,
                 srcMacAddress: str = '',
                 dstMacAddress: str = '',
                 dstIpAddress: str= ''):

        self.interfaceType = interfaceType
        self.tunnelInfo = tunnelInfo
        self.srcMacAddress = srcMacAddress
        self.dstMacAddress = dstMacAddress
        self.dstIpAddress = dstIpAddress

    @staticmethod
    def from_json(data: dict) -> DestinationInterface:
        # First validate the json via jsonschema
        # cherrypy.log("Destination Interface from_json data:")
        # cherrypy.log(json.dumps(data))
        validate(instance=data, schema=destinationInterface_schema)

        interfaceType = data.pop("interfaceType")
        tunnelInfo = TunnelInfo.from_json(data.pop("tunnelInfo")) if "tunnelInfo" in data else None
        srcMacAddress = data.pop("srcMacAddress") if "srcMacAddress" in data else None
        dstMacAddress = data.pop("dstMacAddress") if "dstMacAddress" in data else None
        dstIpAddress = data.pop("dstIpAddress") if "dstIpAddress" in data else None

        return DestinationInterface(interfaceType = interfaceType, tunnelInfo = tunnelInfo,
                                    srcMacAddress = srcMacAddress, dstMacAddress = dstMacAddress,
                                    dstIpAddress = dstIpAddress)

    def to_json(self):
        return ignore_none_value(dict(interfaceType = self.interfaceType,
                                      tunnelInfo = self.tunnelInfo, srcMacAddress = self.srcMacAddress,
                                      dstMacAddress = self.dstMacAddress, dstIpAddress = self.dstIpAddress) )


class TrafficRule:
    def __init__(self, 
                 trafficRuleId: str, 
                 filterType: str,
                 priority: int,
                 trafficFilter: List[TrafficFilter] = None,
                 action: str = '',
                 dstInterface: List[DestinationInterface] = None,
                 state: str = ''
                ):

        self.trafficRuleId = trafficRuleId
        self.filterType = filterType
        self.priority = priority
        self.trafficFilter = trafficFilter
        self.action = action
        self.dstInterface = dstInterface
        self.state = state


    @staticmethod
    def from_json(data: dict) -> TrafficRule:
        validate(instance=data, schema=trafficRule_schema)
        # cherrypy.log("TrafficRule from_json data:")
        # cherrypy.log(json.dumps(data))

        trafficRuleId = data.pop("trafficRuleId")
        filterType = data.pop("filterType")
        priority = data.pop("priority")
        trafficFilters = data.pop("trafficFilter")
        trafficFilter = []
        for filter in trafficFilters:
            trafficFilter.append(TrafficFilter.from_json(filter))
        action = data.pop("action")
        dstInterfaces = data.pop("dstInterface")
        dstInterface = []
        for interface in dstInterfaces:
            dstInterface.append(DestinationInterface.from_json(interface))
        state = data.pop("state")

        return TrafficRule(trafficRuleId = trafficRuleId, filterType = filterType,
                            priority = priority, trafficFilter = trafficFilter, action = action,
                            dstInterface = dstInterface, state = state)

    def to_json(self):
        return ignore_none_value(dict(trafficRuleId = self.trafficRuleId, filterType = self.filterType,
                                      priority = self.priority, trafficFilter = self.trafficFilter,
                                      action = self.action, dstInterface = self.dstInterface, state = self.state) )
    
    def toNetworkPolicy(self):
        networkpolicy = dict(ingress=[self.getIngress()], egress=[self.getEgress()])
        # cherrypy.log(json.dumps(networkpolicy))
        return networkpolicy
           
    def getIngress(self):
        addresses = []
        for filter in self.trafficFilter:
            addresses.append(dict(srcAddress=filter.srcAddress, srcPort=filter.srcPort))
            
        _from = []
        _ports = []
        for address in addresses:
            for ip in address["srcAddress"]:
                _from.append({"ipBlock": {"cidr": ip}})
            for port in address["srcPort"]:
                _ports.append({"port": int(port)})
        
        return {"from":_from, "ports":_ports}

    def getEgress(self):
        addresses = []
        for filter in self.trafficFilter:
            addresses.append(dict(dstAddress=filter.dstAddress, dstPort=filter.dstPort))
        _to = []
        _ports = []
        for address in addresses:
            for ip in address["dstAddress"]:
                _to.append({"ipBlock": {"cidr": ip}})
            for port in address["dstPort"]:
                _ports.append({"port": int(port)})

        return {"to":_to, "ports":_ports}


class CurrentTime:
    def __init__(self, timeInfo: int, traceability: TimeSourceStatus = TimeSourceStatus.UNTRACEABLE):
        self.seconds = timeInfo
        self.nanoseconds = timeInfo
        self.timeSourceStatus = traceability
    
    def to_json(self):
        return ignore_none_value(dict(seconds = self.seconds, nanoseconds = self.nanoseconds, timeSourceStatus = self.timeSourceStatus) )


class TimingCaps:
    def __init__(self, 
    timeStamp: CurrentTime = None, 
    ntpServers: List[ntpServer] = None, 
    ptpMasters: List[ptpMaster] = None
    ):

        self.timeStamp = timeStamp
        self.ntpServers = ntpServers
        self.ptpMasters = ptpMasters
    
    def to_json(self):
        return ignore_none_value(dict(timeStamp = self.timeStamp, ntpServers = self.ntpServers, ptpMasters = self.ptpMasters) )

class ntpServer:
    def __init__(self, ntpServerAddrType: NtpServerAddrType, ntpServerAddr: string, minPollingInterval: int, 
    maxPollingInterval: int, localPriority: int, authenticationOption: AuthenticationOption, authenticationKeyNum: int):

     self.ntpServerAddrType = ntpServerAddrType
     self.ntpServerAddr = ntpServerAddr
     self.minPollingInterval = minPollingInterval
     self.maxPollingInterval = maxPollingInterval
     self.localPriority = localPriority
     self.authenticationOption = authenticationOption
     self.authenticationKeyNum = authenticationKeyNum


class ptpMaster:
    def __init__(self, ptpMasterIpAddress: string, ptpMasterLocalPriority: int, delayReqMaxRate: int):
        self.ptpMasterIpAddress = ptpMasterIpAddress
        self.ptpMasterLocalPriority = ptpMasterLocalPriority
        self.delayReqMaxRate = delayReqMaxRate
    
    def to_json(self):
        return ignore_none_value(dict(ptpMasterIpAddress = self.ptpMasterIpAddress, ptpMasterLocalPriority = self.ptpMasterLocalPriority, 
        delayReqMaxRate = self.delayReqMaxRate) )


class TimeStamp:
    def __init__(self, seconds: int, nanoseconds: int):
        self.seconds = seconds
        self.nanoseconds = nanoseconds
    def to_json(self):
        return ignore_none_value(dict(seconds = self.seconds, nanoseconds = self.nanoseconds))


class ServiceLivenessInfo:
    def __init__(self, state: ServiceState, timeStamp: TimeStamp, interval: int):
        self.state = state
        self.timeStamp = timeStamp
        self.interval = interval
    
    @staticmethod
    def from_json(data: dict) -> ServiceLivenessInfo:
        # First validate the json via jsonschema

        # cherrypy.log("validade timestamp")
        validate(instance = data["timeStamp"][0], schema = timeStamp_schema)

        # cherrypy.log("validate service liveness info")
        validate(instance=data, schema=serviceLivenessInfo_schema)

        state = data.pop("state")
        timeStamp = data.pop("timeStamp")
        interval = data.pop("interval")

        return ServiceLivenessInfo(state, timeStamp, interval)

    def to_json(self):
        return ignore_none_value(dict(state = self.state, timeStamp = self.timeStamp, interval = self.interval))


class ServiceLivenessUpdate:
    def __init__(self, state: ServiceState):
        self.state = state
    
    @staticmethod
    def from_json(data: dict) -> ServiceLivenessInfo:
        # First validate the json via jsonschema
        # cherrypy.log("validate service liveness update")
        validate(instance=data, schema=serviceLivenessUpdate_schema)
        state = data.pop("state")

        return ServiceLivenessUpdate(state)

    def to_json(self):
        return ignore_none_value(dict(state = self.state))

##############################################################################
############################    MM5 DATA TYPES    ############################
##############################################################################
# MEC 010v2 6.2.2.21


class TransportDescriptor:
    """
    The TransportDescriptor data type describes a transport.

    Section 6.2.1.19 of MEC010-2
    """
    def __init__(
        self,
        name: str,
        type: TransportType,
        version: str,
        security: SecurityInfo,
        description: str = "",
        protocol: str = "HTTP",
        implSpecificInfo: str = ""):
        """
        :param name: Name of this transport.
        :param description: Human-readable description of this transport.
        :param type: Type of transport.
        :param protocol: The name of the protocol used.
        :param version: The version of the protocol used.
        :param security: Information about the security used by the transport.
        :param implSpecificInfo: Additional implementation specific details of the transport.
        """

        self.name = name
        self.description = description
        self.type = type
        self.protocol = protocol
        self.version = version
        self.security = security
        self.implSpecificInfo = implSpecificInfo

    @staticmethod
    def from_json(data: dict) -> TransportDescriptor:
        # First validate the json via jsonschema
        validate(instance=data, schema=transportDescriptor_schema)

        name = data.pop("name")
        description = data.pop("description", None)
        type = TransportType(data.pop("type"))

        # Always "HTTP" since is a REST API? TODO: Check this
        protocol = data.pop("protocol")
        version = data.pop("version")
        security = SecurityInfo.from_json(data.pop("security"))
        implSpecificInfo = data.pop("implSpecificInfo", None)

        return TransportDescriptor(name, description, type, protocol, version, security, implSpecificInfo)


class ServiceDescriptor:
    def __init__(
        self,
        serName: str = None,
        serCategory: CategoryRef = None,
        version: str = None,
        transportsSupported: List[Transports] = None
        ):
        """
        :param serName: Name of the service.
        :param serCategory: A Category reference of the service, defined in ETSI GS MEC 011
        :param version: Version of the service.
        :param transportsSupported: Indicates transports and serialization formats supported made available to the service-consuming application. Defaults to REST + JSON if absent.
        :param transport: Information about the transport in this binding.
        :param serializers: Information about the serializers in this binding, as defined in the SerializerType type in ETSI GS MEC 011
        """
        self.serName = serName
        self.serCategory = serCategory
        self.version = version
        self.transportsSupported = transportsSupported

    @staticmethod
    def from_json(data: dict) -> ServiceDescriptor:
        validate(instance=data, schema=serviceDescriptor_schema)

        serName = data.pop("serName")
        serCategory = data.pop("serCategory")
        version = data.pop("version")
        transportsSupported = data.pop("transportsSupported")

        return ServiceDescriptor(serName, serCategory, version, transportsSupported)


class FeatureDependency:
    """
    The FeatureDependency data type supports the specification of requirements 
    of a MEC application related to a feature of MEC platform.

    Section 6.2.8 of MEC 010-2
    """
    def __init__(self, featureName: str, version: str):
        """
        :param featureName: Name of the feature.
        :param version: Version of the feature.
        """
        self.featureName = featureName
        self.version = version

    @staticmethod
    def from_json(data: dict) -> FeatureDependency:
        validate(instance=data, schema=featureDependency_schema)

        return FeatureDependency(data.pop("featureName"), data.pop("version"))


class Transports:
    def __init__(
        self,
        transport: TransportDescriptor,
        serializers: List[SerializerType],
        ):
        """
        :param transport: Information about the transport in this transport binding.
        :param serializers: Information about the serializers in this transport binding.
        :param labels: Set of labels that allow to define groups of transport bindings.
        """
        self.transport = transport
        self.serializers = serializers

    @staticmethod
    def from_json(data: dict) -> Transports:
        validate(instance=data, schema=transports_schema)

        transport = TransportDescriptor.from_json(data.pop("transport"))
        serializers = [SerializerType(s) for s in data.pop("serializers")]

        return Transports(transport, serializers)


class TransportDependency:
    """
    The TransportDependency data type supports the specification of requirements
    of a MEC application related to supported transport bindings (each being a 
    combination of a transport with one or more serializers).

    6.2.1.18 of MEC 010-2
    """
    def __init__(
        self,
        transport: TransportDescriptor,
        serializers: List[SerializerType],
        labels: List[str],
        ):
        """
        :param transport: Information about the transport in this transport binding.
        :param serializers: Information about the serializers in this transport binding.
        :param labels: Set of labels that allow to define groups of transport bindings.
        """
        self.transport = transport
        self.serializers = serializers
        self.labels = labels

    @staticmethod
    def from_json(data: dict) -> TransportDependency:
        # First validate the json via jsonschema
        validate(instance=data, schema=transportDependency_schema)

        transport = TransportDescriptor.from_json(data.pop("transport"))
        serializers = [SerializerType(s) for s in data.pop("serializers")]
        labels = data.pop("labels")

        return TransportDependency(transport, serializers, labels)


class ServiceDependency:
    """
    The ServiceDependency data type supports the specification of requirements 
    of a service-consuming MEC application related to a MEC service.
    
    Section 6.2.1.17 of MEC 010-2
    """
    def __init__(
        self, 
        serName: str, 
        version: str,  
        serCategory: CategoryRef = None,
        serTransportDependencies: TransportDependency = None, 
        requestedPermissions: List[str] = None):
        """
        :param serName: Name of the service.
        :param serCategory: A Category reference of the service.
        :param version: Version of the service.
        :param serTransportDependencies: Indicates transport and serialization format dependencies of consuming the service. Defaults to REST + JSON if absent.
        :param requestedPermissions: Requested permissions regarding the access of the application to the service.
        """

        self.serName = serName
        self.serCategory = serCategory
        self.version = version
        self.serTransportDependencies = serTransportDependencies
        self.requestedPermissions = requestedPermissions

    def to_json(self):
        return ignore_none_value(dict(
            serName = self.serName,
            serCategory = self.serCategory,
            version = self.version,
            serTransportDependencies = self.serTransportDependencies,
            requestedPermissions = self.requestedPermissions
        ))
    
    @staticmethod
    def from_json(data: dict) -> ServiceDependency:
        # First validate the json via jsonschema
        validate(instance=data, schema=serviceDependency_schema)

        serName = data.pop("serName")
        serCategory = data.pop("serCategory", None)
        
        if serCategory is not None:
            serCategory = CategoryRef(**serCategory)
       
        version = data.pop("version")
        
        serTransportDependencies = data.pop("serTransportDependencies", None)
        if serTransportDependencies is not None:
            serTransportDependencies = [TransportDependency.from_json(td) for td in serTransportDependencies]
        else:
            # TODO insert oAuth2Info when creating SecurityInfo to be used in TransportDescriptor?
            transp_descript = TransportDescriptor(
                name="REST", 
                type=TransportType.REST, 
                protocol="HTTP", 
                version="2.0",
                securityInfo=SecurityInfo()
                )
            # TODO label = ["A"], label = ["B"] or label = ["A", "B"]?
            serTransportDependencies = [
                TransportDependency(transp_descript, [SerializerType.JSON], ["A"])
                ]

        requestedPermissions = data.pop("requestedPermissions", None)             

        return ServiceDependency(serName, serCategory, version, serTransportDependencies, requestedPermissions)


class TrafficRuleDescriptor:
    def __init__(self, trafficRule: TrafficRule):
        self.trafficRule = trafficRule
    
    def from_json(data: dict):
        data = data | {"state": "ACTIVE"}
        trafficRuleDescriptor = TrafficRule.from_json(data)
        return TrafficRuleDescriptor(trafficRuleDescriptor)

    def to_json(self):
        trafficRuleDescriptor = self.trafficRule.to_json()
        trafficRuleDescriptor.pop("state")
        return trafficRuleDescriptor


class DNSRuleDescriptor:
    def __init__(self, dnsRule: DnsRule):
        self.dnsRule = dnsRule
    
    def from_json(data: dict):
        data = data | {"state": "ACTIVE"}
        dnsRule = DnsRule.from_json(data)
        return DNSRuleDescriptor(dnsRule)

    def to_json(self):
        dnsDescriptor = self.dnsRule.to_json()
        dnsDescriptor.pop("state")
        return dnsDescriptor


class LatencyDescriptor:
    """
    This data type describes latency requirements for a MEC application.

    Section 6.2.1.14 - MEC 010-2
    """
    def __init__(self, maxLatency: int):
        """
        :param maxLatency: Maximum latency in nano seconds tolerated by the MEC application.
        """
        self.maxLatency = maxLatency

    @staticmethod
    def from_json(data: dict) -> LatencyDescriptor:
        return LatencyDescriptor(int(data.pop("maxLatency")))


class UserContextTransferCapility:
    """
    This data type represents the information of user context transfer capability of application.

    Section 6.2.1.20 - MEC 010-2
    """
    def __init__(self, statefulApplication: bool, userContextTransfer: bool = None):
        """
        :param statefulApplication: Indicates whether the application is stateful.
        :param userContextTransfer: Indicates whether the application supports user 
        context transfer. This attribute shall be present if the application is 
        stateful and shall be absent otherwise.

        """
        self.statefulApplication = statefulApplication
        self.userContextTransfer = userContextTransfer

        if statefulApplication and userContextTransfer is None:
            raise ValueError("userContextTransfer must be present if the application is stateful")
        if not statefulApplication and userContextTransfer is not None:
            raise ValueError("userContextTransfer must be absent if the application is not stateful")

    @staticmethod
    def from_json(data: dict) -> UserContextTransferCapility:
        validate(instance=data, schema=userContextTransferCapility_schema)
        return UserContextTransferCapility(**data)


class SteeredNets:
    def __init__(
        self, 
        cellularNetwork: bool = None, 
        wifiNetwork: bool = None, 
        fixedAccessNetwork: bool = None):
        """
        :param cellularNetwork: Indicates whether the application can be steered to cellular network.
        :param wifiNetwork: Indicates whether the application can be steered to Wi-Fi network.
        :param fixedAccessNetwork: Indicates whether the application can be steered to fixed access network.
        """
        self.cellularNetwork = cellularNetwork
        self.wifiNetwork = wifiNetwork
        self.fixedAccessNetwork = fixedAccessNetwork


class AppNetworkPolicy:
    """
    This data type represents the network policy in the application instantiation and operation.

    Section 6.2.1.21 - MEC 010-2
    """
    def __init__(self, steeredNetworks: SteeredNets):
        """
        :param steeredNetworks: The network policy of the application.
        """
        self.steeredNetworks = steeredNetworks

    @staticmethod
    def from_json(data: dict) -> AppNetworkPolicy:
        validate(instance=data, schema=appNetworkPolicy_schema)

        return AppNetworkPolicy(SteeredNets(**data["steeredNetwork"]))


class ConfigPlatformForAppRequest:
    """
    This data type represents the parameters for configuring the MEP to run an application instance.

    Section 6.2.2.21 - MEC 010-2
    """
    def __init__(
        self, 
        appServiceRequired: List(ServiceDependency) = None,
        appServiceOptional: List(ServiceDependency) = None,
        appServiceProduced: List(ServiceDescriptor) = None,
        appFeatureRequired: List(FeatureDependency) = None,
        appFeatureOptional: List(FeatureDependency) = None,
        transportDependencies: List(TransportDependency) = None,
        appTrafficRule: List(TrafficRuleDescriptor) = None,
        appDNSRule: List(DNSRuleDescriptor) = None,
        appLatency: LatencyDescriptor = None,
        userContextTransferCapability: UserContextTransferCapility = None,
        appNetworkPolicy: AppNetworkPolicy = None,
        ):
        """
        :param appServiceRequired: Describes services a MEC application requires to run.
        :param appServiceOptional: Describes services a MEC application may use if available.
        :param appServiceProduced: Describes services a MEC application is able to produce to the platform or other MEC applications. Only relevant for service-producing apps.
        :param appFeatureRequired: Describes features a MEC application requires to run.
        :param appFeatureOptional: Describes features a MEC application may use if available.
        :param transportDependencies: Transports, if any, that this application requires to be provided by the platform. These transports will be used by the application to deliver services provided by this application. Only relevant for service-producing apps.
        :param appTrafficRule: Describes traffic rules a MEC application requires.
        :param appDNSRule: Describes DNS rules a MEC application requires.
        :param appLatency: Describes the maximum latency tolerated by the MEC application.
        :param userContextTransferCapability: Describes the user context transfer capability of the MEC application. If the application supports the user context transfer capability, this attribute shall be included.
        :param appNetworkPolicy: If present, it represents the application network policy of carrying the application traffic.
        """
        self.appServiceRequired = appServiceRequired
        self.appServiceOptional = appServiceOptional
        self.appServiceProduced = appServiceProduced
        self.appFeatureRequired = appFeatureRequired
        self.appFeatureOptional = appFeatureOptional
        self.transportDependencies = transportDependencies
        self.appTrafficRule = appTrafficRule
        self.appDNSRule = appDNSRule
        self.appLatency = appLatency
        self.userContextTransferCapability = userContextTransferCapability
        self.appNetworkPolicy = appNetworkPolicy

    def from_json(data: dict) -> ConfigPlatformForAppRequest:
        try:
            appServiceRequired = []
            for svc in data["appServiceRequired"]:
                appServiceRequired.append(ServiceDependency.from_json(svc))
        except KeyError:
            appServiceRequired = None
            
        try:
            appServiceOptional = []
            for svc in data["appServiceOptional"]:
                appServiceOptional.append(ServiceDependency.from_json(svc))
        except KeyError:
            appServiceOptional = None
        
        try:
            appServiceProduced = []
            for svc in data["appServiceProduced"]:
                appServiceProduced.append(ServiceDescriptor.from_json(svc))
        except KeyError:
            appServiceProduced = None

        try:
            appFeatureRequired = []
            for ft in data["appFeatureRequired"]:
                appFeatureRequired.append(FeatureDependency.from_json(ft))
        except KeyError:
            appFeatureRequired = None

        try:
            appFeatureOptional = []
            for ft in data["appFeatureOptional"]:
                appFeatureOptional.append(FeatureDependency.from_json(ft))
        except KeyError:
            appFeatureOptional = None

        try:
            transportDependencies = []
            for td in data["transportDependencies"]:
                transportDependencies.append(TransportDependency.from_json(td))
        except KeyError:
            transportDependencies = None

        try:
            appTrafficRule = []
            for tr in data["appTrafficRule"]:
                appTrafficRule.append(TrafficRuleDescriptor.from_json(tr))
        except KeyError:
            appTrafficRule = None

        try:
            appDNSRule = []
            for dr in data["appDNSRule"]:
                appDNSRule.append(DNSRuleDescriptor.from_json(dr))
        except KeyError:
            appDNSRule = None

        try:
            appLatency = LatencyDescriptor.from_json(data["appLatency"])
        except KeyError:
            appLatency = None

        try:
            userContextTransferCapability = UserContextTransferCapility.from_json(data["userContextTransferCapability"])
        except KeyError:
            userContextTransferCapability = None
        
        try:
            appNetworkPolicy = AppNetworkPolicy.from_json(data["appNetworkPolicy"])
        except KeyError:
            appNetworkPolicy = None

        return ConfigPlatformForAppRequest(
            appServiceRequired=appServiceRequired,
            appServiceOptional=appServiceOptional,
            appServiceProduced=appServiceProduced,
            appFeatureRequired=appFeatureRequired,
            appFeatureOptional=appFeatureOptional,
            transportDependencies=transportDependencies,
            appTrafficRule=appTrafficRule,
            appDNSRule=appDNSRule,
            appLatency=appLatency,
            userContextTransferCapability=userContextTransferCapability,
            appNetworkPolicy=appNetworkPolicy
        )

    def to_json(self):
        return ignore_none_value(
            dict(
                appServiceRequired=self.appServiceRequired,
                appServiceOptional=self.appServiceOptional,
                appServiceProduced=self.appServiceProduced,
                appFeatureRequired=self.appFeatureRequired,
                appFeatureOptional=self.appFeatureOptional,
                transportDependencies=self.transportDependencies,
                appTrafficRule=self.appTrafficRule,
                appDNSRule=self.appDNSRule,
                appLatency=self.appLatency,
                userContextTransferCapability=self.userContextTransferCapability,
                appNetworkPolicy=self.appNetworkPolicy
            )
        )


class ChangeAppInstanceState:
    def __init__(self, appInstanceId: str, changeStateTo: ChangeStateTo, stopType: StopType = None, gracefulStopTimeout: int = None) -> None:
        self.appInstanceId = appInstanceId
        self.changeStateTo = changeStateTo
        self.stopType = stopType
        self.gracefulStopTimeout = gracefulStopTimeout
    
    def from_json(data: dict):
        validate(data, schema=changeAppInstanceState_schema)
        appInstanceId = data.pop("appInstanceId")
        changeStateTo = ChangeStateTo(data.pop("changeStateTo"))
        stopType = StopType(data.pop("stopType"))
        gracefulStopTimeout = int(data.pop("gracefulStopTimeout"))

        return ChangeAppInstanceState(
            appInstanceId=appInstanceId,
            changeStateTo=changeStateTo,
            stopType=stopType,
            gracefulStopTimeout=gracefulStopTimeout
        )

    def to_json(self):
        return ignore_none_value(
            dict(
                appInstanceId=self.appInstanceId,
                changeStateTo=self.changeStateTo,
                stopType=self.stopType,
                gracefulStopTimeout=self.gracefulStopTimeout
            )
        )


class TerminateAppInstance:
    def __init__(self, appInstanceId: str, terminationType: TerminationType, gracefulStopTimeout: int) -> None:
        self.appInstanceId = appInstanceId
        self.terminationType = terminationType
        self.gracefulStopTimeout = gracefulStopTimeout
    
    def from_json(data: dict):
        validate(data, schema=terminateAppInstance_schema)
        appInstanceId = data.pop("appInstanceId")
        terminationType = TerminationType(data.pop("terminationType"))
        try:
            gracefulStopTimeout = int(data.pop("gracefulStopTimeout"))
        except KeyError:
            gracefulStopTimeout = 0

        return TerminateAppInstance(
            appInstanceId=appInstanceId,
            terminationType=terminationType,
            gracefulStopTimeout=gracefulStopTimeout
        )

    def to_json(self):
        return ignore_none_value(
            dict(
                appInstanceId=self.appInstanceId,
                terminationType=self.terminationType,
                gracefulStopTimeout=self.gracefulStopTimeout
            )
        )


class AppInstanceState:
    def __init__(self, instantiationState: InstantiationState, operationalState: OperationalState = None):
        self.instantiationState = instantiationState
        self.operationalState = operationalState
    
    def to_json(self):
        return ignore_none_value(
            dict(
                instantiationState=self.instantiationState,
                operationalState=self.operationalState
            )
        )


# New
class Links_:
    """
    This type represents links to resources that are related to a AppInstance resource.
    """
    def __init__(
        self, 
        self_: LinkType,
        instantiate: LinkType = None,
        terminate: LinkType = None,
        operate: LinkType = None,
        configure_platform_for_app: LinkType = None):
        """
        :param self_: Self referring URI.
        :param instantiate: Link to the "instantiate" task resource, if the related operation is possible based on the current status of this application instance resource (i.e. application instance in NOT_INSTANTIATED state).
        :param terminate: Link to the "terminate" task resource, if the related operation is possible based on the current status of this application instance resource (i.e. application instance is in INSTANTIATED state).
        :param operate: Link to the "operate" task resource, if the related operation is possible based on the current status of this application instance resource (i.e. application instance is in INSTANTIATED state).
        :param configure_platform_for_app: Link to the "configurePlatformForApp" task resource, if the related operation is possible based on the current status of this application instance resource (i.e. application instance is in INSTANTIATED state).
        """
        self.self_ = self_
        self.instantiate = instantiate
        self.terminate = terminate
        self.operate = operate
        self.configure_platform_for_app = configure_platform_for_app

    @classmethod
    def from_json(data: dict) -> Links_:
        #validate(data, schema=links__schema)
        self_ = LinkType.from_json(data.pop("self"))
        instantiate = LinkType.from_json(data.pop("instantiate"))
        terminate = LinkType.from_json(data.pop("terminate"))
        operate = LinkType.from_json(data.pop("operate"))
        configure_platform_for_app = LinkType.from_json(data.pop("configurePlatformForApp"))
        return Links_(self_=self_, instantiate=instantiate, terminate=terminate, operate=operate, configure_platform_for_app=configure_platform_for_app)


# New
class AppInstanceInfo:
    """
    This data type the parameters of instantiated application instance resources.

    Section 6.2.2.4 of ETSI MEC 010-2 v2.2.1 (2022-02)
    """
    def __init__(
        self,
        id: str,
        appDId: str,
        appProvider: str,
        appName: str,
        appSoftVersion: str,
        appDVersion: str,
        appPkgId: str,
        instantiationState: InstantiationState,
        appInstanceName: str = None,
        appInstanceDescription: str = None,
        vimConnectionInfo: List[VimConnectionInfo] = None,
        nsInstanceId: str = None,
        vnfInstaneId: str = None,
        instantiationAppState: InstantiationAppState = None,
        communicationInterface: CommunicationInterface = None,
        _links: Links_ = None,
        ):
        """
        :param id: Identifier of the application instance represented by this data type.
        :param appDId: Identifier of the application descriptor associated with this application instance. ThIS identifier is managed by the application provider to identify the application descriptor in a globally unique way.

        """
        pass

############################ EXTRA SERVICES (DNS AND OAUTH) ###########################################

class OAuthServer:
    def __init__(self, url: str, port: str) -> None:
        self.url = url
        self.port = port
    
    def register(self):
        response = requests.get("http://%s:%s/register" %(self.url, self.port))
        response = json.loads(response.content)
        if (response['message'] == 'Client registered successfully'):
            response.pop('message')
            return response
        
        return False
            
    def get_token(self, client_id:str, client_secret:str):
        credentials = dict(grant_type="client_credentials", client_id=client_id, client_secret=client_secret)
        response = requests.post("http://%s:%s/token" %(self.url, self.port), json=credentials)
        if response.status_code == 200:
            token = json.loads(response.content)['access_token']
            return token
        
        return False
    
    def validate_token(self, access_token:str):
        data = dict(access_token=access_token)
        response = requests.post("http://%s:%s/validate_token" %(self.url, self.port), json=data)
        return response.status_code == 200
    
    def delete_client(self, client_id:str, client_secret:str):
        credentials = dict(client_id=client_id, client_secret=client_secret)
        response = requests.post("http://%s:%s/delete" %(self.url, self.port), json=credentials)        
        return response.status_code == 200


class DnsApiServer:
    def __init__(self, url: str, port: str, zone: str = "zone0") -> None:
        self.url = url
        self.port = port
        self.zone = zone

    def create_record(self, domain: str, ip: str, ttl: int):

        headers = {"Content-Type": "application/json"}
        query = {"name": domain, "ip": ip, "ttl": ttl}

        url_0 = 'http://%s:%s/dns_support/v1/api/%s/record' % (self.url, self.port, self.zone)

        response = requests.post(url_0, headers=headers, params=query)

        # print(f"\n# DNS rule creation #\nresponse: {response.json()}\n")

        return response.status_code == 200

    def remove_record(self, domain: str):
        
        headers = {"Content-Type": "application/json"}
        
        url = 'http://%s:%s/dns_support/v1/api/%s/record?name=%s' %(self.url, self.port, self.zone, domain)
        
        response = requests.delete(url, headers=headers)

        return response.status_code == 200