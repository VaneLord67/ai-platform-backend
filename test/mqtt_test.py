import time
import paho.mqtt.client as mqtt

from common import config

if __name__ == '__main__':
    # MQTT Broker的地址和端口
    broker_address = config.config.get("mqtt_host")
    port = config.config.get("mqtt_port")

    # 定义发布者
    def publish_message(client, topic, message):
        print(f"Publishing message '{message}' to topic '{topic}'")
        client.publish(topic, message)


    # 定义订阅者
    def on_message(client, userdata, msg):
        print(f"Received message '{msg.payload}' on topic '{msg.topic}'")


    # 创建MQTT客户端实例
    client = mqtt.Client()

    # 连接到MQTT Broker
    client.connect(broker_address, port)

    # 订阅主题
    topic_to_subscribe = "example/topic"
    client.subscribe(topic_to_subscribe)
    client.on_message = on_message

    # 发布消息
    topic_to_publish = "example/topic"
    message_to_publish = "Hello, MQTT!"

    publish_message(client, topic_to_publish, message_to_publish)

    # 等待接收消息
    print(f"Waiting for messages on topic '{topic_to_subscribe}'...")
    client.loop_start()
    time.sleep(5)  # 等待5秒，让订阅者有足够的时间接收消息
    client.loop_stop()

    # 断开连接
    client.disconnect()
