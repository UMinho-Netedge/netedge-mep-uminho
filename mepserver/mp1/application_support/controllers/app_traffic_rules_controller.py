import sys
import cherrypy

sys.path.append("../../")
from mp1.models import *


class AppTrafficRulesController:
    @json_out(cls=NestedEncoder)
    def traffic_rules_get(self):
        pass

    def traffic_rule_get_with_traffic_rule_id(self):
        pass

    def traffic_rules_put(self):
        pass