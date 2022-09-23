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

from abc import ABC, abstractmethod


class DatabaseBase(ABC):
    """
    Specification if at some point there is a decision to change to another database (this by no means totally enforces
    the structure of a database connection. It serves as a sort of guideline)
    """

    @abstractmethod
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.client = None

    @abstractmethod
    def connect(self, thread_index: int):
        """
        Connect to the database

        :param thread_index: CherryPy Thread_Index (used to avoid overloading the database when cherrypy creates it's threads)
        :type thread_index: int
        :return: Instance of DatabaseBase
        :rtype: DatabaseBase
        """
        pass

    @abstractmethod
    def disconnect(self):
        """
        Disconnect from the database
        :return: None
        """
        pass

    """
    The rest of the methods are database dependent
    """
