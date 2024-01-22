from nameko.timer import timer

from microservice.mqtt_storage import MQTTStorage


class MQTTListenerService:
    name = "mqtt_listener_service"

    mqtt_storage = MQTTStorage()

    # unit: seconds
    @timer(interval=1)
    def listen_message_on_mqtt(self):
        self.mqtt_storage.listen_message()

