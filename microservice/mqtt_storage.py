from typing import Union

import paho.mqtt.client as mqtt
from nameko.extensions import DependencyProvider

from common.config import config


class MQTTStorage(DependencyProvider):

    def __init__(self, topic="ai-platform"):
        self.client: Union[mqtt.Client, None] = None
        self.topic = topic

    def setup(self):
        broker_address = config.config.get("mqtt_host")
        port = config.config.get("mqtt_port")
        self.client = mqtt.Client()
        self.client.connect(broker_address, port)

    def stop(self):
        if self.client:
            self.client.disconnect()

    def get_dependency(self, worker_ctx):
        return self

    def push_message(self, msg):
        self.client.publish(self.topic, msg)
        self.client.loop(timeout=0.1)

    @staticmethod
    def on_message(client, userdata, msg):
        print(f"Received message {msg.payload} on topic: {msg.topic}")

    def listen_message(self):
        self.client.on_message = self.on_message
        self.client.subscribe(self.topic)
        self.client.loop(timeout=0.1)

    def __del__(self):
        if self.client:
            self.client.disconnect()
