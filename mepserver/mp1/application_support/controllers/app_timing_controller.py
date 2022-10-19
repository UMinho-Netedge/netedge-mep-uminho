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

import json
import sys
from time import time_ns
import cherrypy

sys.path.append("../../")
from mp1.models import *
import uuid
import jsonschema


class AppTimingController:
    @json_out(cls=NestedEncoder)
    def timing_capabilites_get(self, **kwargs):
        """"
        This method retrieves the information of the platform's timing capabilities which corresponds to the timing capabilities query
        
        :return: TimingCaps or ProblemDetails
        """

        if kwargs != {}:
            error_msg = "Invalid attribute(s): %s" % (str(kwargs))
            error = BadRequest(error_msg)
            return error.message()

        timmingCaps = TimingCaps()
        return timmingCaps

    # For now just for test
    @json_out(cls=NestedEncoder)
    def current_time_get(self, **kwargs):
        """"
        This method retrieves the information of the platform's current time which corresponds to the get platform time procedure
        
        :return: CurrentTime or ProblemDetails
        """

        if kwargs != {}:
            error_msg = "Invalid attribute(s): %s" % (str(kwargs))
            error = BadRequest(error_msg)
            return error.message()

        currentTime = CurrentTime(time_ns(), TimeSourceStatus.TRACEABLE)
        return currentTime
