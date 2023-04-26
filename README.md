# bplog cli

[![GitHub version](https://img.shields.io/badge/version-v0.0.1-blue.svg)](https://github.com/narfel/bplog/blob/main/README.md)
[![License](https://img.shields.io/github/license/narfel/bplog)](https://github.com/narfel/bplog/blob/main/LICENSE)

Simple data logger to log blood pressure measurements from the terminal

## Description

> Quickly store blood pressure values from the terminal. Values are stored in a sqlite3 database and can be listed on the terminal, exported to csv or plotted with matplotlib if it is installed.

## Installation

Open a terminal and type

```sh
~$ git clone https://github.com/narfel/bplog.git
~$ cd bplog
~$ pip install bplog .
```

## How to use

Positional arguments

```
123:45             Measurement separated by a colon (e.g. 120:80)
```

Optional arguments

```

-c COMMENT      Add a comment to the measurement
-d DATE         Specify the date "YYYY-MM-DD" (default: today)
-t TIME         Specify the time "HH:MM" (default: current time)
-rm             Remove measurement by date/time
-rl             Remove the last measurement added
-l              List all records on the terminal (using prettytable if installed)
-csv            Export database to csv
-config CONFIG  Path to configuration file
-reset_config   Reset the config path
-h, --help              Show help
```

## Examples

```
Create a database on the first run, shows graph or list subsequently
~$ bplog

Add the values 120:80 as a record with the comment "after workout"
~$ bplog 120:80 -c "after workout"

Add the same values as a record with a specified time and date
~$ bplog 120:80 -d 2023-04-23 -t 00:00

Create a new database at the current directory
~$ bplog -config .
```

## Dependencies

None by default, but optionally:

* [**prettytable>=3.7.0**](https://pypi) (to prettify listing on the terminal)
* [**matplotlib>=3.7.1**](https://pypi) (for plotting a graph of the measurements)

## License

Copyright (c) 2023 Narfel.

Usage is provided under the MIT License. See [LICENSE](https://github.com/.../blob/master/LICENSE) for the full details.
