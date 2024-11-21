from django.db.backends.mysql.base import DatabaseWrapper as MySQLDatabaseWrapper
from MySQLdb import OperationalError

class DatabaseWrapper(MySQLDatabaseWrapper):
    def get_new_connection(self, conn_params):
        try:
            return super().get_new_connection(conn_params)
        except OperationalError as e:
            if e.args[0] == 2006:
                return super().get_new_connection(conn_params)
            raise
