import sys
import cherrypy

sys.path.append("../../")
from mp1.models import *


class AppDnsRulesController:
    @json_out(cls=NestedEncoder)
    def dns_rules_get(self):
        pass

    def dns_rule_get_with_dns_rule_id(self):
        pass

    def dns_rules_put(self):
        pass