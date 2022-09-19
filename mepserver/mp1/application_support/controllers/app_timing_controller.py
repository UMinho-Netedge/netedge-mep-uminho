import sys
import cherrypy

sys.path.append("../../")
from mp1.models import *


class AppTimingController:
    @json_out(cls=NestedEncoder)
    def timing_capabilites_get(self):
        pass

    def current_time_get(self):
        pass
