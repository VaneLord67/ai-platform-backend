# 面向多AI模型部署管理的微服务平台
基于TensorRT深度学习推理架构和Nameko基础微服务库，设计并实现一个面向多AI模型部署管理的微服务平台。
针对检测、识别、跟踪等典型AI模型部署，封装多输入形式（图像序列和IP地址）的接口服务，
提供服务启停、服务发现、负载均衡、服务多实例等微服务基础功能， 并实现Web管理平台页面，
包括微服务算法参数配置与测试模拟、任务请求/设备状况/流量可视化监控、一键启停控制、任务阻塞预警、硬件资源红线预警、报错前台提示等功能。

# build step
## python依赖库
```text
# 安装Python库
pip install flask flask-cors flask_nameko Flask-SocketIO DBUtils mysqlclient mysql-connector-python casbin nameko minio psutil GPutil redis paho-mqtt PyJWT websocket-client
conda install -c conda-forge opencv
```

## Docker安装
[Ubuntu Docker安装文档](https://www.runoob.com/docker/ubuntu-docker-install.html)

[Windows Docker安装文档](https://www.runoob.com/docker/windows-docker-install.html)

安装好Docker后，按下面的步骤运行起所需容器

### 1. MySQL
```shell
docker run -d --name ai-mysql --env=MYSQL_ROOT_PASSWORD=abc123 -e TZ=Asia/Shanghai -p 3307:3306 mysql:latest
# 初始化数据库
docker exec -it ai-mysql mysql -uroot -pabc123 < sql/ai-platform.sql
# 初始化casbin policy
cat base_policy.csv > policy.csv
```

### 2. RabbitMQ
```shell
docker run --privileged -d --name ai-rabbitmq -p 1884:1883 -p 5673:5672 -p 15673:15672 rabbitmq:3.12-management
# 开启mqtt协议支持：
docker exec -it ai-rabbitmq rabbitmq-plugins enable rabbitmq_mqtt
```

### 3. minio
```shell
# 这里的挂载点选择服务器上磁盘空间较大的位置
# 下面用的挂载点为/media/hx/1a19b641-b996-4b88-b2ca-1cc3ded71d49/ai-platform/minio_volume
docker run -d -v /media/hx/1a19b641-b996-4b88-b2ca-1cc3ded71d49/ai-platform/minio_volume/data:/bitnami/minio/data -v /media/hx/1a19b641-b996-4b88-b2ca-1cc3ded71d49/ai-platform/minio_volume/certs:/certs --name ai-minio -p 9000:9000 -p 9001:9001 -e MINIO_DEFAULT_BUCKETS="ai-platform" -e MINIO_ROOT_USER="minio-root-user" -e MINIO_ROOT_PASSWORD="minio-root-password" bitnami/minio:latest
创建好后访问浏览器上localhost:9001进行登录，登录用户名为minio-root-user，密码为minio-root-password
新建一个Access Key，将Access Key和Secret Key复制到config.json中

如果发现容器没跑起来，报错权限不足，则
cd 挂载点
sudo chmod -R ug+rw certs
sudo chmod -R ug+rw data 
```

### 4. redis
```shell
# 这里的挂载点选择服务器上磁盘空间较大的位置
# 下面用的挂载点为/media/hx/1a19b641-b996-4b88-b2ca-1cc3ded71d49/ai-platform/redis_volume
cd 挂载点
sudo chmod -R ug+rw redis_volume
docker run --privileged -d -v /media/hx/1a19b641-b996-4b88-b2ca-1cc3ded71d49/ai-platform/redis_volume:/data --rm --name ai-redis -p 6379:6379 redis
```

### 5. webrtc-streamer
```shell
docker run --network=host -d --name ai-webrtc mpromonet/webrtc-streamer
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
编译4.8.0版本的openCV

[C++ OpenCV Release](https://opencv.org/releases/)

```shell
git clone git@github.com:opencv/opencv.git
git checkout 4.8.0
cd opencv
mkdir build && cd build
cmake .. -D BUILD_opencv_world=ON
# cmake .. -D CMAKE_BUILD_TYPE=Debug -D BUILD_opencv_world=OFF -D WITH_FFMPEG=ON
make
# make后在build/lib目录下查看是否生成了libopencv_world.so.4.8.0
```

## Pybind安装
[Pybind install](https://pybind11.readthedocs.io/en/stable/installing.html)

## 修改配置文件
1. config.json: 按照实际的端口号填写，注意minio_url要改为服务器的公网ip或局域网ip
2. nameko_config.yaml: 修改AMQP_URI

## python Flask启动
```cmd
直接在项目根目录下运行cgi/main.py即可
export PYTHONPATH=${代码根目录路径}
python cgi/main.py
```

## 微服务启动
```cmd
# 在项目根目录下
cd ~/ai-platform/ai-platform-backend
export PYTHONPATH=$PWD
conda activate ai-platform
# ubuntu下为conda activate ai-platform_3.8

nameko run --config nameko_config.yaml microservice.manage:ManageService
nameko run --config nameko_config.yaml microservice.monitor:MonitorService
nameko run --config nameko_config.yaml microservice.object_storage:ObjectStorageService
nameko run --config nameko_config.yaml microservice.user:UserService
nameko run --config nameko_config.yaml microservice.mqtt_listener:MQTTListenerService

nameko run --config nameko_config.yaml microservice.detection:DetectionService
# ubuntu下为 nameko run --config nameko_config.yaml microservice.detection_hx:DetectionService
nameko run --config nameko_config.yaml microservice.track:TrackService
# ubuntu下为 nameko run --config nameko_config.yaml microservice.track_hx:TrackService
nameko run --config nameko_config.yaml microservice.recognition:RecognitionService
```
