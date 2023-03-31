import sqlite3


def check_sqlite_version(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute("SELECT sqlite_version()")
    version = cur.fetchone()[0]
    print(f"SQLite version: {version}")


def show_table_info(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(bplog)")
    table_info = cur.fetchall()
    for column in table_info:
        print(column)


def recreate_db_ids(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute(
        """CREATE TEMPORARY TABLE bplog_backup
                (date TEXT, time TEXT, systolic INTEGER, diastolic INTEGER, comment TEXT)"""
    )
    cur.execute(
        "INSERT INTO bplog_backup SELECT date, time, systolic, diastolic, comment FROM bplog"
    )
    cur.execute("DROP TABLE bplog")
    cur.execute(
        """CREATE TABLE bplog
                (id INTEGER PRIMARY KEY, date TEXT, time TEXT, systolic INTEGER, diastolic INTEGER, comment TEXT)"""
    )
    cur.execute(
        "INSERT INTO bplog SELECT NULL, date, time, systolic, diastolic, comment FROM bplog_backup"
    )
    cur.execute("DROP TABLE bplog_backup")

    conn.commit()