# 面向多AI模型部署管理的微服务平台
基于TensorRT深度学习推理架构和Nameko基础微服务库，设计并实现一个面向多AI模型部署管理的微服务平台。
针对检测、识别、跟踪等典型AI模型部署，封装多输入形式（图像序列和IP地址）的接口服务，
提供服务启停、服务发现、负载均衡、服务多实例等微服务基础功能， 并实现Web管理平台页面，
包括微服务算法参数配置与测试模拟、任务请求/设备状况/流量可视化监控、一键启停控制、任务阻塞预警、硬件资源红线预警、报错前台提示等功能。

# 依赖
```text
flask
flask-cors 
flask_nameko
Flask-SocketIO
nameko 
opencv 
minio 
psutil 
GPutil 
redis
```

# RabbitMQ
docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3.12-management

# minio
docker run -d --name ai-minio -p 9000:9000 -p 9001:9001 -e MINIO_ROOT_USER="minio-root-user" -e MINIO_ROOT_PASSWORD="minio-root-password" bitnami/minio:latest

# redis
docker run -d --rm --name ai-redis -p 6379:6379 redis

# cgi
```cmd
$env:FLASK_APP = "cgi/main.py"
python -m flask run --port=8086
```

# microservice
```cmd
nameko run microservice.manage:ManageService
nameko run microservice.object_storage:ObjectStorageService
nameko run microservice.detection:DetectionService
nameko run microservice.track:TrackService
nameko run microservice.recognition:RecognitionService
nameko run microservice.user:UserService
nameko run microservice.monitor:MonitorService
```

# yolo
```cmd
# 推理图片
--model=E:/GraduationDesign/yolov8n.trt --size=640 --batch_size=1  --img=E:/GraduationDesign/tensorrt-alpha/data/6406402.jpg --show --savePath=E:\GraduationDesign\tensorOutput
# 推理视频
--model=E:/GraduationDesign/yolov8n.trt --size=640 --batch_size=8  --video=E:/GraduationDesign/tensorrt-alpha/data/people.mp4 --show --savePath=E:\GraduationDesign\tensorOutput
```

```cmd
"--model=E:/GraduationDesign/yolov8n.trt" --size=640 --batch_size=1  --img=E:/GraduationDesign/tensorrt-alpha/data/6406402.jpg --show --savePath=E:\GraduationDesign\tensorOutput

```
