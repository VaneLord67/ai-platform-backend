import json
from datetime import datetime, timedelta

import jwt
import mysql.connector
from mysql.connector import Error


class APIResponse:
    def __init__(self, code, message, data=None):
        self.code = code
        self.message = message
        self.data = data

    def to_dict(self):
        return {'code': self.code, 'message': self.message, 'data': self.data}

    def to_json(self):
        return json.dumps(self.to_dict())

    @staticmethod
    def success():
        return APIResponse(code=1, message="success")

    @staticmethod
    def success_with_data(data):
        return APIResponse(code=1, message="success", data=data)

    @staticmethod
    def fail():
        return APIResponse(code=0, message="fail")

secret_key = 'ai-platform'

def generate_jwt(username: str) -> str:

    expiration_time = datetime.utcnow() + timedelta(hours=24)
    payload = {
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