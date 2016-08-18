# -*- mode: C++; indent-tabs-mode: nil; c-basic-offset: 4; tab-width: 4; -*-
# vim: set shiftwidth=4 softtabstop=4 expandtab:

"""Exceptions for ncharts django web app.

2014 Copyright University Corporation for Atmospheric Research

This file is part of the "django-ncharts" package.
The license and distribution terms for this file may be found in the
file LICENSE in this package.
"""

class TooMuchDataException(Exception):
    """Exception subclass if an excessive amount of data is requested.
    """
    def __init__(self, msg):
        super().__init__(msg)
        # self.msg = msg
    # def __str__(self):
    #     return repr(self.msg)

class NoDataException(Exception):
    """Exception subclass if no data is requested.
    """
    def __init__(self, msg):
        super().__init__(msg)
        # self.msg = msg
    # def __str__(self):
    #     return repr(self.msg)

class NoDataFoundException(Exception):
    """Exception subclass if no data is found, such as
    database connection is bad or no files found.
    """
    def __init__(self, msg):
        super().__init__(msg)
        # self.msg = msg
    # def __str__(self):
    #     return repr(self.msg)
