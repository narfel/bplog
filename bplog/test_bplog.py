"""Unittest."""
import argparse
import os
import sqlite3
import sys
import unittest
from io import StringIO
from unittest.mock import MagicMock, patch

import matplotlib
from matplotlib import pyplot as plt

from bplog import bplog

matplotlib.use("Agg")


class TestBplog(unittest.TestCase):
    def test_connect_to_database(self):
        with patch.dict(os.environ, {"BPLOG_DB_PATH": ":memory:"}):
            conn = bplog.connect_to_database()
            self.assertIsInstance(conn, sqlite3.Connection)
            conn.close()

    def test_setup_cli_parser(self) -> None:
        with patch(
            "sys.argv",
            [
                "bplog",
                "120:80",
                "--date",
                "2023-12-12",
                "--time",
                "11:11",
                "-rm",
                "-rl",
                "--comment",
                "moin",
            ],
        ):
            test_args = bplog.setup_cli_parser()

        self.assertEqual(test_args.bp, "120:80")
        self.assertEqual(test_args.date, "2023-12-12")
        self.assertEqual(test_args.time, "11:11")
        self.assertTrue(test_args.rm)
        self.assertTrue(test_args.rl)
        self.assertEqual(test_args.comment, "moin")

    def test_database_setup(self) -> None:
        conn = sqlite3.connect(":memory:")
        bplog.database_setup(conn)
        cur = conn.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='bplog'"
        )
        db_result_bplog = cur.fetchone()
        self.assertIsNotNone(db_result_bplog)

        # Assert idx_bplog_date_time
        cur.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name='idx_bplog_date_time'"
        )
        db_index = cur.fetchone()[0]
        self.assertEqual(db_index, 1)
        conn.close()

    def test_delete_record(self) -> None:
        conn = sqlite3.connect(":memory:")
        bplog.database_setup(conn)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO bplog (date, time, systolic, diastolic, comment) VALUES (?, ?, ?, ?, ?)",
            ("2020-03-03", "11:00", 120, 80, "Lorem Ipsum"),
        )
        cur.execute("SELECT id, date, time, systolic, diastolic, comment FROM bplog")
        rows = cur.fetchall()
        self.assertEqual(rows, [(1, "2020-03-03", "11:00", 120, 80, "Lorem Ipsum")])
        # run func
        bplog.delete_record(conn, 1)
        # assert empty
        empty_rows = cur.fetchall()
        self.assertEqual(empty_rows, [])
        conn.close()

    def test_get_record_by_date(self) -> None:
        conn = sqlite3.connect(":memory:")
        bplog.database_setup(conn)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO bplog (date, time, systolic, diastolic, comment) VALUES (?, ?, ?, ?, ?)",
            ("2020-03-03", "11:00", 120, 80, "Lorem Ipsum"),
        )
        bplog.get_record_by_date(conn, "2020-03-03")
        deleted_record = cur.fetchall()
        # assert empty
        self.assertEqual(deleted_record, [])
        conn.close()

    def test_delete_last_record_added(self):
        conn = sqlite3.connect(":memory:")
        bplog.database_setup(conn)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO bplog (date, time, systolic, diastolic, comment) VALUES (?, ?, ?, ?, ?)",
            ("2020-03-03", "11:00", 120, 80, "Lorem Ipsum"),
        )
        with patch("builtins.print") as mock_print:
            bplog.delete_last_record_added(conn)
            deleted_record = cur.fetchall()
            # assert empty
            self.assertEqual(deleted_record, [])
            # assert print statement
            mock_print.assert_called_with(
                "Last record deleted: (1, '2020-03-03', '11:00', 120, 80, 'Lorem Ipsum')"
            )
        conn.close()


class TestRemoveMeasurementByDate(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        bplog.database_setup(self.conn)
        self.conn.execute(
            "INSERT INTO bplog (date, time, systolic, diastolic, comment) VALUES (?, ?, ?, ?, ?)",
            ("2020-03-03", "11:01", 121, 81, "Lorem Ipsum"),
        )
        self.conn.execute(
            "INSERT INTO bplog (date, time, systolic, diastolic, comment) VALUES (?, ?, ?, ?, ?)",
            ("2020-03-03", "11:02", 122, 82, "Lorem Ipsum  2"),
        )
        self.conn.execute(
            "INSERT INTO bplog (date, time, systolic, diastolic, comment) VALUES (?, ?, ?, ?, ?)",
            ("2020-03-05", "11:03", 123, 83, "Lorem Ipsum 3"),
        )

    def tearDown(self):
        self.conn.close()

    def test_remove_single_measurement(self):
        with unittest.mock.patch("builtins.print") as mock_print:
            bplog.remove_measurement_by_date(self.conn, "2020-03-05")
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM bplog WHERE date = '2020-03-05'")
            count = cursor.fetchone()[0]
            self.assertEqual(count, 0)
            mock_print.assert_called_once_with(
                "Measurement removed: (3, '2020-03-05', '11:03', 123, 83, 'Lorem Ipsum 3')"
            )

    def test_no_measurements_found(self):
        # Test removing a date with no measurements
        with unittest.mock.patch("builtins.print") as mock_print:
            bplog.remove_measurement_by_date(self.conn, "2022-01-03")
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM bplog")
            count = cursor.fetchone()[0]
            self.assertEqual(count, 3)
            mock_print.assert_called_once_with("No measurements found for 2022-01-03")

    def test_remove_multiple_wrong_date(self):
        with unittest.mock.patch("builtins.print") as mock_print:
            with unittest.mock.patch("builtins.input", return_value="12:10"):
                bplog.remove_measurement_by_date(self.conn, "2020-03-03")
                cursor = self.conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM bplog WHERE date = '2020-03-03'")
                count = cursor.fetchone()[0]
                self.assertEqual(count, 2)
                mock_print.assert_has_calls(
                    [
                        unittest.mock.call("2 measurements found for 2020-03-03:"),
                        unittest.mock.call("2020-03-03 11:01 - 121:81"),
                        unittest.mock.call("2020-03-03 11:02 - 122:82"),
                        unittest.mock.call(
                            "No measurement found for 2020-03-03 at time 12:10",
                        ),
                    ],
                )

    def test_remove_multiple_measurements(self):
        with unittest.mock.patch("builtins.print") as mock_print:
            with unittest.mock.patch("builtins.input", return_value="11:01"):
                bplog.remove_measurement_by_date(self.conn, "2020-03-03")
                cursor = self.conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM bplog WHERE date = '2020-03-03'")
                count = cursor.fetchone()[0]
                self.assertEqual(count, 1)
                mock_print.assert_has_calls(
                    [
                        unittest.mock.call("2 measurements found for 2020-03-03:"),
                        unittest.mock.call("2020-03-03 11:01 - 121:81"),
                        unittest.mock.call("2020-03-03 11:02 - 122:82"),
                        unittest.mock.call(
                            "Measurement removed: 2020-03-03 11:01 - 121:81 (id:1)"
                        ),
                    ],
                )


class TestAddMeasurement(unittest.TestCase):
    def test_add_measurement(self):
        conn = sqlite3.connect(":memory:")
        bplog.database_setup(conn)
        mock_args = {"time": "09:50", "comment": "Lorem Ipsum"}
        args = argparse.Namespace(**mock_args)

        with unittest.mock.patch("builtins.print") as mock_print:
            bplog.add_measurement(conn, args, 120, 80, "2020-02-02")
            mock_print.assert_called_once_with(
                "Blood pressure measurement added: 120/80 (2020-02-02 09:50)"
            )
            cur = conn.cursor()
            cur.execute(
                "SELECT id, date, time, systolic, diastolic, comment FROM bplog"
            )
            rows = cur.fetchall()
            self.assertEqual(rows, [(1, "2020-02-02", "09:50", 120, 80, "Lorem Ipsum")])

        conn.close()


class TestParsing(unittest.TestCase):
    def test_parse_date_and_blood_pressure(self):
        conn = sqlite3.connect(":memory:")
        bplog.database_setup(conn)
        mock_args = {"bp": "09:50", "date": "02,02,2020"}
        args = argparse.Namespace(**mock_args)
        returned_values = bplog.parse_date_and_blood_pressure(args, conn)
        self.assertEqual(returned_values, (9, 50, "2020-02-02"))

    def test_parse_date_and_blood_pressure_else(self):
        conn_mock = MagicMock()

        plot_blood_pressures_mock = MagicMock()
        with patch("bplog.bplog.plot_blood_pressures", plot_blood_pressures_mock):
            mock_args = {"bp": None, "date": "02,02,2020"}
            args = argparse.Namespace(**mock_args)

            sys_exit_mock = MagicMock()
            with patch("sys.exit", sys_exit_mock):
                bplog.parse_date_and_blood_pressure(args, conn_mock)
                sys_exit_mock.assert_called_once()


class TestListAllRecords(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        bplog.database_setup(self.conn)
        self.conn.execute(
            "INSERT INTO bplog (date, time, systolic, diastolic, comment) VALUES (?, ?, ?, ?, ?)",
            ("2020-03-03", "11:01", 121, 81, "Lorem Ipsum"),
        )
        self.conn.execute(
            "INSERT INTO bplog (date, time, systolic, diastolic, comment) VALUES (?, ?, ?, ?, ?)",
            ("2020-03-03", "11:02", 122, 82, "Lorem Ipsum  2"),
        )
        self.conn.execute(
            "INSERT INTO bplog (date, time, systolic, diastolic, comment) VALUES (?, ?, ?, ?, ?)",
            ("2020-03-05", "11:03", 123, 83, "Lorem Ipsum 3"),
        )

    def tearDown(self) -> None:
        self.conn.close()

    def test_get_all_records(self):
        return_list = bplog.get_all_records(self.conn)
        return_list_expected = [
            (1, "2020-03-03", "11:01", 121, 81, "Lorem Ipsum"),
            (2, "2020-03-03", "11:02", 122, 82, "Lorem Ipsum  2"),
            (3, "2020-03-05", "11:03", 123, 83, "Lorem Ipsum 3"),
        ]
        self.assertEqual(return_list, return_list_expected)

    def test_list_all_records(self):
        records = bplog.list_all_records(self.conn)
        self.assertIsInstance(records, str)

    def test_list_all_records_import_error(self):
        def import_mock(name, *args):
            if name == "prettytable":
                raise ImportError

        with patch("builtins.__import__", side_effect=import_mock):
            returned_str = bplog.list_all_records(self.conn)
            expected_str = "2020-03-03\t11:01\t121:81\tLorem Ipsum\n2020-03-03\t11:02\t122:82\tLorem Ipsum  2\n2020-03-05\t11:03\t123:83\tLorem Ipsum 3"
            self.assertEqual(returned_str, expected_str)


class TestTableError(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        bplog.database_setup(self.conn)
        self.conn.execute(
            "INSERT INTO bplog (date, time, systolic, diastolic, comment) VALUES (?, ?, ?, ?, ?)",
            ("2020-03-03", "11:01", 121, 81, "Lorem Ipsum"),
        )
        self.conn.execute(
            "INSERT INTO bplog (date, time, systolic, diastolic, comment) VALUES (?, ?, ?, ?, ?)",
            ("2020-03-03", "11:02", 122, 82, "Lorem Ipsum  2"),
        )
        self.conn.execute(
            "INSERT INTO bplog (date, time, systolic, diastolic) VALUES (?, ?, ?, ?)",
            ("2020-03-05", "11:03", 123, 83),
        )

    def tearDown(self) -> None:
        self.conn.close()

    def test_generate_table_error(self):
        records = [
            (1, "2020-03-03", "11:01", 121, 81, "Lorem Ipsum"),
            (2, "2020-03-03", "11:02", 122, 82, "Lorem Ipsum  2"),
            (3, "2020-03-05", "11:03", 123, 83),
        ]
        with self.assertRaises(ValueError):
            bplog.generate_table(records)


class TestPlotFunc(unittest.TestCase):
    def test_plot_blood_pressures(self):
        conn = sqlite3.connect(":memory:")
        bplog.database_setup(conn)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO bplog (date, time, systolic, diastolic, comment) VALUES (?, ?, ?, ?, ?)",
            ("2020-03-03", "11:00", 120, 80, "Lorem Ipsum"),
        )
        bplog.plot_blood_pressures(conn)
        assert plt.fignum_exists(1)


class TestMain(unittest.TestCase):
    def test_main(self):
        conn = sqlite3.connect(":memory:")
        bplog.database_setup(conn)
        sys.argv = ["bplog", "130:90", "--date", "03,03,2023", "--time", "19:00"]

        # capture sys.stdout
        with StringIO() as mock_stdout:
            sys.stdout = mock_stdout
            bplog.main()
            output = mock_stdout.getvalue()
            expected_output = (
                "Blood pressure measurement added: 130/90 (2023-03-03 19:00)\n"
            )
            self.assertEqual(output, expected_output)

        # reset sys.stdout
        sys.stdout = sys.__stdout__
        conn.close()


if __name__ == "__main__":
    unittest.main()  # pragma no cover
