"""Unittest."""
import argparse
import configparser
import csv
import sqlite3
import textwrap
import unittest
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

# import matplotlib
# from matplotlib import pyplot as plt

from src.bplog import app

# matplotlib.use("agg")


def setup_test_database():
    conn = sqlite3.connect(":memory:")
    app.database_setup(conn)
    return conn


def clean_files(*file_paths):
    for file_path in file_paths:
        filename = Path(file_path)
        if filename.exists():
            filename.unlink()


class TestConnectToDatabase(unittest.TestCase):
    def test_connect_to_database(self):
        conn = app.connect_to_database(use_in_memory=True)
        self.assertIsInstance(conn, sqlite3.Connection)
        conn.close()

    def test_connect_to_database_else(self):
        conn = app.connect_to_database(use_in_memory=False, db_config="test.db")
        conn.close()
        clean_files("config.ini", "test.db")
        self.assertIsInstance(conn, sqlite3.Connection)

    def test_conn_error(self):
        with patch("sqlite3.connect") as mock_connect:
            mock_connect.side_effect = Exception("test error")
            with self.assertRaises(Exception) as cm:
                app.connect_to_database(False)
            self.assertEqual(str(cm.exception), "test error")


class TestHandles(unittest.TestCase):
    def test_handle_list_records(self):
        with patch("src.bplog.app.list_all_records") as mock_list:
            with patch("sys.exit") as mock_exit:
                mock_conn = Mock()
                mock_list.return_value = ["record1", "record2"]
                app.handle_list_records(mock_conn, None)
                mock_list.assert_called_once_with(mock_conn)
                mock_exit.assert_called_once_with(0)

    def test_handle_export_to_csv(self):
        with patch("src.bplog.app.export_to_csv") as mock_export:
            mock_conn = Mock()
            app.handle_export_to_csv(mock_conn, None)
            mock_export.assert_called_once_with(mock_conn)

    def test_handle_reset_config(self):
        with patch("src.bplog.app.reset_db_path_config"):
            with self.assertRaises(SystemExit):
                app.handle_reset_config(None, None)

    def test_handle_remove_measurement(self):
        with patch("src.bplog.app.remove_measurement_by_date") as mock_remove:
            mock_conn = Mock()
            date = "02-02-2023"
            with patch("builtins.input", return_value=date):
                app.handle_remove_measurement(mock_conn, date)
                mock_remove.assert_called_once_with(mock_conn, date)

    def test_handle_remove_last_record(self):
        with patch("src.bplog.app.delete_last_record_added") as mock_delete:
            mock_conn = Mock()
            app.handle_remove_last_record(mock_conn, None)
            mock_delete.assert_called_once_with(mock_conn)

    def test_handle_plot_blood_pressures(self):
        with patch("src.bplog.app.plot_blood_pressures") as mock_plot:
            with patch("sys.exit"):
                mock_conn = Mock()
                app.handle_plot_blood_pressures(mock_conn, None)
                mock_plot.assert_called_once_with(mock_conn)

    def test_handle_add_measurement(self):
        mock_args = argparse.Namespace(time=None, comment=None)
        with patch("src.bplog.app.add_measurement") as mock_add:
            with patch(
                "src.bplog.app.parse_date_and_blood_pressure",
                return_value=(120, 80, "02-02-2023 19:00"),
            ):
                mock_conn = Mock()
                app.handle_add_measurement(mock_conn, mock_args)
                mock_add.assert_called_once_with(
                    mock_conn, mock_args, 120, 80, "02-02-2023 19:00"
                )


class TestCLIParser(unittest.TestCase):
    def test_setup_cli_parser(self) -> None:
        with patch(
            "sys.argv",
            [
                "bplog",
                "120:80",
                "-d",
                "2023-12-12",
                "-t",
                "11:11",
                "-rm",
                "-rl",
                "-c",
                "test",
            ],
        ):
            test_args = app.setup_cli_parser()

        self.assertEqual(test_args.bp, "120:80")
        self.assertEqual(test_args.date, "2023-12-12")
        self.assertEqual(test_args.time, "11:11")
        self.assertTrue(test_args.rm)
        self.assertTrue(test_args.rl)
        self.assertEqual(test_args.comment, "test")


class TestDatabaseSetup(unittest.TestCase):
    def test_database_setup(self) -> None:
        conn = setup_test_database()
        cur = conn.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='bplog'",
        )
        db_result_bplog = cur.fetchone()
        self.assertIsNotNone(db_result_bplog)

        # Assert idx_bplog_date_time
        cur.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name='idx_bplog_date_time'",
        )
        db_index = cur.fetchone()[0]
        self.assertEqual(db_index, 1)
        conn.close()


class TestGetSetDelete(unittest.TestCase):
    def test_delete_record(self) -> None:
        conn = setup_test_database()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO bplog (date, time, systolic, diastolic, comment) VALUES (?, ?, ?, ?, ?)",
            ("2020-03-03", "11:00", 120, 80, "Lorem Ipsum"),
        )
        cur.execute("SELECT id, date, time, systolic, diastolic, comment FROM bplog")
        rows = cur.fetchall()
        self.assertEqual(rows, [(1, "2020-03-03", "11:00", 120, 80, "Lorem Ipsum")])
        app.delete_record(conn, 1)
        empty_rows = cur.fetchall()
        self.assertEqual(empty_rows, [])
        conn.close()

    def test_get_record_by_date(self) -> None:
        conn = setup_test_database()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO bplog (date, time, systolic, diastolic, comment) VALUES (?, ?, ?, ?, ?)",
            ("2020-03-03", "11:00", 120, 80, "Lorem Ipsum"),
        )
        app.get_record_by_date(conn, "2020-03-03")
        deleted_record = cur.fetchall()
        self.assertEqual(deleted_record, [])
        conn.close()

    def test_delete_last_record_added(self):
        conn = setup_test_database()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO bplog (date, time, systolic, diastolic, comment) VALUES (?, ?, ?, ?, ?)",
            ("2020-03-03", "11:00", 120, 80, "Lorem Ipsum"),
        )
        with patch("builtins.print") as mock_print:
            app.delete_last_record_added(conn)
            deleted_record = cur.fetchall()
            self.assertEqual(deleted_record, [])
            mock_print.assert_called_with(
                "Last record deleted: (1, '2020-03-03', '11:00', 120, 80, 'Lorem Ipsum')",
            )
        conn.close()

    def test_add_measurement(self):
        conn = setup_test_database()
        mock_args = {"time": "09:50", "comment": "Lorem Ipsum"}
        args = argparse.Namespace(**mock_args)

        with patch("builtins.print") as mock_print:
            app.add_measurement(conn, args, 120, 80, "2020-02-02")
            mock_print.assert_called_once_with(
                "Blood pressure measurement added: 120/80 (2020-02-02 09:50)",
            )
            cur = conn.cursor()
            cur.execute(
                "SELECT id, date, time, systolic, diastolic, comment FROM bplog",
            )
            rows = cur.fetchall()
            self.assertEqual(rows, [(1, "2020-02-02", "09:50", 120, 80, "Lorem Ipsum")])

        conn.close()


class TestRemoveMeasurementByDate(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        app.database_setup(self.conn)
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
        with patch("builtins.print") as mock_print:
            app.remove_measurement_by_date(self.conn, "2020-03-05")
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM bplog WHERE date = '2020-03-05'")
            count = cursor.fetchone()[0]
            self.assertEqual(count, 0)
            mock_print.assert_called_once_with(
                "Measurement removed: (3, '2020-03-05', '11:03', 123, 83, 'Lorem Ipsum 3')",
            )

    def test_no_measurements_found(self):
        # Test removing a date with no measurements
        with patch("builtins.print") as mock_print:
            app.remove_measurement_by_date(self.conn, "2022-01-03")
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM bplog")
            count = cursor.fetchone()[0]
            self.assertEqual(count, 3)
            mock_print.assert_called_once_with("No measurements found for 2022-01-03")

    def test_remove_multiple_wrong_date(self):
        with patch("builtins.print") as mock_print:
            with patch("builtins.input", return_value="12:10"):
                app.remove_measurement_by_date(self.conn, "2020-03-03")
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
        with patch("builtins.print") as mock_print:
            with unittest.mock.patch("builtins.input", return_value="11:01"):
                app.remove_measurement_by_date(self.conn, "2020-03-03")
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
                            "Measurement removed: 2020-03-03 11:01 - 121:81 (id:1)",
                        ),
                    ],
                )


class TestExportToCsv(unittest.TestCase):
    def test_export_to_csv(self):
        conn = sqlite3.connect(":memory:")
        cur = conn.cursor()
        cur.execute(
            "CREATE TABLE bplog (date text, time text, systolic integer,"
            "diastolic integer, comment text)",
        )
        cur.execute(
            "INSERT INTO bplog VALUES ('2022-01-01', '12:00', 120, 80, 'test comment')",
        )
        conn.commit()
        app.export_to_csv(conn)
        with open("bplog_database.csv", "r", newline="", encoding="utf-8") as csv_file:
            reader = csv.reader(csv_file)
            header = next(reader)
            expected = list(reader)
        self.assertEqual(header, ["date", "time", "systolic", "diastolic", "comment"])
        self.assertEqual(
            expected, [["2022-01-01", "12:00", "120", "80", "test comment"]]
        )
        clean_files("bplog_database.csv")
        conn.close()


class TestNoData(unittest.TestCase):
    def test_plot_blood_pressure(self):
        with patch("builtins.print") as mock_print:
            conn = setup_test_database()
            app.plot_blood_pressures(conn)
            mock_print.assert_called_once_with("No data to plot")


class TestParsing(unittest.TestCase):
    def test_parse_date_and_blood_pressure_year1(self):
        setup_test_database()
        mock_args = {"bp": "09:50", "date": "02,02,2020"}
        args = argparse.Namespace(**mock_args)
        returned_values = app.parse_date_and_blood_pressure(args)
        self.assertEqual(returned_values, (9, 50, "2020-02-02"))

    def test_parse_date_and_blood_pressure_year2(self):
        setup_test_database()
        mock_args = {"bp": "09:50", "date": "2020-02-02"}
        args = argparse.Namespace(**mock_args)
        returned_values = app.parse_date_and_blood_pressure(args)
        self.assertEqual(returned_values, (9, 50, "2020-02-02"))


class TestListAllRecords(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        app.database_setup(self.conn)
        sql_data = [
            ("2020-03-03", "11:01", 121, 81, "Lorem Ipsum"),
            ("2020-03-03", "11:02", 122, 82, "Lorem Ipsum  2"),
            ("2020-03-05", "11:03", 123, 83, "Lorem Ipsum 3"),
        ]
        self.conn.executemany(
            "INSERT INTO bplog (date, time, systolic, diastolic, comment) VALUES (?, ?, ?, ?, ?)",
            sql_data,
        )

    def tearDown(self) -> None:
        self.conn.close()

    def test_get_all_records(self):
        return_list = app.get_all_records(self.conn)
        return_list_expected = [
            (1, "2020-03-03", "11:01", 121, 81, "Lorem Ipsum"),
            (2, "2020-03-03", "11:02", 122, 82, "Lorem Ipsum  2"),
            (3, "2020-03-05", "11:03", 123, 83, "Lorem Ipsum 3"),
        ]
        self.assertEqual(return_list, return_list_expected)

    def test_list_all_records(self):
        records = app.list_all_records(self.conn)
        self.assertIsInstance(records, str)

    def test_list_all_records_no_records(self):
        with patch("src.bplog.app.get_all_records", return_value=None):
            with patch("builtins.print") as mock_print:
                app.list_all_records(self.conn)
                mock_print.assert_called_with("No data to list")

    def test_list_all_records_import_error(self):
        def import_mock(name, *args):
            if name == "prettytable":
                raise ImportError

        with patch("builtins.__import__", side_effect=import_mock):
            returned_str = app.list_all_records(self.conn)
            expected_str = textwrap.dedent(
                """\
                2020-03-03\t11:01\t121:81\tLorem Ipsum
                2020-03-03\t11:02\t122:82\tLorem Ipsum  2
                2020-03-05\t11:03\t123:83\tLorem Ipsum 3
                Records: 3, Average: 122:82"""
            )
            self.assertEqual(returned_str, expected_str)


class TestTableError(unittest.TestCase):
    def test_generate_table_error_prettytable(self):
        conn = setup_test_database()
        sql_data = [
            ("2020-03-03", "11:01", 121, 81, "Lorem Ipsum"),
            ("2020-03-03", "11:02", 122, 82, "Lorem Ipsum 2"),
            ("2020-03-05", "11:03", 123, 83, None),
        ]
        conn.executemany(
            "INSERT INTO bplog (date, time, systolic, diastolic, comment) VALUES (?, ?, ?, ?, ?)",
            sql_data,
        )
        records = [
            (1, "2020-03-03", "11:01", 121, 81, "Lorem Ipsum"),
            (2, "2020-03-03", "11:02", 122, 82, "Lorem Ipsum  2"),
            (3, "2020-03-05", "11:03", 123, 83),
        ]
        with self.assertRaises(ValueError):
            app.generate_list_table(records)
        conn.close()

    def test_generate_table_error_no_prettytable(self):
        conn = setup_test_database()
        sql_data = [
            ("2020-03-03", "11:01", 121, 81, "Lorem Ipsum"),
            ("2020-03-03", "11:02", 122, 82, "Lorem Ipsum 2"),
            ("2020-03-05", "11:03", 123, 83, None),
        ]
        conn.executemany(
            "INSERT INTO bplog (date, time, systolic, diastolic, comment) VALUES (?, ?, ?, ?, ?)",
            sql_data,
        )
        records = [
            (1, "2020-03-03", "11:01", 121, 81, "Lorem Ipsum"),
            (2, "2020-03-03", "11:02", 122, 82, "Lorem Ipsum  2"),
            (3, "2020-03-05", "11:03", 123, 83),
        ]

        import_mock = Mock(side_effect=ImportError)
        with patch("builtins.__import__", side_effect=import_mock):
            with self.assertRaises(ValueError):
                app.generate_list_table(records)
        conn.close()


# class TestPlotFunc(unittest.TestCase):
#     def test_plot_blood_pressures_data(self):
#         conn = setup_test_database()
#         cur = conn.cursor()
#         cur.execute(
#             "INSERT INTO bplog (date, time, systolic, diastolic, comment) VALUES (?, ?, ?, ?, ?)",
#             ("2020-03-03", "11:00", 120, 80, "Lorem Ipsum"),
#         )
#         app.plot_blood_pressures(conn)
#         self.assertTrue(plt.fignum_exists(1))

#     @patch.dict("sys.modules", {"matplotlib": None})
#     def test_plot_blood_pressures_sysexit(self):
#         conn = setup_test_database()
#         cur = conn.cursor()
#         cur.execute(
#             "INSERT INTO bplog (date, time, systolic, diastolic, comment) VALUES (?, ?, ?, ?, ?)",
#             ("2020-03-03", "11:00", 120, 80, "Lorem Ipsum"),
#         )
#         with self.assertRaises(SystemExit):
#             app.plot_blood_pressures(conn)


class TestDatabasePath(unittest.TestCase):
    def test_reset_db_path_config(self):
        config_file = Path("config.ini")
        with open(config_file, "w", encoding="utf-8") as cfg:
            cfg.write("dummy content")
        app.reset_db_path_config()
        self.assertFalse(config_file.exists())

    def test_get_db_path_string(self):
        db_config = "daterbeys"
        return_val = app.get_db_path(db_config)
        self.assertEqual(return_val.name, "daterbeys")

    def test_get_db_path_dot(self):
        db_config = "."
        return_val = app.get_db_path(db_config)
        self.assertEqual(return_val.name, "bplog.db")

    def test_get_db_path_none(self):
        clean_files("config.ini")
        db_config = None
        return_val = app.get_db_path(db_config)
        self.assertEqual(return_val.name, "bplog.db")
        self.assertEqual(return_val.parent.name, "bplog")

    def test_config_read_exception(self):
        db_config = None
        with patch(
            "configparser.ConfigParser.read",
            side_effect=configparser.Error("Mock exception"),
        ):
            with self.assertRaises(Exception) as context:
                app.get_db_path(db_config)
                self.assertEqual(str(context.exception), "Mock exception")


class TestDBConfig(unittest.TestCase):
    def test_update_db_config(self):
        db_path = Path("new_db_path.db")
        config_data = "[Database]\nfile_path=old_db_path.db\n"
        with patch("builtins.open", mock_open(read_data=config_data)) as mock_open_func:
            app.update_db_config(db_path)
            mock_open_func.assert_called_with("config.ini", "w", encoding="utf-8")
            self.assertGreaterEqual(mock_open_func().write.call_count, 1)
            written_content = "".join(
                [call.args[0] for call in mock_open_func().write.call_args_list]
            )
            written_config = configparser.ConfigParser()
            written_config.read_string(written_content)
            self.assertEqual(written_config["Database"]["file_path"], str(db_path))

    def test_update_db_config_raise(self):
        with patch(
            "configparser.ConfigParser.read",
            side_effect=configparser.Error("Mock exception"),
        ):
            with self.assertRaises(Exception) as context:
                db_path = "moo"
                app.update_db_config(db_path)
                self.assertEqual(str(context.exception), "Mock exception")

    def test_update_db_config_return(self):
        db_path = "moo"
        mock_config = configparser.ConfigParser()
        with patch.dict(mock_config, {"Database": {"file_path": "foo"}}, clear=True):
            with patch("configparser.ConfigParser.read", return_value=True):
                with patch("builtins.open", new_callable=mock_open) as mock_file:
                    app.update_db_config(db_path)
                    mock_file.assert_called_with("config.ini", "w", encoding="utf-8")

    def test_update_db_config_not_equal(self):
        with patch("configparser.ConfigParser.read", return_value="moo"):
            with patch("builtins.open", new_callable=mock_open) as mock_file:
                db_path = "not_moo"
                with open(
                    app.update_db_config(db_path), "w", encoding="utf-8"
                ) as tempfile:
                    mock_file.return_value = tempfile
                    app.update_db_config(db_path)


if __name__ == "__main__":
    unittest.main()  # pragma no cover
