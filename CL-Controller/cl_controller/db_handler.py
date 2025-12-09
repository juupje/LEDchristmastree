import sqlite3 as sq
import queue

#ensure that this is threadsafe
class DataBaseHandler:
    def __init__(self, database_path:str):
        self.database_path = database_path
        self.connection = None
        self.queue = queue.Queue()

    def get_database(self) -> sq.Connection:
        if self.connection is None:
            self.connection = sq.connect(self.database_path, detect_types=sq.PARSE_DECLTYPES)
            self.connection.row_factory = self.make_dicts
        return self.connection

    def make_dicts(self, cursor, row):
        return dict((cursor.description[idx][0], value)
                    for idx, value in enumerate(row))

    def query_db(self, query, args=(), one=False, commit=False):
        cur = self.get_database().execute(query, args)
        if commit:
            cur.connection.commit()
        rv = cur.fetchone() if one else cur.fetchall()  
        cur.close()
        return rv

    def close_database(self):
        if self.connection is not None:
            self.connection.close()