import argparse
import configparser
import csv
import datetime as dt
import sqlite3
import sys
from pathlib import Path
from typing import List


def setup_cli_parser(args=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Record and graph blood pressure measurements",
    )
    parser.add_argument(
        "bp",
        nargs="?",
        action="store",
        help="The blood pressure measurement to insert into the database separated by a colon (e.g. 120:80)",
    )
    parser.add_argument("--list", action="store_true", help="List all records")
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help='Specify the date of measurement in the form "YYYY-MM-DD" (default: today)',
    )
    parser.add_argument(
        "--time",
        type=str,
        default=None,
        help='Specify the time of measurement in the form "HH:MM" (default: current time)',
    )
    parser.add_argument(
        "-rm",
        action="store_true",
        help="Remove measurement by date",
    )
    parser.add_argument(
        "-rl",
        action="store_true",
        help="Remove last measurement added",
    )
    parser.add_argument(
        "--comment",
        type=str,
        default=None,
        help="Add a comment for the measurement",
    )
    parser.add_argument(
        "--in-memory",
        action="store_true",
        help="Use an in-memory database (for testing)",
    )
    parser.add_argument(
        "--csv",
        action="store_true",
        help="Export database to csv",
    )
    parser.add_argument(
        "--config", type=str, default=None, help="Path to configuration file"
    )
    parser.add_argument(
        "--reset_config", action="store_true", help="Reset the config path"
    )

    return parser.parse_args()


def database_setup(conn: sqlite3.Connection) -> None:
    # create table if it doesn't exist
    cur = conn.cursor()
    cur.execute(
        """CREATE TABLE IF NOT EXISTS bplog
                (id INTEGER PRIMARY KEY, date TEXT, time TEXT, systolic INTEGER, diastolic INTEGER, comment TEXT)"""
    )
    # create an index on the date and time columns if it doesn't exist
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_bplog_date_time ON bplog(date, time)",
    )
    conn.commit()


def delete_record(conn: sqlite3.Connection, record_id: str) -> None:
    sql = "DELETE FROM bplog WHERE id = ?"
    cur = conn.cursor()
    cur.execute(sql, (record_id,))
    conn.commit()


def remove_measurement_by_date(conn: sqlite3.Connection, date: str) -> None:
    rows = get_record_by_date(conn, date)
    if not rows:
        print(f"No measurements found for {date}")
        return
    elif len(rows) == 1:
        delete_record(conn, rows[0][0])
        print(f"Measurement removed: {rows[0]}")
    else:
        multiple_records(rows, date, conn)


def multiple_records(
    rows: List[List[str]], date: str, conn: sqlite3.Connection
) -> None:
    print(f"{len(rows)} measurements found for {date}:")
    for row in rows:
        print(f"{row[1]} {row[2]} - {row[3]}:{row[4]}")
    bp_time = input("Enter time of the measurement to remove (HH:MM): ")
    found = False
    for row in rows:
        if row[2] == bp_time:
            delete_record(conn, row[0])
            found = True
            print(
                f"Measurement removed: {row[1]} {row[2]} - {row[3]}:{row[4]} (id:{row[0]})"
            )
            break
    if not found:
        print(f"No measurement found for {date} at time {bp_time}")


def get_record_by_date(conn: sqlite3.Connection, date: str) -> list:
    sql = "SELECT * FROM bplog WHERE date(date) = ? ORDER BY time"
    cur = conn.cursor()
    cur.execute(sql, (date,))
    return cur.fetchall()


def delete_last_record_added(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute("SELECT * FROM bplog WHERE id = (SELECT MAX(id) FROM bplog)")
    deleted_record = cur.fetchone()
    cur.execute("DELETE FROM bplog WHERE id = (SELECT MAX(id) FROM bplog)")
    print(f"Last record deleted: {deleted_record}")
    conn.commit()


def parse_date_and_blood_pressure(
    args: argparse.Namespace,
    conn: sqlite3.Connection,
) -> tuple[int, int, str]:
    if args.bp:
        bp = args.bp.split(":")
        systolic = int(bp[0])
        diastolic = int(bp[1])

        date_format = "%d,%m,%Y"
        date_str = args.date or dt.datetime.now().strftime(date_format)

        date_obj = dt.datetime.strptime(date_str, date_format)

        db_date_format = "%Y-%m-%d"
        db_date_str = date_obj.strftime(db_date_format)
        return systolic, diastolic, db_date_str
    else:
        plot_blood_pressures(conn)
        sys.exit(0)


def add_measurement(
    conn: sqlite3.Connection,
    args: argparse.Namespace,
    systolic: int,
    diastolic: int,
    date_str: str,
) -> None:
    """Add measurements to the database."""
    cur = conn.cursor()
    time_str = args.time or dt.datetime.now().strftime("%H:%M")
    comment = args.comment or ""
    cur.execute(
        "INSERT INTO bplog (date, time, systolic, diastolic, comment) VALUES (?, ?, ?, ?, ?)",
        (date_str, time_str, systolic, diastolic, comment),
    )
    conn.commit()
    print(
        f"Blood pressure measurement added: {systolic}/{diastolic} ({date_str} {time_str})",
    )


def get_all_records(conn: sqlite3.Connection) -> list:
    cur = conn.cursor()
    cur.execute("SELECT * FROM bplog ORDER BY date, time")
    return cur.fetchall()


def generate_table(records) -> str:
    try:
        from prettytable import PrettyTable

        table = PrettyTable(["Date", "Time", "Blood Pressure", "Comment"])
        for record in records:
            if len(record) != 6:
                raise ValueError(f"Unexpected row format: {record}")
            bp = f"{record[3]}:{record[4]}"
            table.add_row([record[1], record[2], bp, record[5]])
        return str(table)
    except ImportError:
        # If prettytable is not installed, generate the table without pretty formatting
        output = []
        for record in records:
            bp = f"{record[3]}:{record[4]}"
            output.append(f"{record[1]}\t{record[2]}\t{bp}\t{record[5]}")
        return "\n".join(output)


def list_all_records(conn: sqlite3.Connection) -> str:
    records = get_all_records(conn)
    table = generate_table(records)
    conn.close()
    return table


def plot_blood_pressures(conn: sqlite3.Connection) -> None:
    try:
        from matplotlib import colormaps
        from matplotlib import pyplot as plt
        from matplotlib.lines import Line2D
    except ImportError:
        sys.exit()

    cur = conn.cursor()
    cur.execute(
        "SELECT date, time, systolic, diastolic FROM bplog ORDER BY date, time",
    )
    rows = cur.fetchall()

    if rows == []:
        print("No data to plot")
        return
    dates_times = [
        dt.datetime.strptime(f"{row[0]} {row[1]}", "%Y-%m-%d %H:%M") for row in rows
    ]
    systolics = [row[2] for row in rows]
    diastolics = [row[3] for row in rows]

    sys_avg = sum(systolics) / len(systolics)
    dias_avg = sum(diastolics) / len(diastolics)

    cmap = colormaps.get_cmap("cool_r")
    times = [dt.datetime.strptime(str(row[1]), "%H:%M").time() for row in rows]
    time_indices = [(t.hour * 60 + t.minute) / (24 * 60) for t in times]

    fig, ax = plt.subplots()
    ax.plot(dates_times, systolics, "-o", color="red", zorder=0, label="systolic")
    ax.plot(dates_times, diastolics, "-o", color="blue", zorder=0, label="diastolic")

    sc = ax.scatter(dates_times, systolics, c=time_indices, cmap=cmap, vmin=0, vmax=1)
    ax.scatter(dates_times, diastolics, c=time_indices, cmap=cmap, vmin=0, vmax=1)

    cbar = fig.colorbar(sc)
    cbar.set_ticks([0, 0.25, 0.5, 0.75, 1.0])
    cbar.set_ticklabels(["0:00", "06:00", "12:00", "18:00", "0:00"])
    cbar.set_label("Time of day")

    plt.xticks(rotation=45)

    # show lines for averages
    plt.axhline(y=sys_avg, color="green", linestyle="--")
    plt.axhline(y=dias_avg, color="green", linestyle="--")

    # show lines for prehipertension
    plt.axhline(y=90, color="red", linestyle=":")
    plt.axhline(y=140, color="red", linestyle=":")
    plt.axhline(y=80, color="black", linestyle=":")
    plt.axhline(y=120, color="black", linestyle=":")

    plt.xlabel("Date")
    plt.ylabel("Blood Pressure (mmHg)")
    plt.title("Blood Pressure over Time")

    custom_lines = [
        Line2D([0], [0], color="black", linestyle=":"),
        Line2D([0], [0], color="red", linestyle=":"),
        Line2D([0], [0], color="green", linestyle="--"),
    ]
    plt.legend(custom_lines, ["normal", "prehypertension", "average"])

    plt.show()


def export_to_csv(conn):
    cur = conn.cursor()
    data = cur.execute("SELECT * FROM bplog")
    with open("bplog_database.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "time", "systolic", "diastolic", "comment"])
        writer.writerows(data)


# def connect_to_database(use_in_memory: bool) -> sqlite3.Connection:
#     if use_in_memory:
#         conn = sqlite3.connect(":memory:")
#     else:
#         db_path = Path("bplog") / "bplog.db"
#         conn = sqlite3.connect(str(db_path))
#     database_setup(conn)
#     return conn


def connect_to_database(use_in_memory: bool, db_path: str = None) -> sqlite3.Connection:
    if use_in_memory:
        conn = sqlite3.connect(":memory:")
    else:
        if db_path is None:
            config = configparser.ConfigParser()
            config.read("config.ini")
            db_file_path = (
                config["Database"]["file_path"]
                if "Database" in config and "file_path" in config["Database"]
                else str(Path("bplog") / "bplog.db")
            )
            db_path = Path(db_file_path).parent / f"{Path(db_file_path).stem}.db"
        else:
            db_path = Path(db_path)

            config = configparser.ConfigParser()
            config["Database"] = {"file_path": str(db_path)}
            with open("config.ini", "w") as config_file:
                config.write(config_file)

        if not db_path.exists():
            conn = sqlite3.connect(db_path)
            database_setup(conn)
        elif db_path.stat().st_mode & 0o200:
            conn = sqlite3.connect(db_path)
            database_setup(conn)
        else:
            raise ValueError(f"File '{db_path}' is not writable")

    return conn

    # def connect_to_database(use_in_memory: bool, db_path: str = None) -> sqlite3.Connection:
    #     if use_in_memory:
    #         conn = sqlite3.connect(":memory:")
    #     else:
    #         if db_path is None:
    #             config = configparser.ConfigParser()
    #             config.read("config.ini")
    #             db_path = (
    #                 config["Database"]["path"]
    #                 if "Database" in config and "path" in config["Database"]
    #                 else str(Path("bplog") / "bplog.db")
    #             )
    #         else:
    #             config = configparser.ConfigParser()
    #             config["Database"] = {"path": db_path}
    #             with open("config.ini", "w") as config_file:
    #                 config.write(config_file)

    #         print(Path(db_path).stat().st_mode)
    #         if not Path(db_path).exists():
    #             print(f"Creating database file at {db_path}")
    #             conn = sqlite3.connect(db_path)
    #             database_setup(conn)
    #         elif Path(db_path).stat().st_mode & 0o200:
    #             print(f"Opening database file at {db_path}")
    #             conn = sqlite3.connect(db_path)
    #             database_setup(conn)
    #         else:
    #             raise ValueError(f"File '{db_path}' is not writable")

    return conn


# def connect_to_database(use_in_memory: bool, db_path: str = None) -> sqlite3.Connection:
#     if use_in_memory:
#         conn = sqlite3.connect(":memory:")
#     else:
#         if db_path is None:
#             config = configparser.ConfigParser()
#             config.read("config.ini")
#             db_path = (
#                 config["Database"]["path"]
#                 if "Database" in config and "path" in config["Database"]
#                 else str(Path("bplog") / "bplog.db")
#             )
#         else:
#             config = configparser.ConfigParser()
#             config["Database"] = {"path": db_path}
#             with open("config.ini", "w") as config_file:
#                 config.write(config_file)
#         print(db_path)
#         conn = sqlite3.connect(db_path)
#     database_setup(conn)
#     return conn


# def update_db_path_config(db_path: str):
#     config = configparser.ConfigParser()
#     config["Database"] = {"path": db_path}
#     with open("config.ini", "w") as config_file:
#         config.write(config_file)


def reset_db_path_config():
    config_file = Path("config.ini")
    if config_file.exists():
        config_file.unlink()


# def reset_db_path_config(db_path: str):
#     config = configparser.ConfigParser()
#     config["Database"] = {"path": None}
#     with open("config.ini", "w") as config_file:
#         config.write(config_file)

# def get_db_path_config() -> str:
#     config = configparser.ConfigParser()
#     config.read("config.ini")
#     return config["Database"]["path"]


def main() -> None:
    args = setup_cli_parser()

    if args.reset_config:
        reset_db_path_config()
        sys.exit(0)

    if args.config:
        conn = connect_to_database(args.in_memory, args.config)
    else:
        conn = connect_to_database(args.in_memory)

    if args.rl:
        delete_last_record_added(conn)

    if args.rm:
        date = input("Enter date of measurement to remove (YYYY-MM-DD): ")
        remove_measurement_by_date(conn, date)

    if args.list:
        print(list_all_records(conn))
        sys.exit(0)

    if args.csv:
        export_to_csv(conn)

    systolic, diastolic, date_str = parse_date_and_blood_pressure(args, conn)
    add_measurement(conn, args, systolic, diastolic, date_str)

    plot_blood_pressures(conn)

    conn.close()


if __name__ == "__main__":
    main()  # pragma: no cover
