# This file exists because it's not possible to set the --access-logformat
# argument to gunicorn inside a systemd service file, because it requires
# quoting, which systemd service files do not support.

import os
import traceback

_this_dir = os.path.abspath(os.path.dirname(__file__))

# This means: remote address, status line, status
access_log_format = '%(h)s "%(r)s" %(s)s'

bind = "0.0.0.0:{}".format(os.environ['CORNA_PORT'])
chdir = _this_dir
logconfig = os.path.join(_this_dir, "gunicorn.logging.ini")

worker_type = 'sync'
workers = 5

timeout = 90


def worker_abort(worker):
    """Log a traceback when a worker gets aborted (due to a timeout)."""
    stack = traceback.format_stack()
    msg = (
        f"This was the call stack at the time the worker was aborted:\n"
        f"{''.join(stack)}"
    )
    worker.log.critical(msg)
