#!/usr/bin/env python
"""Conra flask service.

A REST API underlying the Corna social network.
"""

import os
from logging.config import dictConfig

from corna.app import create_app
from corna.db import session_maker


if __name__ == "__main__":
    dictConfig({
        'version': 1,  # mandatory
        'disable_existing_loggers': False,

        'loggers': {},

        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'standard',
                'level': 'INFO',
            },
        },

        'formatters': {
            'standard': {
                'format':
                    '[%(asctime)s] %(levelname)-8s: %(name)s: %(message)s'
            },
        },

        'root': {
            'level': 'DEBUG',  # actual level controlled by handlers
            'handlers': ['console'],
        },
    })

    # pylint: disable=invalid-name
    debug_val = os.environ.get("DEBUG_VALUE", 1)
    session_class = session_maker(statement_timeout_secs=300)
    app = create_app(session_class)
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("CORNA_PORT", 8080)),
        debug=bool(int(debug_val)))
