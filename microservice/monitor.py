import json

from nameko.rpc import rpc

from microservice.mysql_storage import MysqlStorage
from model.request_log import RequestLog
from model.statistics import Statistics


class MonitorService:
    name = "monitor_service"

    mysql_storage = MysqlStorage()

    @rpc
    def get_total_num(self):
        conn = self.mysql_storage.conn
        count_query = "SELECT COUNT(*) FROM request_log"
        cursor = conn.cursor()
        cursor.execute(count_query)
        total_num = cursor.fetchone()[0]
        cursor.close()
        return total_num

    @rpc
    def get_monitor_data_list(self, page_num, page_size):
        conn = self.mysql_storage.conn
        cursor = conn.cursor()
        # 构建查询语句
        query = """
                    SELECT id, user_id, method, path, status_code, duration, response_json, time
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
            id, user_id, method, path, status_code, duration, response_json, time = r
            rl = RequestLog(id, user_id, method, path, status_code, duration, response_json, time.timestamp())
            requestLogs.append(rl)
        # 关闭连接
        cursor.close()
        return requestLogs

    @rpc
    def insert_request_log(self, log_data):
        conn = self.mysql_storage.conn
        cursor = conn.cursor()
        insert_sql = """
               INSERT INTO request_log (user_id, method, path, status_code, duration, response_json, time)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
           """
        cursor.execute(insert_sql, (
            log_data['user_id'],
            log_data['method'],
            log_data['path'],
            log_data['status_code'],
            log_data['duration'],
            json.dumps(log_data['response_json']) if log_data['response_json'] else "",
            log_data['time'],
        ))
        conn.commit()
        cursor.close()

    @staticmethod
    def build_statistics_sql(time_interval_string: str):
        return f"""
                            SELECT 
                                path,
                                COUNT(*) AS total_calls,
                                AVG(duration) AS avg_response_time,
                                (SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) / COUNT(*)) * 100 AS error_rate
                            FROM 
                                request_log
                            WHERE 
                                path IN ('/model/detection/call', '/model/recognition/call', '/model/track/call')
                                AND time >= NOW() + INTERVAL 8 HOUR - INTERVAL {time_interval_string} 
                            GROUP BY 
                                path
                            ORDER BY 
                                path;
                            """

    @rpc
    def get_statistics(self):
        cursor = self.mysql_storage.conn.cursor()
        sql_for_hour = self.build_statistics_sql("1 HOUR")
        cursor.execute(sql_for_hour)
        results = cursor.fetchall()
        statistics_for_hour = []
        for row in results:
            path, total_calls, avg_response_time, error_rate = row
            statistic = Statistics(path, total_calls, float(avg_response_time), float(error_rate))
            statistics_for_hour.append(statistic)

        cursor = self.mysql_storage.conn.cursor()
        sql_for_day = self.build_statistics_sql("1 DAY")
        cursor.execute(sql_for_day)
        statistics_for_day = []
        results = cursor.fetchall()
        for row in results:
            path, total_calls, avg_response_time, error_rate = row
            statistic = Statistics(path, total_calls, float(avg_response_time), float(error_rate))
            statistics_for_day.append(statistic)

        r = {
            'statistics_for_hour': statistics_for_hour,
            'statistics_for_day': statistics_for_day,
        }
        return r

