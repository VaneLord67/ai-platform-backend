cd ~
mkdir ai-platform
mkdir -p minio_volume/data
mkdir -p minio_volume/certs:/certs
sudo chmod -R ug+rw minio_volume/certs
sudo chmod -R ug+rw minio_volume/data

# install python environment
export AI_PLATFORM_VENV_NAME=ai-platform
conda create -n $AI_PLATFORM_VENV_NAME python=3.8
conda activate $AI_PLATFORM_VENV_NAME
pip install flask flask-cors flask_nameko Flask-SocketIO DBUtils mysqlclient mysql-connector-python casbin nameko minio psutil GPutil redis paho-mqtt PyJWT
conda install -c conda-forge opencv

# install docker
curl -fsSL https://test.docker.com -o test-docker.sh
sudo sh test-docker.sh

# run docker containers
docker run -d --name ai-mysql --env=MYSQL_ROOT_PASSWORD=abc123 -p 3307:3306 mysql:latest
docker run --privileged -d --name ai-rabbitmq -p 1883:1883 -p 5672:5672 -p 15672:15672 rabbitmq:3.12-management
docker exec -it ai-rabbitmq rabbitmq-plugins enable rabbitmq_mqtt # enable rabbitmq mqtt protocol
docker run -d -v $PWD/minio_volume/data:/bitnami/minio/data -v $PWD/minio_volume/certs:/certs --name ai-minio -p 9000:9000 -p 9001:9001 -e MINIO_DEFAULT_BUCKETS="ai-platform" -e MINIO_ROOT_USER="minio-root-user" -e MINIO_ROOT_PASSWORD="minio-root-password" bitnami/minio:latest

# backend
git clone git@github.com:VaneLord67/ai-platform-backend.git
export PYTHONPATH=$PWD


