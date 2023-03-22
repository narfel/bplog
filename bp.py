""" # flake8: noqa """
import argparse
import datetime as dt
import sqlite3
import sys

from matplotlib import pyplot as plt


def setup_cli_parser():
    # Set up the command-line argument parser
    parser = argparse.ArgumentParser(
        description="Record and graph blood pressure measurements",
    )
    parser.add_argument(
        "bp",
        nargs="?",
        action="store",
        help="The blood pressure measurement to insert into the database (e.g. 120:80)",
    )
    parser.add_argument("--list", action="store_true", help="List all records")
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help='date of measurement in the form "YYYY-MM-DD" (default: today)',
    )
    parser.add_argument(
        "--time",
        type=str,
        default=None,
        help='time of measurement in the form "HH:MM" (default: current time)',
    )
    parser.add_argument(
        "--remove",
        action="store_true",
        help="remove an existing entry",
    )
    parser.add_argument(
        "-rm",
        action="store_true",
        help="remove record",
    )
    parser.add_argument(
        "-rl",
        action="store_true",
        help="remove last record added",
    )
    parser.add_argument(
        "--comment",
        type=str,
        default=None,
        help="comment for the measurement",
    )
    return parser.parse_args()


def database_setup(conn):
    # create table if it doesn't exist
    cur = conn.cursor()
    cur.execute(
        """CREATE TABLE IF NOT EXISTS blood_pressure
                (id INT INTEGER PRIMARY KEY, date TEXT, time TEXT, systolic INTEGER, diastolic INTEGER, comment TEXT)"""
    )
    # Create an index on the date and time columns if it doesn't exist
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_blood_pressure_date_time ON blood_pressure(date, time)",
    )
    conn.commit()


def delete_record(conn, record_id):
    sql = "DELETE FROM blood_pressure WHERE id = ?"
    cur = conn.cursor()
    cur.execute(sql, (record_id,))
    conn.commit()


def remove_measurement(conn, date):
    rows = get_record_by_date(conn, date)
    if not rows:
        print(f"No measurements found for {date}")
        return
    elif len(rows) == 1:
        delete_record(conn, rows[0][0])
        print(f"Measurement removed: {rows[0]}")
    else:
        handle_multiple_records(rows, date, conn)


def handle_multiple_records(rows, date, conn):
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


def get_record_by_date(conn, date):
    sql = "SELECT * FROM blood_pressure WHERE date(date) = ? ORDER BY time"
    cur = conn.cursor()
    cur.execute(sql, (date,))
    return cur.fetchall()


def delete_last_record_added():
    conn = sqlite3.connect("blood_pressure.db")
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM blood_pressure WHERE id = (SELECT MAX(id) FROM blood_pressure)"
    )
    deleted_record = cur.fetchone()
    cur.execute(
        "DELETE FROM blood_pressure WHERE id = (SELECT MAX(id) FROM blood_pressure)"
    )
    print(f"Last record deleted: {deleted_record}")
    conn.commit()
    conn.close()
    sys.exit()


def parse_date_and_blood_pressure(args, conn):
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
        sys.exit()


def add_measurement(conn, args, systolic, diastolic, date_str):
    """Add measurements to the database."""
    cur = conn.cursor()
    time_str = args.time or dt.datetime.now().strftime("%H:%M")
    comment = args.comment or ""
    cur.execute(
        "INSERT INTO blood_pressure (date, time, systolic, diastolic, comment) VALUES (?, ?, ?, ?, ?)",
        (date_str, time_str, systolic, diastolic, comment),
    )
    conn.commit()
    print(
        f"Blood pressure measurement added: {systolic}/{diastolic} ({date_str} {time_str})",
    )


def list_all_records(conn):
    cur = conn.cursor()
    cur.execute("SELECT * FROM blood_pressure ORDER BY date, time")
    records = cur.fetchall()

    try:
        from prettytable import PrettyTable

        table = PrettyTable(["Date", "Time", "Blood Pressure", "Comment"])
        for record in records:
            bp = f"{record[3]}:{record[4]}"
            table.add_row([record[1], record[2], bp, record[5]])
        print(table)
    except ImportError:
        # If prettytable is not installed, print the table without pretty formatting
        for record in records:
            bp = f"{record[3]}:{record[4]}"
            print(f"{record[1]}\t{record[2]}\t{bp}")
    sys.exit(0)


def plot_blood_pressures(conn):
    cur = conn.cursor()
    cur.execute(
        "SELECT date, time, systolic, diastolic FROM blood_pressure ORDER BY date, time",
    )
    rows = cur.fetchall()

    dates_times = [
        dt.datetime.strptime(f"{row[0]} {row[1]}", "%Y-%m-%d %H:%M") for row in rows
    ]
    systolics = [row[2] for row in rows]
    diastolics = [row[3] for row in rows]

    cmap = plt.get_cmap("plasma")
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
    plt.axhline(y=80, color="black", linestyle=":")
    plt.axhline(y=120, color="black", linestyle=":")
    plt.xlabel("Date")
    plt.ylabel("Blood Pressure (mmHg)")
    plt.title("Blood Pressure over Time")

    plt.show()


def main():
    # connect to the database and create the table if necessary
    conn = sqlite3.connect("blood_pressure.db")
    database_setup(conn)

    args = setup_cli_parser()

    if args.rl:
        delete_last_record_added()

    if args.rm:
        date = input("Enter date of measurement to remove (YYYY-MM-DD): ")
        remove_measurement(conn, date)

    if args.list:
        list_all_records(conn)

    # Parse the blood pressure measurement and the date
    systolic, diastolic, date_str = parse_date_and_blood_pressure(args, conn)

    # write input blood pressure to database
    add_measurement(conn, args, systolic, diastolic, date_str)

    # plot
    plot_blood_pressures(conn)

    # Close the database connection
    conn.close()


if __name__ == "__main__":
    main()
