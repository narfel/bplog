"""Simple data logger for blood pressure data."""
import argparse
import configparser
import csv
import datetime as dt
import sqlite3
import sys
from pathlib import Path


def setup_cli_parser(args=None) -> argparse.Namespace:
    """Create command line arguments for the cli.

    Args:
        args: None argument is used in for unittests

    Returns:
        argparse.Namespace: args
    """
    parser = argparse.ArgumentParser(
        description="Record and graph blood pressure measurements",
    )
    parser.add_argument(
        "bp",
        nargs="?",
        action="store",
        help=("Blood pressure measurement " "separated by a colon (e.g. 120:80)"),
    )
    parser.add_argument(
        "-c",
        dest="comment",
        type=str,
        default=None,
        help="Add a comment to the measurement",
    )
    parser.add_argument(
        "-l", dest="list", action="store_true", help="List all records on the terminal"
    )
    parser.add_argument(
        "-d",
        dest="date",
        type=str,
        default=None,
        help='Specify the date of measurement in the form "YYYY-MM-DD" (default: today)',
    )
    parser.add_argument(
        "-t",
        dest="time",
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
        help="Remove the last measurement added",
    )
    parser.add_argument(
        "-in-memory",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "-csv",
        action="store_true",
        help="Export database to csv",
    )
    parser.add_argument(
        "-config",
        type=str,
        default=None,
        help="Path to configuration file",
    )
    parser.add_argument(
        "-reset_config",
        action="store_true",
        help="Reset the config path",
    )

    return parser.parse_args()


def database_setup(conn: sqlite3.Connection) -> None:
    """Set up the database.

    Args:
        conn (sqlite3.Connection): Database connection handle
    """
    # create table if it doesn't exist
    cur = conn.cursor()
    cur.execute(
        """CREATE TABLE IF NOT EXISTS bplog (id INTEGER PRIMARY KEY, date TEXT,
        time TEXT, systolic INTEGER, diastolic INTEGER, comment TEXT)""",
    )
    # create an index on the date and time columns if it doesn't exist
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_bplog_date_time ON bplog(date, time)",
    )
    conn.commit()


def delete_record(conn: sqlite3.Connection, record_id: str) -> None:
    """Delete a record from the database.

    Args:
        conn (sqlite3.Connection): Database connection handle
        record_id (str): Identifier for the record
    """
    sql = "DELETE FROM bplog WHERE id = ?"
    cur = conn.cursor()
    cur.execute(sql, (record_id,))
    conn.commit()


def remove_measurement_by_date(conn: sqlite3.Connection, date: str) -> None:
    """Remove a measurement by date.

    Args:
        conn (sqlite3.Connection): Database connection handle
        date (str): Date of the measurement to be deleted
    """
    rows = get_record_by_date(conn, date)
    if not rows:
        print(f"No measurements found for {date}")
        return
    if len(rows) == 1:
        delete_record(conn, rows[0][0])
        print(f"Measurement removed: {rows[0]}")
    else:
        multiple_records(rows, date, conn)


def multiple_records(
    rows: list,
    date: str,
    conn: sqlite3.Connection,
) -> None:
    """Handle the case if multiple records exist on a day.

    Args:
        rows (list): List of records on a certain date
        date (str): Date of the measurement to be deleted
        conn (sqlite3.Connection): Database connection handle
    """
    print(f"{len(rows)} measurements found for {date}:")
    for row in rows:
        print(f"{row[1]} {row[2]} - {row[3]}:{row[4]}")
    bp_time = input("Enter time of the measurement to remove (HH:MM): ")
    found = False
    for item in rows:
        if item[2] == bp_time:
            delete_record(conn, item[0])
            found = True
            print(
                f"Measurement removed: {item[1]} {item[2]} - {item[3]}:{item[4]} (id:{item[0]})",
            )
            break
    if not found:
        print(f"No measurement found for {date} at time {bp_time}")


def get_record_by_date(conn: sqlite3.Connection, date: str) -> list:
    """Get a list of records matching date.

    Args:
        conn (sqlite3.Connection): Database connection handle
        date (str): Date to be searched

    Returns:
        list: List of measurements on date
    """
    sql = "SELECT * FROM bplog WHERE date(date) = ? ORDER BY time"
    cur = conn.cursor()
    cur.execute(sql, (date,))
    return cur.fetchall()


def delete_last_record_added(conn: sqlite3.Connection) -> None:
    """Delete the last record that was added to the database .

    Args:
        conn (sqlite3.Connection): Database connection handle
    """
    cur = conn.cursor()
    cur.execute("SELECT * FROM bplog WHERE id = (SELECT MAX(id) FROM bplog)")
    deleted_record = cur.fetchone()
    cur.execute("DELETE FROM bplog WHERE id = (SELECT MAX(id) FROM bplog)")
    print(f"Last record deleted: {deleted_record}")
    conn.commit()


def parse_date_and_blood_pressure(args: argparse.Namespace) -> tuple:
    """Parse the measurement data from args.

    Args:
        args (argparse.Namespace): CLI arguments

    Returns:
        tuple: Tuple containing systolic, diastolic and date
    """
    measurement = args.bp.split(":")
    systolic = int(measurement[0])
    diastolic = int(measurement[1])

    date_format_1 = "%d,%m,%Y"
    date_format_2 = "%Y-%m-%d"
    date_str = args.date or dt.datetime.now().strftime(date_format_1)

    try:
        date_obj = dt.datetime.strptime(date_str, date_format_1)
    except ValueError:
        date_obj = dt.datetime.strptime(date_str, date_format_2)

    db_date_format = "%Y-%m-%d"
    db_date_str = date_obj.strftime(db_date_format)
    return systolic, diastolic, db_date_str


def add_measurement(
    conn: sqlite3.Connection,
    args: argparse.Namespace,
    systolic: int,
    diastolic: int,
    date_str: str,
) -> None:
    """Add a new blood pressure measurement .

    Args:
        conn (sqlite3.Connection): Database connection handle
        args (argparse.Namespace): CLI arguments
        systolic (int): Numeric systolic value
        diastolic (int): Numeric diastolic value
        date_str (str): Date of measurement
    """
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
    """Return list of all records in the database.

    Args:
        conn (sqlite3.Connection): Database connection handle

    Returns:
        list: List of all records in the database
    """
    cur = conn.cursor()
    cur.execute("SELECT * FROM bplog ORDER BY date, time")
    return cur.fetchall()


def generate_list_table(records: list) -> str:
    """Generate a pretty table from a list of dictionaries .

    If prettytable is not installed, generate the table without pretty formatting

    Args:
        records (list): All records in list form

    Raises:
        ValueError: If the record does not containg 6 values
        (id, date, time, systolic, diastolic, comment)

    Returns:
        str: Return string either in raw or in prettytable format
    """
    sum_dia_values = 0
    sum_sys_values = 0
    try:
        from prettytable import PrettyTable

        table = PrettyTable(["Date", "Time", "Blood Pressure", "Comment"])
        for index, record in enumerate(records):
            if len(record) != 6:
                raise ValueError(f"Unexpected row format: {record}")
            bloodpressure = f"{record[3]}:{record[4]}"
            sum_sys_values = sum_sys_values + record[3]
            sum_dia_values = sum_dia_values + record[4]
            if index == len(records) - 1:
                table.add_row(
                    [record[1], record[2], bloodpressure, record[5]], divider=True
                )
            else:
                table.add_row([record[1], record[2], bloodpressure, record[5]])
        avg_sys = round(sum_sys_values / len(records))
        avg_dia = round(sum_dia_values / len(records))

        table.add_row(
            ["Records", len(records), "Average", f"{avg_sys}:{avg_dia}"], divider=True
        )
        return str(table)
    except ImportError as import_error:
        output = []
        for record in records:
            if len(record) != 6:
                raise ValueError(f"Unexpected row format: {record}") from import_error
            bloodpressure = f"{record[3]}:{record[4]}"
            sum_sys_values = sum_sys_values + record[3]
            sum_dia_values = sum_dia_values + record[4]
            output.append(f"{record[1]}\t{record[2]}\t{bloodpressure}\t{record[5]}")
        avg_sys = round(sum_sys_values / len(records))
        avg_dia = round(sum_dia_values / len(records))
        output.append(f"Records: {len(records)}, Average: {avg_sys}:{avg_dia}")

        return "\n".join(output)


def list_all_records(conn: sqlite3.Connection) -> str:
    """Gather all records in a list.

    Args:
        conn (sqlite3.Connection): Database connection handle

    Returns:
        str: Formatted table
    """
    records = get_all_records(conn)
    table = generate_list_table(records)
    conn.close()
    return table


def plot_blood_pressures(conn: sqlite3.Connection) -> None:
    """Plot blood pressure data if matplotlib is installed.

    Args:
        conn (sqlite3.Connection): Database connection handle
    """
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

    if not rows:
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

    fig, axes = plt.subplots()
    axes.plot(dates_times, systolics, "-o", color="red", zorder=0, label="systolic")
    axes.plot(dates_times, diastolics, "-o", color="blue", zorder=0, label="diastolic")

    plot = axes.scatter(
        dates_times, systolics, c=time_indices, cmap=cmap, vmin=0, vmax=1
    )
    axes.scatter(dates_times, diastolics, c=time_indices, cmap=cmap, vmin=0, vmax=1)

    cbar = fig.colorbar(plot)
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

    # don't run if non-GUI backend is used during testing
    if plt.get_backend() != "agg":
        plt.show()  # pragma: no cover


def export_to_csv(conn: sqlite3.Connection) -> None:
    """Export the database to csv.

    Args:
        conn (sqlite3.Connection): Database connection handle
    """
    cur = conn.cursor()
    data = cur.execute("SELECT * FROM bplog")
    with open("bplog_database.csv", "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["date", "time", "systolic", "diastolic", "comment"])
        writer.writerows(data)


def get_db_path(db_config: str = "") -> Path:
    """Get the database path from config file.

    Args:
        db_config (str): Argument holding config path if provided. Defaults to None.

    Returns:
        Path: Path to the database
    """
    if not db_config:
        config = configparser.ConfigParser()
        try:
            config.read("config.ini")
            db_file_path = (
                config["Database"]["file_path"]
                if "Database" in config and "file_path" in config["Database"]
                else str(Path("src") / "bplog" / "bplog.db")
            )
        except configparser.Error as parse_error:
            print(f"Error reading config file: {parse_error}")
            db_file_path = str(Path("src") / "bplog" / "bplog.db")
        return Path(db_file_path).parent / f"{Path(db_file_path).stem}.db"
    elif db_config == ".":
        return Path(Path.cwd()) / "bplog.db"
    else:
        return Path(db_config)


def update_db_config(db_path: Path) -> None:
    """Update the configuration of a database .

    Args:
        db_path (Path): [description]
    """
    config = configparser.ConfigParser()
    try:
        if (
            config.read("config.ini")
            and "Database" in config
            and "file_path" in config["Database"]
        ):
            if db_path != config["Database"]["file_path"]:
                config.set("Database", "file_path", str(db_path))
                with open("config.ini", "w", encoding="utf-8") as config_file:
                    config.write(config_file)
        elif db_path != Path("src") / "bplog" / "bplog.db":
            config["Database"] = {"file_path": str(db_path)}
            with open("config.ini", "w", encoding="utf-8") as second_config_file:
                config.write(second_config_file)
    except (configparser.Error, IOError) as config_error:
        print(f"Error updating config file: {config_error}")


def connect_to_database(
    use_in_memory: bool,
    db_config: str = "",
) -> sqlite3.Connection:
    """Connect to the database.

    Args:
        use_in_memory (bool): Use an in-memory database for unittesting
        db_config (str): Argument holding config path if provided. Defaults to None.

    Raises:
        Exception: If any exception occurs connnecting to the database

    Returns:
        sqlite3.Connection: Database connection handle
    """
    if use_in_memory:
        conn = sqlite3.connect(":memory:")
    else:
        db_path = get_db_path(db_config)
        update_db_config(db_path)
        try:
            conn = sqlite3.connect(db_path)
            database_setup(conn)
        except Exception as conn_error:
            print(f"Error connecting to database: {conn_error}")
            raise
    return conn


def reset_db_path_config() -> None:
    """Remove config.ini file."""
    config_file = Path("config.ini")
    if config_file.exists():
        config_file.unlink()


def handle_reset_config(
    conn: sqlite3.Connection,
    args: argparse.Namespace,
) -> None:
    """Handle a reset of the database path configuration and exit.

    Args:
        conn (sqlite3.Connection): Database connection handle
        args (argparse.Namespace): CLI arguments
    """
    reset_db_path_config()
    sys.exit(0)


def handle_remove_last_record(
    conn: sqlite3.Connection,
    args: argparse.Namespace,
) -> None:
    """Handle remove last record from the database.

    Args:
        conn (sqlite3.Connection): Database connection handle
        args (argparse.Namespace): CLI arguments
    """
    delete_last_record_added(conn)


def handle_remove_measurement(
    conn: sqlite3.Connection,
    args: argparse.Namespace,
) -> None:
    """Handle remove measurement from database.

    Args:
        conn (sqlite3.Connection): Database connection handle
        args (argparse.Namespace): CLI arguments
    """
    date = input("Enter date of measurement to remove (YYYY-MM-DD): ")
    remove_measurement_by_date(conn, date)


def handle_list_records(
    conn: sqlite3.Connection,
    args: argparse.Namespace,
) -> None:
    """Handle printing a list of records to the console.

    Args:
        conn (sqlite3.Connection): Database connection handle
        args (argparse.Namespace): CLI arguments
    """
    print(list_all_records(conn))
    sys.exit(0)


def handle_export_to_csv(
    conn: sqlite3.Connection,
    args: argparse.Namespace,
) -> None:
    """Handle export_to_csv.

    Args:
        conn (sqlite3.Connection): Database connection handle
        args (argparse.Namespace): CLI arguments
    """
    export_to_csv(conn)


def handle_add_measurement(
    conn: sqlite3.Connection,
    args: argparse.Namespace,
) -> None:
    """Handle adding a measurement to the database.

    Args:
        conn (sqlite3.Connection): Database connection handle
        args (argparse.Namespace): CLI arguments
    """
    systolic, diastolic, date_str = parse_date_and_blood_pressure(args)
    add_measurement(conn, args, systolic, diastolic, date_str)


def handle_plot_blood_pressures(
    conn: sqlite3.Connection,
    args: argparse.Namespace,
) -> None:
    """Handle plotting a blood pressure graph.

    Args:
        conn (sqlite3.Connection): Database connection handle
        args (argparse.Namespace): CLI arguments
    """
    plot_blood_pressures(conn)
    sys.exit(0)


handlers: dict = {
    "reset_config": handle_reset_config,
    "rl": handle_remove_last_record,
    "rm": handle_remove_measurement,
    "list": handle_list_records,
    "csv": handle_export_to_csv,
    "bp": handle_add_measurement,
}


def main() -> None:  # pragma: no cover
    """Set main entry point for bplog."""
    args = setup_cli_parser()

    if args.config:
        conn = connect_to_database(args.in_memory, args.config)
    else:
        conn = connect_to_database(args.in_memory)

    for arg, bplog_handler in handlers.items():
        if getattr(args, arg):
            bplog_handler(conn, args)

    if not args.rl:
        plot_blood_pressures(conn)

    conn.close()


if __name__ == "__main__":
    main()  # pragma no cover
