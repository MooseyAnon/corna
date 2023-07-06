import flask
from flask_apispec import doc, marshal_with, use_kwargs
from marshmallow import Schema, fields


dummy = flask.Blueprint("dummy", __name__)


@dummy.route("/dummy")
def dummy_():
    return {"resp": "hello world"}
