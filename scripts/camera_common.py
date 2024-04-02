import json
import logging
import sys
from datetime import datetime

from nameko.standalone.rpc import ClusterRpcProxy

from common import config
from common.util import is_integer
from microservice.mqtt_storage import MQTTStorage
from model.hyperparameter import Hyperparameter
from model.task import Task


def parse_camera_command_args():
    args = sys.argv[1:]
    print("Received arguments:", args)
    if len(args) != 7:
        raise ValueError('args length error')
    camera_id, hyperparameters_json_str, namespace, task_id, service_unique_id, \
        camera_output_path, camera_output_json_path = args
    if is_integer(camera_id):
        camera_id = int(camera_id)
    hp_dict_list = json.loads(hyperparameters_json_str)
    hps = []
    for hp_dict in hp_dict_list:
        hp = Hyperparameter().from_dict(hp_dict)
        hps.append(hp)
    return camera_id, hps, namespace, task_id, service_unique_id, \
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
        logging.info(f"msg = {msg}")
        insert_async_task_request_log(cluster_rpc, msg)
        mqtt_storage.push_message(json.dumps(msg))
        mqtt_storage.client.loop(timeout=1)
        cluster_rpc.manage_service.change_state_to_ready(service_name, service_unique_id)
        logging.info(f"camera task done, task_id:{task_id}")


def insert_async_task_request_log(rpc_obj, msg):
    task_id = msg['task_id']
    task_dict: dict = rpc_obj.monitor_service.get_task_by_task_id(task_id)
    if task_dict is None:
        return
    task: Task = Task().from_dict(task_dict)
    request_duration = datetime.now() - task.time
    log_data = {
        'user_id': task.user_id,
        'method': "POST",
        'path': task.path,
        'status_code': 200,
        'duration': request_duration.total_seconds(),
        'response_json': msg,
        'time': datetime.now(),
        'input_mode': task.input_mode
    }
    rpc_obj.monitor_service.insert_request_log(log_data)
