"""Frontend endpoints"""
from http import HTTPStatus

import flask
from flask_sqlalchemy_session import current_session as session

from sqlalchemy.orm import load_only

from corna.db import models
from corna.controls import post_control
from corna.controls import frontend_control as control
from corna.utils import secure, utils
from corna.controls.post_control import NoneExistinCornaError

frontend = flask.Blueprint("frontend", __name__,
    template_folder=(utils.CORNA_ROOT / "themes"),
    static_folder=(utils.CORNA_ROOT / "themes"),
    static_url_path="/api/v1/frontend/static")

print(frontend.static_url_path, "***********")
@frontend.after_request
def cors_headers(response):
    """Add cors headers to every request."""
    headers = secure.cors_headers()
    response.headers.update(headers)
    return response


@frontend.route("/")
def index():
    print("index called")
    return flask.send_file("../corna-frontend/index.html")


@frontend.route("/login")
def form_page():
    return flask.render_template("login-form.html")


@frontend.route("/post")
def post_page():
    return flask.render_template("post-form.html")

@frontend.route("/frontend/static/<path:path>")
def custom_static(path):
    print("************************")
    print("GOT CUSTOM STATIC -------->", path)
    print("************************")
    return flask.send_from_directory((utils.CORNA_ROOT / "themes"), path)


@frontend.route("/frontend/<domain_name>/post/<type>/static/<path:path>")
def post_page_static(domain_name, type, path):
    print("************************")
    print("GOT CUSTOM PAGE STATIC -------->", path)
    print("************************")
    return flask.send_from_directory((utils.CORNA_ROOT / "themes"), path)


@frontend.route("/frontend/<domain_name>")
def get_corna(domain_name):
    print("************************")
    print("GOT DOMAIN -------->", domain_name)
    print("************************")
    # temp solution
    # https://stackoverflow.com/questions/40391566/render-jinja-after-jquery-ajax-request-to-flask

    corna = (
        session
        .query(models.CornaTable)
        .options(load_only(models.CornaTable.title))
        .filter(models.CornaTable.domain_name == domain_name)
        .one_or_none()
    )
    title = corna.title
    return flask.render_template(
        "window-64/index.html",
        type="postlist",
        title=title,
        simplifiedPostList=control.simplified_post_list(corna, domain_name))


@frontend.route("/frontend/<domain_name>/post/<type_>/<uuid>")
def get_image(domain_name, type_, uuid):

    # try:
    #     path = post_control.get_image(session, domain_name, uuid)

    # except PostDoesNotExist as e:
    #     utils.respond_json_error(str(e), HTTPStatus.BAD_REQUEST)

    # return flask.send_file(path)
    print("got a single request post ----------->")
    print(type_)
    if type_ == "text":
        obj = session.query(models.PostTable).get(uuid)
        post = obj.mapper.text

    return flask.render_template(
        "window-64/index.html",
        type="expandedPost", post=post)
