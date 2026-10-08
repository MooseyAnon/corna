"""Health endpoints for the Corna API."""

from http import HTTPStatus

import flask
from flask_apispec import doc

from corna.controls import health_control
from corna.oss.flask_sqlalchemy_session import current_session as session

health = flask.Blueprint("health", __name__)


@health.route("/ping", methods=["GET"])
@doc(
    tags=["Health"],
    description="Check whether the Corna API process is alive.",
    responses={
        HTTPStatus.OK: {
            "description": "API is alive.",
        },
    },
)
def ping():
    """Return a shallow liveness check."""
    return {"status": "ok"}, HTTPStatus.OK


@health.route("/healthz", methods=["GET"])
@doc(
    tags=["Health"],
    description="Check Corna API dependencies.",
    responses={
        HTTPStatus.OK: {
            "description": "All required dependencies are healthy.",
        },
        HTTPStatus.SERVICE_UNAVAILABLE: {
            "description": "One or more required dependencies are unhealthy.",
        },
    },
)
def healthz():
    """Return the application dependency health status."""
    response = health_control.health_check(session)

    if response["status"] == "ok":
        status_code = HTTPStatus.OK
    else:
        status_code = HTTPStatus.SERVICE_UNAVAILABLE

    return response, status_code
