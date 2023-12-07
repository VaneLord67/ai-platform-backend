from typing import Union

from mysql.connector import MySQLConnection, CMySQLConnection
from mysql.connector.pooling import PooledMySQLConnection
from nameko.extensions import DependencyProvider

from common.util import connect_to_database


class MysqlStorageWrapper:

    def __init__(self, conn):
        self.conn = conn


class MysqlStorage(DependencyProvider):

    def __init__(self):
        self.conn: Union[PooledMySQLConnection, MySQLConnection, CMySQLConnection, None] = None

    def setup(self):
        self.conn = connect_to_database()

    def get_dependency(self, worker_ctx):
        return MysqlStorageWrapper(self.conn)
