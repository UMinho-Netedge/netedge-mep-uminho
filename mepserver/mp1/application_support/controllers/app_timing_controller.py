import sys
import cherrypy
import time

sys.path.append("../../")
from mp1.models import *


class AppTimingController:
    @json_out(cls=NestedEncoder)
    def timing_capabilites_get(self):
        pass

    # For now just for test
    def current_time_get(self):
        return time.time()
