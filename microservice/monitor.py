import json

from nameko.rpc import rpc

from microservice.mysql_storage import MysqlStorage
from model.request_log import RequestLog


class MonitorService:
    name = "monitor_service"

    mysql_storage = MysqlStorage()

    @rpc
    def getTotalNum(self):
        conn = self.mysql_storage.conn
        count_query = "SELECT COUNT(*) FROM request_log"
        cursor = conn.cursor()
        cursor.execute(count_query)
        total_num = cursor.fetchone()[0]
        cursor.close()
        return total_num

    @rpc
    def getMonitorDataList(self, page_num, page_size):
        conn = self.mysql_storage.conn
        cursor = conn.cursor()
        # 构建查询语句
        query = """
                    SELECT id, user_id, method, path, status_code, duration, response_json
                    FROM request_log ORDER BY id DESC
                    LIMIT %s OFFSET %s
                """
        # 计算 OFFSET
        offset = (page_num - 1) * page_size
        # 执行查询
        cursor.execute(query, (page_size, offset))
        # 获取查询结果
        result = cursor.fetchall()
        requestLogs = []
        for r in result:
            id = r[0]
            user_id = r[1]
            method = r[2]
            path = r[3]
            status_code = r[4]
            duration = r[5]
            response_json = r[6]
            rl = RequestLog()
            rl.id = id
            rl.user_id = user_id
            rl.method = method
            rl.path = path
            rl.status_code = status_code
            rl.duration = duration
            rl.response_json = response_json
            requestLogs.append(rl)
        # 关闭连接
        cursor.close()
        return requestLogs

    @rpc
    def insertRequestLog(self, log_data):
        conn = self.mysql_storage.conn
        cursor = conn.cursor()
        insert_sql = """
               INSERT INTO request_log (user_id, method, path, status_code, duration, response_json)
               VALUES (%s, %s, %s, %s, %s, %s)
           """
        cursor.execute(insert_sql, (
            log_data['user_id'],
            log_data['method'],
            log_data['path'],
            log_data['status_code'],
            log_data['duration'],
            json.dumps(log_data['response_json']) if log_data['response_json'] else "",
        ))
        conn.commit()
        cursor.close()

    @rpc
    def hello(self):
        return "hello!"
