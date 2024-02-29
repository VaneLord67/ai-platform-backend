import json
import sys
from datetime import timedelta

from nameko.standalone.rpc import ClusterRpcProxy

from common import config
from common.log import LOGGER
from common.util import create_redis_client
from microservice.mqtt_storage import MQTTStorage
from model.hyperparameter import Hyperparameter


def parse_camera_command_args():
    args = sys.argv[1:]
    print("Received arguments:", args)
    if len(args) != 9:
        raise ValueError('args length error')
    camera_id, hyperparameters_json_str, stop_signal_key, \
        camera_data_queue_name, log_key, task_id, service_unique_id, \
        camera_output_path, camera_output_json_path = args
    hp_dict_list = json.loads(hyperparameters_json_str)
    hps = []
    for hp_dict in hp_dict_list:
        hp = Hyperparameter().from_dict(hp_dict)
        hps.append(hp)
    return camera_id, hps, stop_signal_key, \
        camera_data_queue_name, log_key, task_id, service_unique_id, \
        camera_output_path, camera_output_json_path


def after_camera_call(camera_output_path, camera_output_json_path, task_id, service_name, service_unique_id):
    with ClusterRpcProxy(config.get_rpc_config()) as cluster_rpc:
        video_url = cluster_rpc.object_storage_service.upload_object(camera_output_path)
        json_url = cluster_rpc.object_storage_service.upload_object(camera_output_json_path)

        mqtt_storage = MQTTStorage()
        mqtt_storage.setup()
        msg = {
            'task_id': task_id,
            'video_url': video_url,
            'json_url': json_url,
        }
        LOGGER.info(f"msg = {msg}")
        mqtt_storage.push_message(json.dumps(msg))
        mqtt_storage.client.loop(timeout=1)
        cluster_rpc.manage_service.change_state_to_ready(service_name, service_unique_id)
        LOGGER.info(f"camera task done, task_id:{task_id}")

