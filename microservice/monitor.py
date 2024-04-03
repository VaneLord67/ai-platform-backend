import json
import time
import uuid

from nameko.events import event_handler
from nameko.rpc import rpc

from common.log import LOGGER
from microservice.manage import ManageService
from microservice.mysql_storage import MysqlStorage
from model.request_log import RequestLog
from model.statistics import Statistics
from model.support_input import SINGLE_PICTURE_URL_TYPE, MULTIPLE_PICTURE_URL_TYPE, SupportInput
from model.task import Task


class MonitorService:
    name = "monitor_service"

    mysql_storage = MysqlStorage()

    @staticmethod
    def monitor_search_condition(username, service_name, start_time, end_time, input_mode):
        query = ""
        params = ()
        if username != "":
            query += f" AND username = %s"
            params += (username,)
        if service_name != "":
            search_path = f"/model/{service_name}/call"
            query += f" AND path = %s"
            params += (search_path,)
        if start_time != 0:
            query += f" AND time >= FROM_UNIXTIME(%s / 1000)"
            params += (start_time,)
        if end_time != 0:
            query += f" AND time <= FROM_UNIXTIME(%s / 1000)"
            params += (end_time,)
        if input_mode != "":
            query += f" AND input_mode = %s"
            params += (input_mode,)
        return query, params

    @rpc
    def get_total_num(self, username, service_name, start_time, end_time, input_mode):
        conn = self.mysql_storage.conn
        count_query = """
        SELECT COUNT(*) FROM request_log 
        INNER JOIN users ON request_log.user_id = users.id 
        WHERE path LIKE '/model/%%/call'
        """
        search_query, params = self.monitor_search_condition(username, service_name, start_time, end_time, input_mode)
        count_query += search_query
        cursor = conn.cursor()
        # print(f'count_query = {count_query}')
        # print(f'params = {params}')
        cursor.execute(count_query, params)
        total_num = cursor.fetchone()[0]
        cursor.close()
        return total_num

    @rpc
    def get_monitor_data_list(self, page_num, page_size, username, service_name, start_time, end_time, input_mode):
        conn = self.mysql_storage.conn
        cursor = conn.cursor()
        # 构建查询语句
        query = """
                SELECT request_log.id, user_id, username, method, path, status_code, duration, response_json, time, input_mode
                FROM request_log INNER JOIN users ON request_log.user_id=users.id
                WHERE path LIKE '/model/%%/call'
                """
        # 计算 OFFSET
        search_query, params = self.monitor_search_condition(username, service_name, start_time, end_time, input_mode)
        query += search_query
        query += " ORDER BY id DESC LIMIT %s OFFSET %s"
        offset = (page_num - 1) * page_size
        params += (page_size, offset)
        # print(f'query = {query}')
        # print(f'params = {params}')
        # 执行查询
        cursor.execute(query, params)
        # 获取查询结果
        result = cursor.fetchall()
        requestLogs = []
        for r in result:
            id, user_id, username, method, path, status_code, duration, response_json, time, input_mode = r
            rl = RequestLog(
                id=id,
                user_id=user_id,
                username=username,
                method=method,
                path=path,
                status_code=status_code,
                duration=duration,
                response_json=response_json,
                time=time.timestamp(),
                input_mode=input_mode,
            )
            requestLogs.append(rl)
        # 关闭连接
        cursor.close()
        return requestLogs

    @staticmethod
    def is_valid_uuid(s):
        try:
            uuid_obj = uuid.UUID(s)
            return str(uuid_obj) == s
        except ValueError:
            return False

    @rpc
    def insert_task(self, task_id, user_id, path, time, input_mode):
        conn = self.mysql_storage.conn
        if not conn:
            LOGGER.error("conn lost in insert_user_task")
            return
        cursor = conn.cursor()
        insert_sql = """
                          INSERT INTO task (task_id, user_id, path, time, input_mode)
                          VALUES (%s, %s, %s, %s, %s)
                      """
        cursor.execute(insert_sql, (
            task_id,
            user_id,
            path,
            time,
            input_mode,
        ))
        conn.commit()
        cursor.close()

    @rpc
    def get_task_by_task_id(self, task_id):
        conn = self.mysql_storage.conn
        cursor = conn.cursor()
        # 构建查询语句
        query = """
                SELECT task.id, task_id, user_id, username, path, time
                FROM task INNER JOIN users ON task.user_id=users.id
                WHERE task_id=%s
                """
        # 执行查询
        cursor.execute(query, (task_id,))
        # 获取查询结果
        result = cursor.fetchone()
        task = None
        if result:
            id, task_id, user_id, username, path, time = result
            task = Task(
                task_id=task_id,
                user_id=user_id,
                username=username,
                path=path,
                time=time,
            )
        cursor.close()
        return task.to_json() if task else None

    @rpc
    def insert_request_log(self, log_data):
        if log_data and log_data['response_json']:
            # 如果该请求是建立socketIO连接，则不将其插入到请求日志中
            response_json = log_data['response_json']
            if 'data' in response_json and response_json['data'] and isinstance(response_json['data'], str)\
                    and self.is_valid_uuid(response_json['data'][1:]):
                return
        conn = self.mysql_storage.conn
        if conn:
            cursor = conn.cursor()
            input_mode = log_data.get('input_mode', '')
            if 'body' in log_data:
                support_input = SupportInput().from_dict(log_data['body']['supportInput'])
                input_mode = support_input.type
            insert_sql = """
                   INSERT INTO request_log 
                   (user_id, method, path, status_code, duration, response_json, time, input_mode)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
               """
            cursor.execute(insert_sql, (
                log_data['user_id'],
                log_data['method'],
                log_data['path'],
                log_data['status_code'],
                log_data['duration'],
                json.dumps(log_data['response_json']) if log_data['response_json'] else "",
                log_data['time'],
                input_mode,
            ))
            conn.commit()
            cursor.close()
        else:
            LOGGER.error("conn lost in insert_request_log")

    @event_handler(ManageService.name, "insert_request_log")
    def insert_request_log_event_handler(self, log_data):
        self.insert_request_log(log_data)

    @staticmethod
    def build_statistics_sql(time_interval_string: str):
        return f"""
                            SELECT 
                                path,
                                COUNT(*) AS total_calls,
                                AVG(duration) AS avg_response_time,
                                MAX(duration) AS max_response_time,
                                (SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) / COUNT(*)) * 100 AS error_rate
                            FROM 
                                request_log
                            WHERE 
                                path LIKE ('/model/%%/call')
                                AND input_mode IN ('{SINGLE_PICTURE_URL_TYPE}', '{MULTIPLE_PICTURE_URL_TYPE}')
                                AND time >= NOW() - INTERVAL {time_interval_string} 
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
            path, total_calls, avg_response_time, max_response_time, error_rate = row
            statistic = Statistics(path, total_calls,
                                   float(avg_response_time), float(max_response_time),
                                   float(error_rate))
            statistics_for_hour.append(statistic)

        cursor = self.mysql_storage.conn.cursor()
        sql_for_day = self.build_statistics_sql("1 DAY")
        cursor.execute(sql_for_day)
        statistics_for_day = []
        results = cursor.fetchall()
        for row in results:
            path, total_calls, avg_response_time, max_response_time, error_rate = row
            statistic = Statistics(path, total_calls,
                                   float(avg_response_time), float(max_response_time),
                                   float(error_rate))
            statistics_for_day.append(statistic)

        r = {
            'statistics_for_hour': statistics_for_hour,
            'statistics_for_day': statistics_for_day,
        }
        return r

    @rpc
    def get_chart(self, start_time, end_time):
        conn = self.mysql_storage.conn
        cursor = conn.cursor()
        query = """
                SELECT 
                    DATE_FORMAT(time, '%%Y-%%m-%%d %%H:00:00') AS hour_interval,
                    path,
                    COUNT(*) AS record_count
                FROM 
                    request_log
                WHERE path LIKE ('/model/%%/call')
                """
        params = ()
        if start_time == 0:
            # 如果没有指定开始时间，则设置默认开始时间
            current_timestamp = time.time()
            one_day_seconds = 24 * 60 * 60
            one_day_ago_timestamp = current_timestamp - one_day_seconds
            # 将秒转换为毫秒
            start_time = int(one_day_ago_timestamp * 1000)
        query += f" AND time >= FROM_UNIXTIME(%s / 1000) "
        params += (start_time,)
        if end_time != 0:
            query += f" AND time <= FROM_UNIXTIME(%s / 1000) "
            params += (end_time,)
        query += " GROUP BY hour_interval, path ORDER BY hour_interval ASC"
        cursor.execute(query, params)
        result = cursor.fetchall()
        chart_data = []

        def process_path(path_str):
            second_slash_index = path_str.find('/', path_str.find('/') + 1)
            if second_slash_index == -1:
                return path_str
            third_slash_index = path_str.find('/', second_slash_index + 1)
            if third_slash_index == -1:
                return path_str
            return path_str[second_slash_index + 1:third_slash_index]

        for r in result:
            hour_interval, path, record_count = r

            chart_data.append({
                'hour_interval': hour_interval,
                'service_name': process_path(path),
                'record_count': record_count,
            })
        return chart_data
