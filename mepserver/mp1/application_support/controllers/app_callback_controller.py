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

import cherrypy
import requests
# from urllib import request, parse
from mp1.models import *
import time
from cherrypy.process.plugins import BackgroundTask
from kubernetes import client, config, utils


class CallbackController:
    @staticmethod
    def execute_callback(
        subscription: AppTerminationNotificationSubscription,
        notification: AppTerminationNotification,
        sleep_time: int = 10,
    ):
        """
        Send the callback to the specified url (i.e callbackreference)
        Start a cherrypy BackgroundTask https://docs.cherrypy.dev/en/latest/pkg/cherrypy.process.plugins.html
        Pass the callbackreference (i.e url to call) and the data

        :param availability_notifications: The python object containing the callbackreference
        :type availability_notifications: AvailabilityNotification
        :param data: Data containing the services that match the filtering criteria of the subscriber
        :type data: Json/Dict
        """
        if notification:
            callback_task = BackgroundTask(
                interval=0,
                function=CallbackController._callback_function,
                args=[subscription, notification, sleep_time],
                bus=cherrypy.engine,
            )
            # Add the callback_task to itself to allow to cancel itself
            # (needed since BackgroundTask is usually repeatable)
            callback_task.args.insert(0, callback_task)
            callback_task.start()

    @staticmethod
    def _callback_function(
        task,
        subscription: AppTerminationNotificationSubscription,
        notification: AppTerminationNotification,
        sleep_time: int,
    ):
        """
        :param task: Reference to the background task itself
        :type task: BackgroundTask
        :param availability_notifications:  Used to obtain the callback references
        :type availability_notifications: SerAvailabilityNotificationSubscription or List of SerAvailabilityNotificationSubscription (each one contains a callbackreference)
        :param data: Data containing the information to be sent in a callback
        :type data: Json/Dict
        """
        cherrypy.log("Starting callback function")
        # Wait for a bit since client might still be receiving the answer from the subscriptions and thus might
        # not be ready to receive the callback
        time.sleep(sleep_time)
        requests.post(
            subscription.callbackReference,
            data=json.dumps(notification, cls=NestedEncoder),
            headers={"Content-Type": "application/json"},
        )
        # httpreq = request.Request(subscription.callbackReference, method="POST")
        # httpreq.add_header('Content-Type', 'application/json')
        # response = request.urlopen(httpreq, data=notification.to_json())

        task.cancel()

    def configure_trafficRules(
        appInstanceId:str,
        trafficRules: List(TrafficRule),
        sleep_time: int = 10,
    ):
        for rule in trafficRules:
            callback_task = BackgroundTask(
                interval=0,
                function=CallbackController._configureRule,
                args=[rule, sleep_time],
                bus=cherrypy.engine,
            )
            # Add the callback_task to itself to allow to cancel itself
            # (needed since BackgroundTask is usually repeatable)
            callback_task.args.insert(0, callback_task)
            callback_task.start()
    
    @staticmethod
    def _configureRule(
        task,
        appInstanceId: str,
        trafficRule: TrafficRule,
        sleep_time: int,
    ):

        cherrypy.log("Starting rule configuration function")

        time.sleep(sleep_time)
        config.load_incluster_config()
        k8s_client = client.ApiClient()
        networkPolicy = trafficRuleToNetworkPolicy(appInstanceId=appInstanceId, data=trafficRule.to_json())
        utils.create_from_dict(k8s_client, networkPolicy)


        task.cancel()

    @staticmethod
    def create_secret(
        task,
        appInstanceId: str,
        data: dict,
        sleep_time: int,
    ):

        cherrypy.log("Creating secret with MEC App token")

        time.sleep(sleep_time)
        
        secret = {
            "apiVersion":"v1",
            "kind": "Secret",
            "metadata": {
                "name": "%s-secret" %appInstanceId,
                "namespace": "%s" %appInstanceId,
            },
            "type": "Opaque",
            "data": data
        }

        config.load_incluster_config()
        k8s_client = client.ApiClient()
        utils.create_from_dict(k8s_client, secret)


        task.cancel()