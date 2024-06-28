"""Managing Roles."""

from http import HTTPStatus
from typing import Dict

import flask
from flask_apispec import doc, marshal_with, use_kwargs
from flask_sqlalchemy_session import current_session as session
from marshmallow import Schema, fields

from corna.controls import roles_control as control
from corna.enums import SessionNames
from corna.utils import errors, secure, utils

roles = flask.Blueprint("roles", __name__)


@roles.after_request
def sec_headers(response: flask.wrappers.Response) -> flask.wrappers.Response:
    """Add security headers to every response.

    :param flask.Response response: a flask response object
    :returns: a flask response object with added security headers
    :rtype: flask.Response
    """
    headers: Dict[str, str] = secure.secure_headers(flask.request)
    response.headers.update(headers)
    return response


class CreateUpdateRoleSend(Schema):
    """Schema for creating or updating a role."""

    domain_name = fields.String(
        required=True,
        metadata={
            "description": "Domain Name of the Corna the role is created for.",
        })

    name = fields.String(
        required=True,
        metadata={
            "description": "The name of the role",
        })

    permissions = fields.List(
        fields.String(),
        required=True,
        metadata={
            "description": "The list of permissions for the role. For no "
            "permissions, leave list empty.",
        })

    class Meta:  # pylint: disable=missing-class-docstring
        strict = True


@roles.route("/roles", methods=["POST"])
@use_kwargs(CreateUpdateRoleSend())
@doc(
    tags=["Roles"],
    decription="Create a new role",
    responses={
        HTTPStatus.BAD_REQUEST: {
            "description": "If Corna does not exist or role is a duplicate",
        },
        HTTPStatus.UNAUTHORIZED: {
            "description": "If user is not authorized to create a role",
        },
        HTTPStatus.CREATED: {
            "description": " If role successfully created",
        },
    }
)
def create_role(**data):
    """Create a new role."""
    cookie = flask.request.cookies.get(SessionNames.SESSION.value)
    try:
        control.new(session, cookie, **data)
    except (control.DuplicateRoleError, errors.CornaNotFoundError) as error:
        return utils.respond_json_error(str(error), HTTPStatus.BAD_REQUEST)
    except errors.UnauthorizedActionError as error:
        return utils.respond_json_error(str(error), HTTPStatus.UNAUTHORIZED)

    session.commit()
    return "", HTTPStatus.CREATED


@roles.route("/roles", methods=["PUT"])
@use_kwargs(CreateUpdateRoleSend())
@doc(
    tags=["Roles"],
    decription="Update role permissions",
    responses={
        HTTPStatus.BAD_REQUEST: {
            "description": "If role does not exist",
        },
        HTTPStatus.UNAUTHORIZED: {
            "description": "If user is not authorized to update a role",
        },
        HTTPStatus.NO_CONTENT: {
            "description": "If role successfully updated",
        },
    },
)
def update_role(**data):
    """Update a given role."""
    cookie = flask.request.cookies.get(SessionNames.SESSION.value)
    try:
        control.update(session, cookie, **data)
    except control.NoneExistingRoleError as error:
        return utils.respond_json_error(str(error), HTTPStatus.BAD_REQUEST)
    except errors.UnauthorizedActionError as error:
        return utils.respond_json_error(str(error), HTTPStatus.UNAUTHORIZED)

    session.commit()
    return "", HTTPStatus.NO_CONTENT


class DeleteRoleSend(Schema):
    """Schema for deleting a role."""

    domain_name = fields.String(
        required=True,
        metadata={
            "description": "Domain name that role was originally created for.",
        })

    name = fields.String(
        required=True,
        metadata={
            "description": "Name of the role to delete",
        })

    class Meta:  # pylint: disable=missing-class-docstring
        strict = True


@roles.route("/roles", methods=["DELETE"])
@use_kwargs(DeleteRoleSend())
@doc(
    tags=["Roles"],
    decription="Delete role",
    responses={
        HTTPStatus.NO_CONTENT: {
            "description": "If role successfully deleted",
        },
        HTTPStatus.UNAUTHORIZED: {
            "description": "If user is not authorized to delete a role",
        },
    },
)
def delete_role(**data):
    """Delete a given role."""
    cookie = flask.request.cookies.get(SessionNames.SESSION.value)
    try:
        control.delete(session, cookie, **data)
    except errors.UnauthorizedActionError as error:
        return utils.respond_json_error(str(error), HTTPStatus.UNAUTHORIZED)
    session.commit()
    return "", HTTPStatus.NO_CONTENT


class AddRemovePermToRoleSend(Schema):
    """Add or remove a permission to/from a role."""

    domain_name = fields.String(
        required=True,
        metadata={
            "description": "Domain name of Corna",
        })

    name = fields.String(
        required=True,
        metadata={
            "description": "Name of the role",
        })

    permission = fields.String(
        required=True,
        metadata={
            "description": "Permission to add/remove.",
        })


@roles.route("/roles/permissions/add", methods=["PUT"])
@use_kwargs(AddRemovePermToRoleSend())
@doc(
    tags=["Roles"],
    description="Add permission to role (does nothing if role already has "
                "permission).",
    responses={
        HTTPStatus.BAD_REQUEST: {
            "description": "If role does not exist",
        },
        HTTPStatus.UNAUTHORIZED: {
            "description": "If user is not authorized to add to role",
        },
        HTTPStatus.NO_CONTENT: {
            "description": "If permission successfully added",
        },
    },
)
def add_to_role(**data):
    """Add permission to role."""
    cookie = flask.request.cookies.get(SessionNames.SESSION.value)
    try:
        control.add(session, cookie, **data)
    except control.NoneExistingRoleError as error:
        return utils.respond_json_error(str(error), HTTPStatus.BAD_REQUEST)
    except errors.UnauthorizedActionError as error:
        return utils.respond_json_error(str(error), HTTPStatus.UNAUTHORIZED)

    session.commit()
    return "", HTTPStatus.NO_CONTENT


@roles.route("/roles/permissions/remove", methods=["PUT"])
@use_kwargs(AddRemovePermToRoleSend())
@doc(
    tags=["Roles"],
    description="Remove permission from role (does nothing if role already "
                "has permission).",
    responses={
        HTTPStatus.BAD_REQUEST: {
            "description": "If role does not exist",
        },
        HTTPStatus.UNAUTHORIZED: {
            "description": "If user is not authorized to add to role",
        },
        HTTPStatus.NO_CONTENT: {
            "description": "If permission successfully removed",
        },
    },
)
def remove_from_role(**data):
    """Remove a permission from a role."""
    cookie = flask.request.cookies.get(SessionNames.SESSION.value)
    try:
        control.remove(session, cookie, **data)
    except control.NoneExistingRoleError as error:
        return utils.respond_json_error(str(error), HTTPStatus.BAD_REQUEST)
    except errors.UnauthorizedActionError as error:
        return utils.respond_json_error(str(error), HTTPStatus.UNAUTHORIZED)

    session.commit()
    return "", HTTPStatus.NO_CONTENT


class GiveTakeRoleSend(Schema):
    """Give or take a role from a user."""

    domain_name = fields.String(
        required=True,
        metadata={
            "description": "Domain name of Corna",
        })

    name = fields.String(
        required=True,
        metadata={
            "description": "Name of role",
        })

    username = fields.String(
        required=True,
        metadata={
            "description": "Username of user",
        })


@roles.route("/roles/give", methods=["POST"])
@use_kwargs(GiveTakeRoleSend())
@doc(
    tags=["Roles"],
    decription="Give user a role",
    responses={
        HTTPStatus.BAD_REQUEST: {
            "description": "If role or user does not exist",
        },
        HTTPStatus.UNAUTHORIZED: {
            "description": "If user is not authorized to give a role",
        },
        HTTPStatus.CREATED: {
            "description": "If role successfully given to user",
        },
    },
)
def give_role(**data):
    """Give user a role."""
    cookie = flask.request.cookies.get(SessionNames.SESSION.value)
    try:
        control.give(session, cookie, **data)
    except (
        control.NoneExistingRoleError,
        errors.NoneExistingUserError,
    ) as error:
        return utils.respond_json_error(str(error), HTTPStatus.BAD_REQUEST)
    except errors.UnauthorizedActionError as error:
        return utils.respond_json_error(str(error), HTTPStatus.UNAUTHORIZED)

    session.commit()
    return "", HTTPStatus.CREATED


@roles.route("/roles/take", methods=["POST"])
@use_kwargs(GiveTakeRoleSend())
@doc(
    tags=["Roles"],
    decription="Remove role from user",
    responses={
        HTTPStatus.UNAUTHORIZED: {
            "description": "If user is not authorized to take a role",
        },
        HTTPStatus.CREATED: {
            "description": "If role successfully taken to user",
        },
    },
)
def take_role(**data):
    """Remove role from a user."""
    cookie = flask.request.cookies.get(SessionNames.SESSION.value)
    try:
        control.take(session, cookie, **data)
    except errors.UnauthorizedActionError as error:
        return utils.respond_json_error(str(error), HTTPStatus.UNAUTHORIZED)

    session.commit()
    return "", HTTPStatus.CREATED


class PermissionsListReturn(Schema):
    """Return list of permissions associated with a role."""

    corna = fields.String(
        metadata={
            "description": "Domain name of the Corna",
        })

    name = fields.String(
        metadata={
            "description": "Name of the role",
        })

    permissions = fields.List(
        fields.String(),
        metadata={
            "description": "The list of permissions the role has",
        })


@roles.route("/roles/<domain_name>/<role_name>/permissions", methods=["GET"])
@marshal_with(PermissionsListReturn(), code=200)
@doc(
    tags=["Roles"],
    description="The list of permissions a given role has",
    responses={
        HTTPStatus.BAD_REQUEST: {
            "description": "If role does not exist",
        },
    },
)
def perm_list(domain_name, role_name):
    """List of permissions associated with a role"""
    try:
        perm_list_ = control.permissions_list(
            session=session,
            domain_name=domain_name,
            name=role_name,
        )
    except control.NoneExistingRoleError as error:
        return utils.respond_json_error(str(error), HTTPStatus.BAD_REQUEST)

    response = {
        "corna": domain_name,
        "name": role_name,
        "permissions": perm_list_,
    }
    return response


class RoleUserListSend(Schema):
    """Get users with a given role."""

    domain_name = fields.String(
        required=True,
        metadata={
            "description": "Domain name of Corna",
        })

    name = fields.String(
        required=True,
        metadata={
            "description": "Name of the role",
        })

    class Meta:  # pylint: disable=missing-class-docstring
        strict = True


class RoleUserListReturn(Schema):
    """Return list of users."""

    corna = fields.String(
        metadata={
            "description": "Domain name of the Corna",
        })

    name = fields.String(
        metadata={
            "description": "Name of the role",
        })

    users = fields.List(
        fields.String(),
        metadata={
            "description": "List of usernames with the role",
        })


@roles.route("/roles/<domain_name>/<role_name>/users", methods=["GET"])
@marshal_with(RoleUserListReturn(), code=200)
@doc(
    tags=["Roles"],
    description="List of users with a given role",
)
def user_list(domain_name, role_name):
    """Get list of users with a given role."""
    _user_list = control.user_list(
        session=session,
        domain_name=domain_name,
        name=role_name,
    )

    response = {
        "corna": domain_name,
        "name": role_name,
        "users": _user_list,
    }
    return response


class CornaRoleListReturn(Schema):
    """List of roles available on a given Corna."""

    corna = fields.String(
        metadata={
            "description": "Domain name of the Corna",
        })

    roles = fields.List(
        fields.String(),
        metadata={
            "description": "List of roles created for a given Corna",
        })


@roles.route("/roles/<domain_name>")
@marshal_with(CornaRoleListReturn(), code=200)
@doc(
    tags=["Roles"],
    description="List of roles associated with a given Corna",
)
def corna_role_list(domain_name):
    """Get all roles associated with a Corna."""
    role_list = control.corna_role_list(session, domain_name)
    response = {
        "corna": domain_name,
        "roles": role_list,
    }
    return response


class UserRoleListReturn(Schema):
    """Get list of roles a user has on a Corna."""

    username = fields.String(
        metadata={
            "description": "username of user",
        })

    corna = fields.String(
        metadata={
            "description": "Corna domain name",
        })

    roles = fields.List(
        fields.String(),
        metadata={
            "description": "List of roles the user has",
        })


@roles.route("/roles/<domain_name>/<username>", methods=["GET"])
@marshal_with(UserRoleListReturn(), code=200)
@doc(
    tags=["Roles"],
    description="List of roles a user has on a given corna",
)
def user_role_list(domain_name, username):
    """Get list of roles user has on a given corna."""
    _user_role_list = control.user_role_list(session, domain_name, username)
    response = {
        "username": username,
        "corna": domain_name,
        "roles": _user_role_list,
    }
    return response


class UserPermissionsListReturn(Schema):
    """List of users with a given permission."""

    corna = fields.String(
        metadata={
            "description": "Corna domain name",
        })

    permission = fields.String(
        metadata={
            "description": "The permission being searched for",
        })

    users = fields.List(
        fields.String(),
        metadata={
            "description": "List of users with permission",
        })


@roles.route("/roles/<domain_name>/users/<perm>", methods=["GET"])
@marshal_with(UserPermissionsListReturn(), code=200)
@doc(
    tags=["Roles"],
    description="List users with a given permission",
)
def user_perms_list(domain_name, perm):
    """List of users with a given permission."""
    _user_perms_list = control.user_perm_list(session, domain_name, perm)
    res = {
        "corna": domain_name,
        "permission": perm,
        "users": _user_perms_list,
    }
    return res
