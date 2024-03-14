#!bin/bash
# Check if the script is not run with interactive bash
if [[ "$-" != *i* ]]; then
    echo "Please run this script with 'bash -i' for interactive mode."
    exit 1
fi

cd ~
mkdir ai-platform
export MYSQL_PORT=3307
export MQTT_PORT=1884
export RABBITMQ_PORT=5673
export RABBITMQ_WEB_PORT=15673
export MINIO_PORT=9000
export MINIO_CONSOLE_PORT=9001
export REDIS_PORT=6379
export MINIO_DEFAULT_BUCKETS=ai-platform
export MINIO_ROOT_USER=minio-root-user
export MINIO_ROOT_PASSWORD=minio-root-password
export DOCKER_VOLUME_ROOT=/media/hx/1a19b641-b996-4b88-b2ca-1cc3ded71d49/ai-platform
export MYSQL_ROOT_PASSWORD=abc123
export AI_PLATFORM_VENV_NAME=ai-platform_3.8

mkdir -p $DOCKER_VOLUME_ROOT/minio_volume/data
mkdir -p $DOCKER_VOLUME_ROOT/minio_volume/certs:/certs
mkdir -p $DOCKER_VOLUME_ROOT/redis_volume

sudo chmod -R ug+rw $DOCKER_VOLUME_ROOT/minio_volume/certs
sudo chmod -R ug+rw $DOCKER_VOLUME_ROOT/minio_volume/data
sudo chmod -R ug+rw $DOCKER_VOLUME_ROOT/redis_volume

# install python environment
conda create -n $AI_PLATFORM_VENV_NAME python=3.8
conda activate $AI_PLATFORM_VENV_NAME
pip install flask flask-cors flask_nameko Flask-SocketIO DBUtils mysqlclient mysql-connector-python casbin nameko minio psutil GPutil redis paho-mqtt PyJWT
conda install -c conda-forge opencv

# install docker
if command -v docker &> /dev/null; then
    echo "Docker 已安装"
    docker --version
    sudo systemctl status docker
else
    echo "Docker 未安装，开始安装Docker"
    curl -fsSL https://test.docker.com -o test-docker.sh
    sudo sh test-docker.sh
fi

# run docker containers
sudo docker run -d --name ai-mysql -e TZ=Asia/Shanghai --env=MYSQL_ROOT_PASSWORD=$MYSQL_ROOT_PASSWORD -p $MYSQL_PORT:3306 mysql:latest
sudo docker run --privileged -d --name ai-rabbitmq -p $MQTT_PORT:1883 -p $RABBITMQ_PORT:5672 -p $RABBITMQ_WEB_PORT:15672 rabbitmq:3.12-management
sudo docker exec -it ai-rabbitmq rabbitmq-plugins enable rabbitmq_mqtt # enable rabbitmq mqtt protocol
sudo docker run -d -v $DOCKER_VOLUME_ROOT/minio_volume/data:/bitnami/minio/data -v $DOCKER_VOLUME_ROOT/minio_volume/certs:/certs --name ai-minio -p $MINIO_PORT:9000 -p $MINIO_CONSOLE_PORT:9001 -e MINIO_DEFAULT_BUCKETS=$MINIO_DEFAULT_BUCKETS -e MINIO_ROOT_USER=$MINIO_ROOT_USER -e MINIO_ROOT_PASSWORD=$MINIO_ROOT_PASSWORD bitnami/minio:latest
sudo docker run --privileged -d -v $DOCKER_VOLUME_ROOT/redis_volume:/data --rm --name ai-redis -p $REDIS_PORT:6379 redis

git clone git@github.com:VaneLord67/ai-platform-backend.git
cd ai-platform-backend

# sql setup
sudo docker exec -it ai-mysql mysql -uroot -p$MYSQL_ROOT_PASSWORD < sql/ai-platform.sql

# casbin setup
cat base_policy.csv > policy.csv

