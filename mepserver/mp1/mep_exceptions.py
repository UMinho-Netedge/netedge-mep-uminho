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

from urllib import response
#from mp1.models import ProblemDetails
import ast
import json

class InvalidQuery(Exception):
    #cherrypy.response.status = 400
    #errorvar = ProblemDetails(type='tipo', title='titulo', status='estado', detail='detalhe', instance='instancia')
    
    '''
    def handle(ex, req, resp, param):
        print("AQUI!!!!!")
        resp.status = 437
        response = json.loads(json.dumps(ast.literal_eval(str(ex))))
        resp.body = json.dumps(response)
        
    '''
    def __init__(self, error=437, message="Erro de exclusao mutua"):
        self.error = error
        self.message = message
        super().__init__(self.error, self.message)

    #pass




class InvalidGrantType(Exception):
    pass
