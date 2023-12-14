import json
import os
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlparse, unquote

import cv2
import jwt
import mysql.connector
import requests
from mysql.connector import Error

from common.config import config


class JsonEncoder(json.JSONEncoder):
    """Extended json encoder to support custom class types."""

    def default(self, o: Any) -> Any:
        if issubclass(o.__class__, (JsonBase)):
            return o.to_json()
        return super().default(o)


class JsonBase(object):
    """Base class to support json Serialization and Deserialization.

    Classes that want to support json serialization and deserialization conveniently should
    subclass this class
    """

    def __init__(self) -> None:
        super().__setattr__("_json", {})

    def __setattr__(self, key: str, value: Any) -> None:
        if hasattr(value, "to_json"):
            self._json[key] = value.to_json()

        elif isinstance(value, list):
            if len(value) > 0 and hasattr(value[0], "to_json"):
                self._json[key] = [v.to_json() for v in value]
            else:
                self._json[key] = [v for v in value]

        else:
            self._json[key] = value
        super().__setattr__(key, value)

    def __repr__(self) -> str:
        return json.dumps(self._json, cls=JsonEncoder)

    def __str__(self) -> str:
        return self.__repr__()

    def to_json(self):
        # dump to dict
        return self._json

    def from_json(self, j: str):
        """Deserialization subclass from str j.

        Be careful! This method will overwrite self.
        **Only support json obj**.

        Args:
            j (str): Str that conforming to the json standard and the serialization type of subclass.

        Returns:
            (subclass): Subclass
        """
        d = json.loads(j)
        return self.from_dict(d)

    def from_dict(self, d: dict):
        if isinstance(d, dict):
            for key, value in d.items():
                if key in self.__dict__:
                    if hasattr(self.__dict__[key], "from_json"):
                        setattr(
                            self, key, self.__dict__[key].from_json(json.dumps(value))
                        )
                    else:
                        setattr(self, key, value)
        return self


def generate_jwt(id: int, username: str) -> str:
    expiration_time = datetime.utcnow() + timedelta(hours=24)
    payload = {
        'id': id,
        'username': username,
        'exp': expiration_time
    }
    token = jwt.encode(payload, config.get("jwt_secret"), algorithm='HS256')
    return token


def decode_jwt(token: str) -> dict | None:
    try:
        decoded_payload = jwt.decode(token, config.get("jwt_secret"), algorithms=['HS256'])
        return decoded_payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def connect_to_database():
    try:
        # 建立数据库连接
        connection = mysql.connector.connect(
            host=config.get("mysql_host"),
            port=config.get("mysql_port"),
            database=config.get("mysql_database"),
            user=config.get("mysql_user"),
            password=config.get("mysql_password")
        )

        if connection.is_connected():
            return connection

    except Error as e:
        print(f"Error: {e}")
        return None


def download_file(url, temp_dir='temp'):
    response = requests.get(url)
    if response.status_code == 200:
        url_path = urlparse(url).path
        file_name = unquote(os.path.basename(url_path))
        file_path = f'{temp_dir}/{file_name}'
        with open(file_path, 'wb') as f:
            f.write(response.content)
        return file_name, file_path
    else:
        print(f"Failed to download file from {url}. Status code: {response.status_code}")
        return None


def find_any_file(folder_path):
    for root, dirs, files in os.walk(folder_path):
        for file_name in files:
            file_path = os.path.join(root, file_name)
            return file_path  # 返回第一个找到的文件路径

    return None  # 如果未找到任何文件，返回None


def generate_video(output_video_path, folder_path):
    img_paths = []
    fps = 1.0
    for root, dirs, files in os.walk(folder_path):
        for file_name in files:
            file_path = os.path.join(root, file_name)
            img_paths.append(file_path)
    if len(img_paths) == 0:
        return
    first_frame = cv2.imread(img_paths[0])
    height, width, layers = first_frame.shape
    # 创建视频对象
    video = cv2.VideoWriter(output_video_path, cv2.VideoWriter_fourcc(*'avc1'), fps, (width, height))
    # 将图片逐一写入视频
    for img_path in img_paths:
        video.write(cv2.imread(img_path))
    # 保存视频
    video.release()


def get_filename_and_ext(file_path):
    file_name, file_extension = os.path.splitext(os.path.basename(file_path))
    return file_name, file_extension
