# Copyright 2022 Instituto de Telecomunicações - Aveiro
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

sys.path.append("../../")
from mp1.models import *
import jsonschema
import uuid


class ServicesController:
    #@url_query_validator(cls=ServicesQueryValidator)
    @json_out(cls=NestedEncoder)
    def services_get(
        self,
        ser_instance_id: List[str] = None,
        ser_name: List[str] = None,
        ser_category_id: str = None,
        scope_of_locality: str = None,
        consumed_local_only: bool = None,
        is_local: bool = None,
        **kwargs,
    ):
        """
        This method retrieves information about a list of mecService resources. This method is typically used in "service availability query" procedure
        Query Params
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

        :return: ServiceInfo or ProblemDetails
        HTTP STATUS CODE: 200, 400, 403, 404, 414
        """
        
        #  If kwargs isn't None the get request was made with invalid atributes
        if kwargs != {}:
            error_msg = "Invalid attribute(s): %s" % (str(kwargs))
            error = BadRequest(error_msg)
            return error.message()
            
        try:
            query = ServiceGet(
                        ser_instance_id=ser_instance_id,
                        ser_name=ser_name,
                        ser_category_id=ser_category_id,
                        scope_of_locality=scope_of_locality,
                        consumed_local_only=consumed_local_only,
                        is_local=is_local)
            query = query.to_query()

            if ser_instance_id != None:
                try:
                    ser_inst_ids_list = ser_instance_id.split(",")
                    for instance_id in ser_inst_ids_list:
                        uuid.UUID(str(instance_id))
                    
                except ValueError:
                    error_msg = f"'ser_instance_id' attempted with invalid format with the value {instance_id}." \
                                " Value is required in UUID format."
                    error = BadRequest(error_msg)
                    return error.message()

            result = cherrypy.thread_data.db.query_col("services", query)
            result = list(result)

        except jsonschema.exceptions.ValidationError as e:
            if "is not of type" in str(e.message):
                error_msg = "Invalid type in '"                                 \
                            + str(camel_to_snake(e.json_path.replace("$.",""))) \
                            + "' attribute: "+str(e.message)
            else:
                error_msg = "Either 'ser_instance_id' or 'ser_name' or "        \
                        "'ser_category_id' or none of them shall be present."
            error = BadRequest(error_msg)
            return error.message()

        # Apps which state IS NOT READY
        appNotReady = cherrypy.thread_data.db.query_col(
            "appStatus",
            query={"$or": [{"indication": "STOPPING"}, {"indication": "TERMINATING"}]},)

        appNotReady = list(appNotReady)
        if appNotReady:
            # create a list of serInstanceIds from not ready apps
            servs_to_del = []
            for app in appNotReady:
                for service in app["services"]:
                    servs_to_del.append(service["serInstanceId"])
            
            print(f"servs_to_del:\n{servs_to_del}")
            # remove them from the result (list of all services)
            res = []
            for idx, service_info in enumerate(result):
                if service_info["serInstanceId"] not in servs_to_del:
                    res.append(service_info)
            print(f"result:\n{res}")
            return res
        # Data is a pymongo cursor we first need to convert it into a json serializable object
        # Since this query is supposed to return various valid Services we can simply convert into a list
        return result
        

    @json_out(cls=NestedEncoder)
    def services_get_with_serviceId(
        self,
        serviceId: str,
        **kwargs
    ):
        """
        This method retrieves information about a mecService resource. This method is typically used in "service availability query" procedure
        :param serviceId: Represents a MEC service instance.
        :type serviceId: String
        :return: ServiceInfo or ProblemDetails
        """
        if kwargs != {}:
            error_msg = "Invalid attribute(s): %s" % (str(kwargs))
            error = BadRequest(error_msg)
            return error.message()

        try:
            uuid.UUID(str(serviceId))
        except ValueError:
            error_msg = "Attempted 'serviceId' with invalid format." \
                        " Value is required in UUID format."
            error = BadRequest(error_msg)
            return error.message()

        query = dict(serInstanceId=str(serviceId))
        data = cherrypy.thread_data.db.query_col("services", query)
        result = list(data)

        # Apps which state IS NOT READY
        appNotReady = cherrypy.thread_data.db.query_col(
            "appStatus",
            query={"$or": [{"indication": "STOPPING"}, {"indication": "TERMINATING"}]},)
        
        appNotReady = list(appNotReady)
        if appNotReady:
            for app in appNotReady:
                for service in app["services"]:
                    if service["serInstanceId"] == serviceId:
                        #return list()
                        error_msg = "Service producing app isn't in READY state."
                        error = Forbidden(error_msg)
                        return error.message()

        return result


    def __str__(self):
        return "\nser_instance_id: "+str(self.ser_instance_id)+ \
                "\nser_name: "+str(self.ser_name)+ \
                "\nser_category_id: "+str(self.ser_category_id)+ \
                "\nscope_of_locality: "+str(self.scope_of_locality)+ \
                "\nconsumed_local_only: "+str(self.consumed_local_only)+ \
                "\nis_local: "+str(self.is_local)
