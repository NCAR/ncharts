#
# http://docs.gunicorn.org/en/latest/settings.html
# http://docs.gunicorn.org/en/latest/configure.html#configuration-file
#

from multiprocessing import cpu_count

bind = "0.0.0.0"
workers = cpu_count() * 2 + 1
