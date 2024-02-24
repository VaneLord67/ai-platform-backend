# 面向多AI模型部署管理的微服务平台
基于TensorRT深度学习推理架构和Nameko基础微服务库，设计并实现一个面向多AI模型部署管理的微服务平台。
针对检测、识别、跟踪等典型AI模型部署，封装多输入形式（图像序列和IP地址）的接口服务，
提供服务启停、服务发现、负载均衡、服务多实例等微服务基础功能， 并实现Web管理平台页面，
包括微服务算法参数配置与测试模拟、任务请求/设备状况/流量可视化监控、一键启停控制、任务阻塞预警、硬件资源红线预警、报错前台提示等功能。

# build step
## python依赖库
```text
# 安装Python库
pip install flask flask-cors flask_nameko Flask-SocketIO DBUtils mysqlclient mysql-connector-python casbin nameko minio psutil GPutil redis paho-mqtt PyJWT
conda install -c conda-forge opencv
```

## Docker安装
[Ubuntu Docker安装文档](https://www.runoob.com/docker/ubuntu-docker-install.html)

[Windows Docker安装文档](https://www.runoob.com/docker/windows-docker-install.html)

安装好Docker后，按下面的步骤运行起所需容器

### 1. MySQL
```shell
docker run -d --name ai-mysql --env=MYSQL_ROOT_PASSWORD=abc123 -p 3307:3306 mysql:latest
```

### 2. RabbitMQ
```shell
docker run --privileged -d --name ai-rabbitmq -p 1883:1883 -p 5672:5672 -p 15672:15672 rabbitmq:3.12-management
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
docker run --privileged -d --rm --name ai-redis -p 6379:6379 redis
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

## 编译C++项目产生Python模块文件
### cpp_redis
[cpp_redis安装文档](https://github.com/cpp-redis/cpp_redis/wiki/Installation)

```shell
git clone git@github.com:Cylix/cpp_redis.git
cd cpp_redis
git submodule init && git submodule update
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make
```

```shell
# 如果在cmake环节出现字样：
# CMake Error: install(EXPORT "cpp_redis" ...) includes target "cpp_redis" which requires target "tacopie" that is not in any export set.
# 则在cpp_redis目录执行以下命令后再cmake
cd tacopie
git fetch origin pull/5/head:cmake-fixes
git checkout cmake-fixes
cd ..
```

### spdlog
[spdlog安装](https://github.com/gabime/spdlog)

git clone下载其头文件库即可，留待后续使用。

```shell
git clone git@github.com:gabime/spdlog.git
```

### cpp_ai_utils
[cpp_ai_utils github地址](https://github.com/VaneLord67/cpp_ai_utils)

这是c++项目中一些公共能力的封装，提供了redis连接、jsonl文件结果写入等。

依赖项目有OpenCV、cpp_redis、spdlog，编译cpp_ai_utils产生libcpp_ai_utils.a。

```shell
git clone git@github.com:VaneLord67/cpp_ai_utils.git
cd cpp_ai_utils/cpp_ai_utils
mkdir build && cd build
# 需要修改CMakeLists.txt中的头文件路径、库路径、动态链接库名
cmake ..
make
```

### app_yolo_cls
下载cls onnx放到app_yolo_cls项目下

[yolov8n-cls.onnx下载地址](https://docs.ultralytics.com/zh/tasks/classify/#_2)

[app_yolo_cls github地址](https://github.com/VaneLord67/yolov8-cls-OpenCV)

修改app_yolo_cls中的modelPath
编译产生Python模块文件libapp_yolo_cls.so

```shell
git clone git@github.com:VaneLord67/ai-platform-yolov8-cls-OpenCV.git
cd ai-platform-yolov8-cls-OpenCV
mkdir build && cd build
# 修改cmake中的头文件路径、库路径
cmake ..
make
```

将libapp_yolo_cls.so放在ai-platform-backend/ais文件夹下

### Eigen3.3.9

[gitlab地址](https://gitlab.com/libeigen/eigen/-/releases/3.3.9)

仅头文件库，git clone后留待后续使用

```shell
git clone git@gitlab.com:libeigen/eigen.git
git checkout 3.3.9
mkdir build && cd build
cmake ..
make
```

### ByteTrack-cpp

[github地址](https://github.com/Vertical-Beach/ByteTrack-cpp)

```shell
# 依赖Eigen3.3.9
# 将这一行的SHARED改为STATIC，使用Cmake编译
add_library(${PROJECT_NAME} SHARED
```

### app_yolo
[app_yolo github地址](https://github.com/VaneLord67/ai-platform-yolov8)

修改app_yolo中的modelPath为TensorRT模型转化步骤中产生的trt文件路径。

依赖OpenCV、TensorRT、CUDA、pybind、cpp_ai_utils、ByteTrack，
编译产生Python模块文件libapp_yolo.so

将libapp_yolo.so放在ai-platform-backend/ais文件夹下
### 其他c++运行时动态库依赖
我个人开发用的win平台上：cudart64_110.dll、nvinfer.dll、opencv_world480.dll、openh264-1.8.0-win64.dll

linux平台下，cudart64可以在CUDA安装文件夹的bin目录下找到，nvinfer可以在tensorRT安装目录lib下找到，
libopencv_world.so在编译后build/lib目录下找到
openh264-1.8.0下载地址：https://github.com/cisco/openh264/releases/tag/v1.8.0

将这些动态库放到ai-platform-backend/ais文件夹下
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
conda activate ai-platform

nameko run --config nameko_config.yaml microservice.manage:ManageService
nameko run --config nameko_config.yaml microservice.monitor:MonitorService
nameko run --config nameko_config.yaml microservice.object_storage:ObjectStorageService
nameko run --config nameko_config.yaml microservice.user:UserService
nameko run --config nameko_config.yaml microservice.mqtt_listener:MQTTListenerService

nameko run --config nameko_config.yaml microservice.detection:DetectionService
nameko run --config nameko_config.yaml microservice.track:TrackService
nameko run --config nameko_config.yaml microservice.recognition:RecognitionService
```
