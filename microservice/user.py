from nameko.rpc import rpc

from common.model import User
from common.util import connect_to_database, generate_jwt


class UserService:
    name = "user_service"

    def __init__(self):
        self.conn = connect_to_database()

    @rpc
    def register(self, user_json) -> str:
        user = User.from_json(user_json)
        username = user.username
        password = user.password
        conn = self.conn
        ok = False
        user_id = 0
        if conn:
            # 插入新用户
            try:
                cursor = conn.cursor()
                insert_query = "INSERT INTO users (username, password) VALUES (%s, %s)"
                cursor.execute(insert_query, (username, password))
                conn.commit()
                if cursor.rowcount > 0:
                    ok = True
                    user_id = cursor.lastrowid
            except Exception as e:
                print(f"Error: {e}")
        jwt = ""
        if ok and user_id != 0:
            jwt = generate_jwt(user_id, username)
        return jwt

    @rpc
    def login(self, user_json) -> str:
        user = User.from_json(user_json)
        username = user.username
        password = user.password
        conn = self.conn
        ok = False
        user_id = 0
        if conn:
            try:
                cursor = conn.cursor()
                query = "SELECT * FROM users WHERE username = %s AND password = %s"
                cursor.execute(query, (username, password))
                result = cursor.fetchone()
                ok = bool(result)
                if result and len(result) > 0:
                    user_id = result[0]
            except Exception as e:
                print(f"Error: {e}")
        jwt = ""
        if ok and user_id != 0:
            jwt = generate_jwt(user_id, username)
        return jwt
