"""Dummy blueprint. Useful for testing."""
import flask

dummy = flask.Blueprint("dummy", __name__)


@dummy.route("/dummy")
def dummy_():
    """Random dummy endpoint."""
    return {"resp": "hello world"}
