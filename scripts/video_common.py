from datetime import timedelta

from nameko.standalone.rpc import ClusterRpcProxy

from common import config
from common.log import LOGGER
from common.util import create_redis_client
from microservice.mqtt_storage import MQTTStorage


def after_video_call(video_output_path, video_output_json_path, task_id, service_name, service_unique_id):
    """
    由于多进程进行传参时，无法将rpc对象以及redis client对象进行传递，所以只能重新创建对象来进行服务调用。
    如果你有更好的方法，可以将其改进。
    """
    with ClusterRpcProxy(config.get_rpc_config()) as cluster_rpc:
        video_url = cluster_rpc.object_storage_service.upload_object(video_output_path)
        json_url = cluster_rpc.object_storage_service.upload_object(video_output_json_path)
        client = create_redis_client()
        mapping = {
            "video_url": video_url,
            "json_url": json_url,
        }
        client.hset(name=task_id, mapping=mapping)
        client.expire(name=task_id, time=timedelta(hours=24))
        mqtt_storage = MQTTStorage()
        mqtt_storage.setup()
        msg = {
            'task_id': task_id,
            'video_url': video_url,
            'json_url': json_url,
        }
        mqtt_storage.push_message(json.dumps(msg))
        mqtt_storage.client.loop(timeout=1)
        cluster_rpc.manage_service.change_state_to_ready(service_name, service_unique_id)
        LOGGER.info(f"video task done, task_id:{task_id}")
