from nameko.web.handlers import http
from util import connect_to_database, generate_jwt, APIResponse


class UserService:
    name = "user_service"
    url_prefix = "/user"

    def __init__(self):
        self.conn = connect_to_database()

    @http('POST', url_prefix + '/register')
    def register(self, request):
        json_data = request.json
        username = json_data.get('username')
        password = json_data.get('password')
        conn = self.conn
        ok = False
        if conn:
            # 插入新用户
            try:
                cursor = conn.cursor()
                insert_query = "INSERT INTO users (username, password) VALUES (%s, %s)"
                cursor.execute(insert_query, (username, password))
                conn.commit()
                if cursor.rowcount > 0:
                    ok = True
            except Exception as e:
                print(f"Error: {e}")
        if ok:
            response = APIResponse.success()
        else:
            response = APIResponse.fail()
        return response.to_json()

    @http('POST', url_prefix + '/login')
    def login(self, request):
        json_data = request.json
        username = json_data.get('username')
        password = json_data.get('password')
        # print(f"username = {username}, password = {password}")
        conn = self.conn
        ok = False
        if conn:
            try:
                cursor = conn.cursor()
                query = "SELECT * FROM users WHERE username = %s AND password = %s"
                cursor.execute(query, (username, password))
                result = cursor.fetchone()
                ok = bool(result)
            except Exception as e:
                print(f"Error: {e}")
        if ok:
            token = generate_jwt(username)
            response = APIResponse.success_with_data(token)
        else:
            response = APIResponse.fail()
        return response.to_json()


