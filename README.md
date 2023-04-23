# bplog cli

[![GitHub version](https://img.shields.io/badge/version-v0.0.1-blue.svg)](https://github.com/yilber/readme-boilerplate)
[![License](https://img.shields.io/github/license/yilber/readme-boilerplate.svg)](https://github.com/Yilber/readme-boilerplate/blob/master/LICENSE)

Simple manual data logger for blood pressure measurements in a terminal

## Background

> Simple data logger to quickly store blood pressure values from the cli. Values are stored in a sqlite3 database and can be exported to csv, listed on the terminal or plotted with matplotlib.

## Installation

Open your terminal and type in

```sh
git clone https://github.com/....git
cd bplog
pip install bplog .
or pip install --prefix=~/.local -e ."
```

## How to use

### Print help

```sh
bplog -h
```

### Positional arguments

```
bp              Measurement separated by a colon (e.g. 120:80)
```

### Optional arguments

```
-c COMMENT      Add a comment to the measurement
-d DATE         Specify the date "YYYY-MM-DD" (default: today)
-t TIME         Specify the time "HH:MM" (default: current time)
```

### Remove measurements

```
-rm             Remove measurement by date/time
-rl             Remove the last measurement added
```

### Show measurements

```
-l              List all records on the terminal (using prettytable if installed)
```

### Manage database file

```
-csv            Export database to csv
-config CONFIG  Path to configuration file
-reset_config   Reset the config path
```

## Examples

```sh
~$ bplog 120:80 -c "after workout"
~$ bplog 120:80 -t 22:00 -c "too much coffee"
~$ bplog 120:80 -d 2023-04-23 -t 00:00 -c "Hi"
```

## Dependencies

None by default, but optionally:

* [**prettytable**](https://pypi) (to format listing on the terminal)
* [**matplotlib**](https://pypi) (for plotting a graph of the measurements)

## Bugs

If you have questions, feature requests or a bug you want to report, please click [here](https://github.com/.../issues) to file an issue.

Copyright (c) 2023 Narfel.

Usage is provided under the MIT License. See [LICENSE](https://github.com/.../blob/master/LICENSE) for the full details.
