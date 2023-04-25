"""Unittests for dependecies"""
import sqlite3
import unittest
from unittest.mock import patch

import matplotlib
from matplotlib import pyplot as plt

from src.bplog import app

matplotlib.use("agg")


def setup_test_database():
    conn = sqlite3.connect(":memory:")
    app.database_setup(conn)
    return conn


class TestPlotFunc(unittest.TestCase):
    def test_plot_blood_pressures_data(self):
        conn = setup_test_database()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO bplog (date, time, systolic, diastolic, comment) VALUES (?, ?, ?, ?, ?)",
            ("2020-03-03", "11:00", 120, 80, "Lorem Ipsum"),
        )
        app.plot_blood_pressures(conn)
        self.assertTrue(plt.fignum_exists(1))

    @patch.dict("sys.modules", {"matplotlib": None})
    def test_plot_blood_pressures_sysexit(self):
        conn = setup_test_database()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO bplog (date, time, systolic, diastolic, comment) VALUES (?, ?, ?, ?, ?)",
            ("2020-03-03", "11:00", 120, 80, "Lorem Ipsum"),
        )
        with self.assertRaises(SystemExit):
            app.plot_blood_pressures(conn)


class TestNoData(unittest.TestCase):
    def test_plot_blood_pressure(self):
        with patch("builtins.print") as mock_print:
            conn = setup_test_database()
            app.plot_blood_pressures(conn)
            mock_print.assert_called_once_with("No data to plot")
