"""Corna social blogging site."""

import http
import inspect
import logging
import os

import flask
from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin
from flask_apispec import FlaskApiSpec
from flask_sqlalchemy_session import flask_scoped_session

from corna.blueprints import frontend
from .blueprints.v1 import auth, corna, dummy, posts

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


def register_blueprint_with_docs(
        api_spec, module, blueprint_attr_name, **kwargs
):
    """Helper to register a blueprint and any APISpec decorated functions.

    :param FlaskApiSpec api_spec:
    :param module module: the blueprint module to register
    :param str blueprint_attr_name: the name of the blueprint
    :param kwargs: passed to `Flask.register_blueprint`
    """
    api_spec.app.register_blueprint(
        getattr(module, blueprint_attr_name), **kwargs)
    for _, func in inspect.getmembers(module, inspect.isfunction):
        if hasattr(func, '__apispec__'):
            api_spec.register(func, blueprint=blueprint_attr_name)


def create_app(session_class):
    """Create a Flask app.

    :returns: the created Flask app
    :rtype: flask.Flask
    """
    logger.info("Creating the Flask app")
    app = flask.Flask(__name__, instance_path=os.getcwd())
    app.url_map.strict_slashes = False

    # Register API documentation
    api_spec = FlaskApiSpec(app)
    api_spec.spec = APISpec(
        title="Corna APIs",
        version="1",
        plugins=(MarshmallowPlugin(),),
        info={
            "description": "APIs for interacting with Corna's backend"},
        openapi_version="2.0"
    )
    flask_scoped_session(session_class, app)
    register_blueprint_with_docs(
        api_spec, auth, "auth", url_prefix="/api/v1")
    register_blueprint_with_docs(
        api_spec, corna, "corna", url_prefix="/api/v1")
    register_blueprint_with_docs(
        api_spec, dummy, "dummy", url_prefix="/api/v1")
    register_blueprint_with_docs(api_spec, frontend, "frontend")
    register_blueprint_with_docs(
        api_spec, posts, "posts", url_prefix="/api/v1")

    # Handle argument errors
    # app.register_error_handler(
    #     http.HTTPStatus.UNPROCESSABLE_ENTITY, docs.handle_unprocessable_entity)
    logger.info("The Flask app has been created")

    return app