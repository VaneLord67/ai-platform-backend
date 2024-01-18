# 面向多AI模型部署管理的微服务平台
基于TensorRT深度学习推理架构和Nameko基础微服务库，设计并实现一个面向多AI模型部署管理的微服务平台。
针对检测、识别、跟踪等典型AI模型部署，封装多输入形式（图像序列和IP地址）的接口服务，
提供服务启停、服务发现、负载均衡、服务多实例等微服务基础功能， 并实现Web管理平台页面，
包括微服务算法参数配置与测试模拟、任务请求/设备状况/流量可视化监控、一键启停控制、任务阻塞预警、硬件资源红线预警、报错前台提示等功能。

# build step
## python依赖库
```text
# 使用pip install安装以下库
flask
flask-cors
flask_nameko
Flask-SocketIO
DBUtils
mysqlclient
casbin
nameko
opencv
minio
psutil
GPutil
redis
paho-mqtt
```

## Docker安装
[Ubuntu Docker安装文档](https://www.runoob.com/docker/ubuntu-docker-install.html)

[Windows Docker安装文档](https://www.runoob.com/docker/windows-docker-install.html)

安装好Docker后，按下面的步骤运行起所需容器

### 1. MySQL
```shell
docker run -d --env=MYSQL_ROOT_PASSWORD=abc123 -p 3307:3306 mysql:latest
```

### 2. RabbitMQ
```shell
docker run -d --name ai-rabbitmq -p 1883:1883 -p 5672:5672 -p 15672:15672 rabbitmq:3.12-management
# 开启mqtt协议支持：
docker exec -it ai-rabbitmq rabbitmq-plugins enable rabbitmq_mqtt
```

### 3. minio
```shell
docker run -d --name ai-minio -p 9000:9000 -p 9001:9001 -e MINIO_ROOT_USER="minio-root-user" -e MINIO_ROOT_PASSWORD="minio-root-password" bitnami/minio:latest
```

### 4. redis
```shell
docker run -d --rm --name ai-redis -p 6379:6379 redis
```

## 驱动、CUDA、CUDNN安装
按照NVIDIA官方文档安装显卡可支持的NVIDIA驱动和CUDA、CUDNN

## C++ TensorRT安装
安装8.6.1.6的TensorRT

[NVIDIA TensorRT官网](https://developer.nvidia.com/tensorrt)

## TensorRT模型转化
下载YoloV8的onnx模型：[onnx模型下载地址](https://share.weiyun.com/3T3mZKBm)

使用安装好的tensorRT bin目录下的trtexec程序将onnx转化为trt：
```shell
${tensorRT安装目录}/bin/trtexec --onnx=${YoloV8 onnx路径}  --saveEngine=${trt目标路径}  --buildOnly --minShapes=images:1x3x640x640 --optShapes=images:4x3x640x640 --maxShapes=images:8x3x640x640
```


## C++ OpenCV安装
安装4.8.0版本的openCV

[C++ OpenCV Release](https://opencv.org/releases/)

## 编译C++项目产生Python模块文件
### cpp_redis
这是手动编译cpp_redis的方法，如果你熟悉cmake的话，可以在下面的cpp_ai_utils项目中编写cmake将cpp_redis作为子项目。

[cpp_redis安装文档](https://github.com/cpp-redis/cpp_redis/wiki/Installation)

### cpp_ai_utils
这是c++项目中一些公共能力的封装，提供了redis连接、jsonl文件结果写入等。

将上面编译好的cpp_redis的lib目录、头文件目录配置好，编译cpp_ai_utils产生静态lib库。
### app_yolo_cls
下载cls onnx放到app_yolo_cls项目下

[yolov8n-cls.onnx下载地址](https://docs.ultralytics.com/zh/tasks/classify/#_2)

修改app_yolo_cls中的modelPath，依赖cpp_ai_utils的lib，
编译产生Python模块文件app_yolo_cls，在linux平台下后缀名为.so，在win平台下后缀名为.pyd

将app_yolo_cls放在ai-platform-backend/ais文件夹下
### app_yolo
修改app_yolo中的modelPath为TensorRT模型转化步骤中产生的trt文件路径。

依赖cpp_ai_utils的lib，编译产生Python模块文件app_yolo，在linux平台下后缀名为.so，在win平台下后缀名为.pyd

将app_yolo放在ai-platform-backend/ais文件夹下
### 其他c++运行时动态库依赖
我个人开发用的win平台上：cudart64_110.dll、nvinfer.dll、opencv_world480.dll、openh264-1.8.0-win64.dll

linux平台下，cudart64可以在CUDA安装文件夹的bin目录下找到，nvinfer可以在tensorRT安装目录lib下找到，
opencv可以在opencv安装目录的bind目录下找到，
openh264-1.8.0下载地址：https://github.com/cisco/openh264/releases/tag/v1.8.0

将这些动态库放到ai-platform-backend/ais文件夹下
## python Flask启动
```cmd
直接在项目根目录下运行cgi/main.py即可
python cgi/main.py
```

## 微服务启动
```cmd
# 在项目根目录下
nameko run microservice.manage:ManageService
nameko run microservice.monitor:MonitorService
nameko run microservice.object_storage:ObjectStorageService
nameko run microservice.user:UserService

nameko run microservice.detection:DetectionService
nameko run microservice.track:TrackService
nameko run microservice.recognition:RecognitionService
```

# 附录
附tensorRT-Alpha仓库中进行yolo调用的命令行参数：
```cmd
# 推理图片
--model=E:/GraduationDesign/yolov8n.trt --size=640 --batch_size=1  --img=E:/GraduationDesign/tensorrt-alpha/data/6406402.jpg --show --savePath=E:\GraduationDesign\tensorOutput
# 推理视频
--model=E:/GraduationDesign/yolov8n.trt --size=640 --batch_size=8  --video=E:/GraduationDesign/tensorrt-alpha/data/people.mp4 --show --savePath=E:\GraduationDesign\tensorOutput
```
