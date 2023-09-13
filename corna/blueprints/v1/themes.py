"""Theme management endpoints."""

import logging

import flask


themes = flask.Blueprint("themes", __name__)

logger = logging.getLogger(__name__)
