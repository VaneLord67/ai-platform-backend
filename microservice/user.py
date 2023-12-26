from nameko.rpc import rpc

from common.util import generate_jwt
from microservice.mysql_storage import MysqlStorage
from model.user import User


class UserService:
    name = "user_service"
    mysql_storage = MysqlStorage()

    def __init__(self):
        pass

    @rpc
    def register(self, user_json) -> str:
        user = User().from_json(user_json)
        username = user.username
        password = user.password
        conn = self.mysql_storage.conn
        ok = False
        user_id = 0
        if conn:
            # 插入新用户
            try:
                cursor = conn.cursor()
                insert_query = "INSERT INTO users (username, password, role) VALUES (%s, %s, guest)"
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
        user = User().from_json(user_json)
        username = user.username
        password = user.password
        conn = self.mysql_storage.conn
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

    @rpc
    def get_user_total_num(self):
        cursor = self.mysql_storage.conn.cursor()
        count_query = "SELECT COUNT(*) FROM users"
        cursor.execute(count_query)
        total_num = cursor.fetchone()[0]
        cursor.close()
        return total_num

    @rpc
    def get_user_page(self, page_num, page_size):
        conn = self.mysql_storage.conn
        cursor = conn.cursor()
        # 构建查询语句
        query = """SELECT id, username, role
                   FROM users ORDER BY id ASC
                   LIMIT %s OFFSET %s"""
        # 计算 OFFSET
        offset = (page_num - 1) * page_size
        # 执行查询
        cursor.execute(query, (page_size, offset))
        # 获取查询结果
        result = cursor.fetchall()
        users = []
        for r in result:
            id, username, role = r
            users.append(User(id=id, username=username, role=role))
        # 关闭连接
        cursor.close()
        return users

    @rpc
    def delete_user(self, user_id):
        conn = self.mysql_storage.conn
        cursor = conn.cursor()
        query = """DELETE FROM users WHERE id = %s"""
        cursor.execute(query, (user_id,))
        conn.commit()
        cursor.close()

    @rpc
    def get_user_by_id(self, user_id):
        conn = self.mysql_storage.conn
        cursor = conn.cursor()
        query = """SELECT id, username, role FROM users WHERE id = %s"""
        cursor.execute(query, (user_id,))

        user = None
        result = cursor.fetchone()
        if result:
            id, username, role = result
            user = User(id=id, username=username, role=role)
        cursor.close()
        return user

    @rpc
    def update_user_by_id(self, user_id, username, role):
        conn = self.mysql_storage.conn
        cursor = conn.cursor()
        query = """UPDATE users set username = %s, role = %s WHERE id = %s"""
        cursor.execute(query, (username, role, user_id))
        conn.commit()
        cursor.close()
