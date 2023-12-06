import json
from datetime import datetime, timedelta
from typing import Any

import jwt
import mysql.connector
from mysql.connector import Error


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


secret_key = 'ai-platform'


def generate_jwt(id: int, username: str) -> str:
    expiration_time = datetime.utcnow() + timedelta(hours=24)
    payload = {
        'id': id,
        'username': username,
        'exp': expiration_time
    }
    token = jwt.encode(payload, secret_key, algorithm='HS256')
    return token


def decode_jwt(token: str) -> dict | None:
    try:
        decoded_payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        return decoded_payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def connect_to_database():
    try:
        # 建立数据库连接
        connection = mysql.connector.connect(
            host='localhost',
            port='3307',
            database='ai-platform',
            user='root',
            password='abc123'
        )

        if connection.is_connected():
            return connection

    except Error as e:
        print(f"Error: {e}")
        return None
