from typing import Union

from dbutils.pooled_db import PooledDB, PooledSharedDBConnection, PooledDedicatedDBConnection
from eventlet.green import MySQLdb
from nameko.extensions import DependencyProvider

from common.config import config


class MysqlStorageWrapper:

    def __init__(self, conn: Union[None, PooledSharedDBConnection, PooledDedicatedDBConnection]):
        self.conn: Union[None, PooledSharedDBConnection, PooledDedicatedDBConnection] = conn


class MysqlStorage(DependencyProvider):

    def __init__(self):
        self.pool: Union[None, PooledDB] = None

    def setup(self):
        pool = PooledDB(MySQLdb,
                        host=config.get("mysql_host"),
                        port=int(config.get("mysql_port")),
                        user=config.get("mysql_user"),
                        passwd=config.get("mysql_password"),
                        db=config.get("mysql_database"),
                        )
        self.pool = pool

    def stop(self):
        if self.pool:
            self.pool.close()

    def get_dependency(self, worker_ctx):
        return MysqlStorageWrapper(self.pool.connection())
