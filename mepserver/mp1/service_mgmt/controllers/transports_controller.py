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

import sys
import cherrypy

sys.path.append("../../")
from mp1.models import *


class TransportsController:
    @json_out(cls=NestedEncoder)
    def transports_get(self, **kwargs,):
        """
        This method retrieves information about a list of available transports. This method is typically used by a service-producing application to discover transports provided by the MEC platform in the "transport information query" procedure

        :return: TransportInfo or ProblemDetails
        HTTP STATUS CODE: 200, 400, 403, 404
        """
                #  If kwargs isn't None the get request was made with invalid atributes
        if kwargs != {}:
            error_msg = "Invalid attribute(s): %s" % (str(kwargs))
            error = BadRequest(error_msg)
            return error.message()
        
        data = json.loads(
            '{"id":"string","name":"string","description":"string","type":"REST_HTTP","protocol":"string","version":"string","security":{"oAuth2Info":{"grantTypes":["OAUTH2_AUTHORIZATION_CODE"],"tokenEndpoint":"string"}},"implSpecificInfo":{}}'
        )
        # transportInfo = TransportInfo.from_json(data)
        return data
