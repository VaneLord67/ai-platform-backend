export -n http_proxy
export -n https_proxy
export PYTHONPATH=$PWD
export AI_PLATFORM_VENV_NAME=ai-platform_3.8
conda activate $AI_PLATFORM_VENV_NAME

nohup python cgi/main.py > log_cgi &
nohup nameko run --config nameko_config.yaml microservice.manage:ManageService > log_manage  &
nohup nameko run --config nameko_config.yaml microservice.monitor:MonitorService > log_monitor &
nohup nameko run --config nameko_config.yaml microservice.object_storage:ObjectStorageService > log_object_storage &
nohup nameko run --config nameko_config.yaml microservice.user:UserService > log_user &

nohup nameko run --config nameko_config.yaml microservice.detection_hx:DetectionService > log_detection &
nohup nameko run --config nameko_config.yaml microservice.track_hx:TrackService > log_track &

