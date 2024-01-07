import multiprocessing
from datetime import timedelta
from typing import Union

import redis
from nameko.standalone.rpc import ClusterRpcProxy

from common import config
from common.util import download_file
from model.hyperparameter import Hyperparameter
from model.service_info import ServiceReadyState, ServiceRunningState
from model.support_input import SupportInput


def call_init(service_info, supportInput, unique_id):
    output = {
        'busy': False,
        'unique_id': unique_id,
    }
    if service_info.state != ServiceReadyState:
        output['busy'] = True
        return output
    service_info.task_type = supportInput.type
    service_info.state = ServiceRunningState
    return output


def parse_hyperparameters(args):
    hyperparameters = []
    if 'hyperparameters' in args:
        hps = args['hyperparameters']
        for hp in hps:
            hyperparameters.append(Hyperparameter().from_dict(hp))
    return hyperparameters


def after_video_call(video_output_path, video_output_json_path, task_id, service_name, service_unique_id):
    with ClusterRpcProxy(config.get_rpc_config()) as cluster_rpc:
        video_url = cluster_rpc.object_storage_service.upload_object(video_output_path)
        json_url = cluster_rpc.object_storage_service.upload_object(video_output_json_path)
        client: Union[redis.StrictRedis, None] = redis.StrictRedis.from_url(config.config.get("redis_url"))
        mapping = {
            "video_url": video_url,
            "json_url": json_url,
        }
        client.hset(name=task_id, mapping=mapping)
        client.expire(name=task_id, time=timedelta(hours=24))
        cluster_rpc.manage_service.change_state_to_ready(service_name, service_unique_id)
        print(f"video task done, task_id:{task_id}")


def handle_video(video_handler, args, hyperparameters, unique_id):
    supportInput = SupportInput().from_dict(args['supportInput'])
    video_url = supportInput.value
    video_progress_key = args['videoProgressKey']

    video_name, video_path = download_file(video_url)
    if 'taskId' not in args:
        raise ValueError("task id not found!")
    task_id = args['taskId']
    output_video_path = f"temp/output_{video_name}"
    output_jsonl_path = f"temp/output_{task_id}.jsonl"

    multiprocessing.Process(target=video_handler, daemon=True,
                            args=[video_path, output_video_path, output_jsonl_path, video_progress_key,
                                  hyperparameters, task_id, unique_id]).start()


def handle_camera(camera_handler, args, hyperparameters):
    supportInput = SupportInput().from_dict(args['supportInput'])
    camera_id = supportInput.value
    stop_signal_key = args['stopSignalKey']
    camera_data_queue_name = args['queueName']
    log_key = args['logKey']
    # self.redis_storage.client.expire(name=camera_data_queue_name, time=timedelta(hours=24))
    multiprocessing.Process(target=camera_handler, daemon=True,
                            args=[camera_id, hyperparameters, stop_signal_key,
                                  camera_data_queue_name, log_key]).start()
