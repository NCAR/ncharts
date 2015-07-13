#!/usr/bin/env python3
# -*- mode: C++; indent-tabs-mode: nil; c-basic-offset: 4; tab-width: 4; -*-
# vim: set shiftwidth=4 softtabstop=4 expandtab:

"""Support for reading from an NCAR EOL RAF PostgreSQL database of
real-time flight data.

2014 Copyright University Corporation for Atmospheric Research

This file is part of the "django-ncharts" package.
The license and distribution terms for this file may be found in the
file LICENSE in this package.
"""

from datetime import datetime
import pytz
import numpy as np
import logging
import sys, threading

import psycopg2

from ncharts import exceptions as nc_exc

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
_logger = logging.getLogger(__name__)   # pylint: disable=invalid-name

class RAFDatabase(object):
    """Support for reading time series from NCAR EOL RAF PostgreSQL database.

    """

    __cached_connections = {}
    __cache_lock = threading.Lock()

    @staticmethod
    def get_connection(
            database="real-time-GV",
            user="ads",
            host="eol-rt-data.fl-ext.ucar.edu",
            port=5432,
            password=None):
        """Return a psycopg2 database connection.

        The returned connection can be shared between threads.
        If the connection is kept open, then for a given
        database, user, host and port, this method
        will always return the same connection.

        Args:
            database, user, host, port password: Parameters needed
                to establish a connection to the PostgreSQL database.
        Returns:
            A psycopg2.connection

        Raises:
            psycopg2.Error
        """

        hashval = hash(database + user + host + str(port))

        with RAFDatabase.__cache_lock:
            conn = None
            if hashval in RAFDatabase.__cached_connections:
                conn = RAFDatabase.__cached_connections[hashval]
                # connection closed: nonzero if it is closed or broken.
                # Mainly just checking here if it is broken, in which
                # case, close and attempt a re-connect.
                if conn.closed:
                    try:
                        conn.rollback()
                    except psycopg2.InterfaceError as exc:
                        _logger.warn("%s rollback: %s", conn, exc)
                    try:
                        conn.close()
                    except psycopg2.InterfaceError as exc:
                        # psycopg2.InterfaceError: connection already closed
                        _logger.warn("%s close: %s", conn, exc)
                    del RAFDatabase.__cached_connections[hashval]
                    conn = None

            if not conn:
                conn = psycopg2.connect(
                    database=database, user=user,
                    host=host, port=port, password=password)
                conn.set_session(
                        isolation_level="READ COMMITTED",
                        readonly=True)
                RAFDatabase.__cached_connections[hashval] = conn

        return conn

    @staticmethod
    def close_connection(conn):
        """Close a psycopg2 database connection.

        Args:
            conn: connection to close.
        Raises:
            psycopg2.Error
        """

        with RAFDatabase.__cache_lock:
            for (hashval, cconn) in RAFDatabase.__cached_connections.items():
                if conn == cconn:
                    try:
                        conn.rollback()
                    except psycopg2.InterfaceError as exc:
                        _logger.warn("%s rollback: %s", conn, exc)
                    try:
                        conn.close()
                    except psycopg2.InterfaceError as exc:
                        # psycopg2.InterfaceError: connection already closed
                        _logger.warn("%s close: %s", conn, exc)
                    del RAFDatabase.__cached_connections[hashval]
                    break

    def __init__(
            self,
            database="real-time-GV",
            user="ads",
            host="eol-rt-data.fl-ext.ucar.edu",
            port=5432,
            password=None,
            table="raf_lrt"):
        """Construct an instance of RAF database connection.

        Args:
            database, user, host, port, password: Usual parameters
                needed to create a PostgreSQL connection.
            table: name of table in the database which contains
                the time-series data to be read.

        Raises:
            psycopg2.Error
        """

        self.conn = RAFDatabase.get_connection(
            database=database, user=user,
            host=host, port=port, password=password)
        self.database = database
        self.user = user
        self.host = host
        self.port = port
        self.password = password
        self.table = table

    def get_variables(self):
        """Fetch pertinent fields from the 'variable_list' table in
        the RAF database, such as the list of variable names, their units, and
        missing values.

        Raises:
            nc_exc.NoDataFoundException
        """

        with self.conn.cursor() as cur:
            try:
                cur.execute("\
SELECT name, units, long_name, ndims, dims, missing_value from variable_list;")
            except psycopg2.OperationalError as exc:
                # psycopg.connections are thread safe
                RAFDatabase.close_connection(self.conn)
                raise nc_exc.NoDataFoundException(
                    "No variables found: {}".format(exc))

            variables = {}
            for var in cur:
                variables[var[0]] = {
                    "units": var[1],
                    "long_name": var[2],
                    "shape": var[4]
                    }

            return variables

    def read_times(
            self,
            start_time=pytz.utc.localize(datetime.min),
            end_time=pytz.utc.localize(datetime.max)):
        """Read datetimes from the table within a range.

        Raises:
            nc_exc.NoDataFoundException
        """

        start_time = start_time.replace(tzinfo=None)
        end_time = end_time.replace(tzinfo=None)

        _logger.debug("read_times, table=%s", self.table)

        with self.conn.cursor() as cur:
            # datetimes in database are returned to python as timezone naive.
            try:
                vname = "datetime"
                cur.execute(
                    "SELECT {} FROM {} WHERE {} >= %s AND {} < %s;"
                    .format(vname, self.table, vname, vname),
                    (start_time, end_time))
            except psycopg2.OperationalError as exc:
                RAFDatabase.close_connection(self.conn)
                raise nc_exc.NoDataFoundException(
                    "read {}: {}".format(vname, exc))

            return [pytz.utc.localize(x[0]).timestamp() for x in cur]

    def get_start_time(self):
        """Read first datatime from the database table.

        Raises:
            nc_exc.NoDataFoundException
        """

        with self.conn.cursor() as cur:
            # datetimes in database are returned to python as timezone naive.
            try:
                vname = "datetime"
                cur.execute(
                    "SELECT {} FROM {} FETCH FIRST 1 ROW ONLY;"
                    .format(vname, self.table))
            except psycopg2.OperationalError as exc:
                RAFDatabase.close_connection(self.conn)
                raise nc_exc.NoDataFoundException(
                    "read {}: {}".format(vname, exc))

            start_time = cur.fetchone()[0]
            return pytz.utc.localize(start_time)

    def read_time_series(
            self,
            variables=(),
            start_time=pytz.utc.localize(datetime.min),
            end_time=pytz.utc.localize(datetime.max),
            size_limit=1000 * 1000 * 1000):
        """Read times and variables from the table within a time period.

        For each variable, its missing_value will be read from the
        variable_list table. Values read from the time series table
        which match the missing_value will be set to float('nan').

        Args:
            variables: list or tuple of variable names to read.
            start_time: starting datetime of data to be read.
            end_time: ending datetime of data to be read.
            size_limit: attempt to screen outrageous requests.

        Returns:
            A dict, compatible with that returned by netcdf.read_time_series(),
            containing the following, where series name is an empty string:
            {
                'time' : dict, by series name, of lists of
                    UTC timestamps,
                'data': dict, by series name, of dicts by variable name,
                    of numpy.ndarray containing the data for each variable,
                'dim2': dict, by series name, of a dict by variable name,
                    of values for second dimension of the data, such as height,
            }
        Raises:
            nc_exc.NoDataFoundException
        """

        total_size = 0

        start_time = start_time.replace(tzinfo=None)
        end_time = end_time.replace(tzinfo=None)

        times = self.read_times(start_time=start_time, end_time=end_time)
        _logger.debug("read_times, len=%d", len(times))

        total_size += sys.getsizeof(times)
        if total_size > size_limit:
            raise nc_exc.TooMuchDataException(
                "too many time values requested, size={0} MB".\
                format(total_size/(1000 * 1000)))

        with self.conn.cursor() as cur:
            vdata = {}
            vdim2 = {}
            for vname in variables:
                # _logger.debug("vname=%s",vname)

                try:
                    cur.execute(
                        "SELECT dims, missing_value from variable_list where name=%s;",
                        (vname,))
                except psycopg2.OperationalError as exc:
                    RAFDatabase.close_connection(self.conn)
                    raise nc_exc.NoDataFoundException(
                        "read variable_list: {}".format(exc))

                vinfo = cur.fetchall()
                # _logger.debug("vinfo=%s",vinfo)
                dims = vinfo[0][0]
                dims[0] = len(times)
                missval = vinfo[0][1]

                if len(dims) > 1:
                    # In initial CSET data, dims for CUHSAS_RWOOU in variable_list was [1,99]
                    # Seems that the 99 should have been 100, which is what is returned
                    # by this:
                    try:
                        cur.execute("\
SELECT array_upper({},1) FROM {} FETCH FIRST 1 ROW ONLY;\
".format(vname, self.table))
                    except psycopg2.OperationalError as exc:
                        RAFDatabase.close_connection(self.conn)
                        raise nc_exc.NoDataFoundException(
                            "read dimension of {}: {}".format(vname, exc))

                    dimsx = cur.fetchall()[0]
                    dims[1] = dimsx[0]
                    _logger.debug("vname=%s, dims=%s, dimsx=%s", vname, dims, dimsx)

                try:
                    cur.execute("\
SELECT {} FROM {} WHERE datetime >= %s AND datetime < %s;\
".format(vname, self.table), (start_time, end_time))
                except psycopg2.OperationalError as exc:
                    RAFDatabase.close_connection(self.conn)
                    raise nc_exc.NoDataFoundException(
                        "read {}: {}".format(vname, exc))

                cdata = np.ma.masked_values(np.ndarray(
                    shape=dims, buffer=np.array(
                        [v for v in cur], dtype=float)), value=missval)

                if isinstance(cdata, np.ma.core.MaskedArray):
                    # _logger.debug("is MaskedArray")
                    cdata = cdata.filled(fill_value=float('nan'))

                total_size += sys.getsizeof(cdata)
                if total_size > size_limit:
                    raise nc_exc.TooMuchDataException(
                        "too many values requested, size={0} MB".\
                        format(total_size/(1000 * 1000)))
                vdata[vname] = cdata
                if len(dims) > 1:
                    vdim2[vname] = {
                        "data": [i for i in range(dims[1])],
                        "name": "bin",
                        "units": ""
                        }

            return {
                "time": {"": times},
                "data": {"": vdata},
                "dim2": {"": vdim2},
            }

def test_func():
    """ """
    db = RAFDatabase(
        database="real-time-GV", user="ads",
        host="eol-rt-data.fl-ext.ucar.edu",
        port=5432,
        table="raf_lrt")

    variables = db.get_variables()
    time0 = db.get_start_time()
    _logger.debug("time0=%s", time0)

    # times = db.read_times()
    # _logger.debug("all times=%s",times)

    t1 = pytz.utc.localize(datetime(2015, 6, 29, 15, 10, 0))
    t2 = pytz.utc.localize(datetime(2015, 6, 29, 15, 11, 0))

    times = db.read_times(start_time=t1, end_time=t2)
    _logger.debug("times=%s", times)

    data = db.read_time_series(("TASX",), start_time=t1, end_time=t2)
    _logger.debug("data=%s", data)
    data = db.read_time_series(("CUHSAS_RWOOU",), start_time=t1, end_time=t2)
    _logger.debug("data=%s", data)

    RAFDatabase.close_connection(db)

if __name__ == '__main__':
    test_func()
