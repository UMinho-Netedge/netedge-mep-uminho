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

from enum import Enum


class ServiceState(Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"


class SerializerType(Enum):
    JSON = "JSON"
    XML = "XML"
    PROTOBUF3 = "PROTOBUF3"


class LocalityType(Enum):
    MEC_SYSTEM = "MEC_SYSTEM"
    MEC_HOST = "MEC_HOST"
    NFVI_POP = "NFVI_POP"
    ZONE = "ZONE"
    ZONE_GROUP = "ZONE_GROUP"
    NFVI_NODE = "NFVI_NODE"


class TransportType(Enum):
    REST_HTTP = "REST_HTTP"
    MB_TOPIC_BASED = "MB_TOPIC_BASED"
    MB_ROUTING = "MB_ROUTING"
    MB_PUBSUB = "MB_PUBSUB"
    RPC = "RPC"
    RPC_STREAMING = "RPC_STREAMING"
    WEBSOCKET = "WEBSOCKET"


class GrantTypes(Enum):
    OAUTH2_AUTHORIZATION_CODE = "OAUTH2_AUTHORIZATION_CODE"
    OAUTH2_IMPLICIT_GRANT = "OAUTH2_IMPLICIT_GRANT"
    OAUTH2_RESOURCE_OWNER = "OAUTH2_RESOURCE_OWNER"
    OAUTH2_CLIENT_CREDENTIALS = "OAUTH2_CLIENT_CREDENTIALS"


class IndicationType(Enum):
    READY = "READY"


class OperationActionType(Enum):
    STOPPING = "STOPPING"
    TERMINATING = "TERMINATING"

    def __str__(self):
        return self.name


class ChangeType(Enum):
    ADDED = "ADDED"  # New service was added
    REMOVED = "REMOVED"  # The service was removed
    STATE_CHANGED = "STATE_CHANGED"  # Only the state of the service was changed
    ATTRIBUTES_CHANGED = "ATTRIBUTES_CHANGED"  # At least one attribute of the service other than state was changed. The change may or may not include changing the state

class FilterType(Enum):
    FLOW = "FLOW"
    PACKET =  "PACKET"

class TrafficRuleAction(Enum):
    DROP = "DROP"
    FORWARD_DECAPSULATED = "FORWARD_DECAPSULATED"
    FORWARD_ENCAPSULATED = "FORWARD_ENCAPSULATED"
    PASSTHROUGH = "PASSTHROUGH"
    DUPLICATE_DECAPSULATED = "DUPLICATE_DECAPSULATED"
    DUPLICATE_ENCAPSULATED = "DUPLICATE_ENCAPSULATED"

class TrafficRuleState(Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

class InterfaceType(Enum):
    TUNNEL = "TUNNEL"
    MAC = "MAC"
    IP = "IP"

class TunnelType(Enum):
    GTP_U = "GTP_U"
    GRE = "GRE"

class IpAddressType(Enum):
    IP_V4 = "IP_V4"
    IP_V6 = "IP_V6"

class StateType(Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

class TimeSourceStatus(Enum):
    TRACEABLE = "TRACEABLE"
    UNTRACEABLE = "UNTRACEABLE"

class NtpServerAddrType(Enum):
    IP_ADDRESS = "IP_ADDRESS"
    DNS_NAME = "DNS_NAME"

class AuthenticationOption(Enum):
    NONE = "NONE"
    SYMMETRIC_KEY = "SYMMETRIC_KEY"
    AUTO_KEY = "AUTO_KEY"

class ChangeStateTo(Enum):
    STARTED = "STARTED"
    STOPPED = "STOPPED"

class StopType(Enum):
    FORCEFUL = "FORCEFUL"
    GRACEFUL = "GRACEFUL"

class TerminationType(Enum):
    FORCEFUL = "FORCEFUL"
    GRACEFUL = "GRACEFUL"

class OperationStatus(Enum):
    PROCESSING = "PROCESSING"
    SUCCESSFULLY_DONE = "SUCCESSFULLY_DONE"
    FAILED = "FAILED"

class InstantiationState(Enum):
    NOT_INSTANTIATED = "NOT_INSTANTIATED"
    INSTANTIATED = "INSTANTIATED"

class OperationalState(Enum):
    STARTED = "STARTED"
    STOPPED = "STOPPED"