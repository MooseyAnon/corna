"""Manage Auth"""
import logging
from typing import Optional

from sqlalchemy.exc import IntegrityError
from werkzeug.local import LocalProxy

from corna.db import models
from corna.enums import InviteRequestStatus
from corna.middleware import alchemy
from corna.utils import encodings, future, get_utc_now, secure, utils
from corna.utils.errors import (
    IncorrectPasswordError, NoneExistingUserError, UserExistsError)

logger = logging.getLogger(__name__)


class InviteCreationError(Exception):
    """Raised when an invite could not be created."""


class InvalidInviteError(Exception):
    """Raised when an invite token cannot be redeemed."""


class InviteRequestExistsError(Exception):
    """Raised when an email already has a pending invite request."""


def username_exists(session: LocalProxy, username: str) -> bool:
    """Check if username is taken.

    :param sqlalchemy.Session session: a db session
    :param str username: username to search for
    :returns: True if the username is already taken, else False
    :rtype: bool
    """
    return utils.exists_(session, models.UserTable.username, username)


def email_exists(session: LocalProxy, email: str) -> bool:
    """Check if email is already taken.

    :param sqlalchemy.Session session: a db session
    :param str email: email to search for
    :returns: True if the email is already taken, else False
    :rtype: bool
    """
    return utils.exists_(session, models.EmailTable.email_address, email)


def session_exists(session, user_uuid):
    """Check a user session exists.

    :param sqlalchemy.Session session: a db session
    :param str user_uuid: user uuid to search for
    :returns: True if the user already has a session
    :rtype: bool
    """
    return utils.exists_(session, models.SessionTable.user_uuid, user_uuid)


def assign_avatar(session: LocalProxy, avatar_slug: str) -> str:
    """Assign user avatar.

    :param LocalProxy session: connection to DB
    :param str avatar_slug: the slug of the image
    :returns: avatar UUID
    :rtype: str
    """
    avatar: models.Media = alchemy.media_from_slug(session, avatar_slug)
    if avatar.orphaned:
        avatar.orphaned = False

    avatar_uuid: str = avatar.uuid
    return avatar_uuid


def validate_invite(session: LocalProxy, token: str) -> models.InviteTable:
    """Validate user registration token.

    Note: this should run inside a transaction as we lock the relevant rows
    to prevent race conditions.

    :param LocalProxy session: db connection
    :param str token: the invite token
    :returns: the invite entry in the db
    :rtype: InviteTable
    :raises InvalidInviteError: if token is invalid
    """

    try:
        token_hash: str = secure.hash_invite_token(token)
    except ValueError as error:
        raise InvalidInviteError(
            "Invite token is invalid or expired.") from error

    # we dont actually save the raw token string (it only gets shown once on
    # the out path) so we need to search using the token hash - which we do
    # have
    invite: Optional[models.InviteTable] = (
        session
        .query(models.InviteTable)
        .filter(models.InviteTable.token_hash == token_hash)
        .with_for_update()
        .one_or_none()
    )

    now = get_utc_now()
    if (
        invite is None
        or invite.redeemed_at is not None
        or invite.revoked_at is not None
        or invite.expires_at <= now
    ):
        raise InvalidInviteError("Invite token is invalid or expired.")

    return invite


@utils.transactional
def register_user(
    session: LocalProxy,
    # the transactional decorator expects the first arg to be a named session
    # arg. This is a safety measure to make sure that session is always passed
    # in first for this function.
    *,
    email: str,
    password: str,
    username: str,
    token: str,
    avatar: Optional[str] = None
) -> None:
    """Register a new user.

    :param sqlalchemy.Session session: session object
    :param str email: user email address
    :param str password: user password
    :param str username: username
    :param str token: single-use invite token
    :param Optional[str] avatar: the UUID of the avatar
    :raises UserExistsError: if user details are already in use
    :raises InvalidInviteError: if the invite token cannot be redeemed
    :raises InviteCreationError: if the user cannot be created
    """
    # check if either username or email are taken
    if email_exists(session, email) or username_exists(session, username):
        raise UserExistsError("Username or email are already in use.")

    invite = validate_invite(session, token)

    user_uuid = utils.get_uuid()
    avatar_uuid: Optional[models.Media] = (
        assign_avatar(session, avatar)
        if avatar else None
    )

    session.add(
        models.EmailTable(
            email_address=email,
            password=password,
        )
    )

    session.add(
        models.UserTable(
            uuid=user_uuid,
            email_address=email,
            username=username,
            date_created=get_utc_now(),
            invited_by_user_id=invite.created_by_user_id,
            is_system_account=False,
            avatar=avatar_uuid,
        )
    )

    # There is no orm relationships defined between users and invites, this is
    # a raw FK relationship. This means sqlalchemy has no way of knowing the
    # ordering of how to create these entries. It may decided to do the update
    # to the invite column below before creating the user, which leads to an
    # integrity error. Flushing does not end/complete the transaction, rather
    # it simply send the pending SQL (up till the flush) to the DB without
    # committing. We also can catch any errors before committing. Once we flush,
    # the ORM knows about the user uuid and can successfully attach the FK to
    # the invite table.
    try:
        session.flush()
    except IntegrityError as error:
        raise InviteCreationError(
            "Failed to create user"
        ) from error

    invite.redeemed_by_user_id = user_uuid
    invite.redeemed_at = get_utc_now()
    logger.info("successfully registered a new user.")


def login_user(session: LocalProxy, email: str, password: str) -> str:
    """Login a user.

    :param sqlalchemy.Session session: session object
    :param str email: user email address
    :param str password: user password
    :raises NoneExistingUserError: if user details do not exist
    :raises IncorrectPasswordError: if password is wrong
    """
    user_account: Optional[models.EmailTable] = (
        session
        .query(models.EmailTable)
        .get(email)
    )
    if user_account is None:
        raise NoneExistingUserError("User does not exist")

    if not user_account.is_password(password):
        raise IncorrectPasswordError("Wrong password")

    user: models.UserTable = (
        session
        .query(models.UserTable)
        .filter(models.UserTable.email_address == email)
        .one()
    )

    # There are situations where the client has deleted the cookie but it is
    # still present in the database. In order to avoid errors we need to ensure
    # the we remove any uncleared sessions. This is due to our constraint that
    # each user can only have one on-going session at a time.
    if session_exists(session, user.uuid):
        delete_prexisting_session(session, user.uuid)

    cookie: str = secure.generate_unique_token(
        session, models.SessionTable.cookie_id)
    session_id: str = secure.generate_unique_token(
        session, models.SessionTable.session_id)
    session.add(
        models.SessionTable(
            session_id=session_id,
            cookie_id=cookie,
            user_uuid=user.uuid,
        )
    )
    logger.info("successfully logged in user and created session")

    # We want to sign the cookie after its been saved into the DB.
    # The reason for this is because there are weird issues with
    # type conversions in postgres and it seems to want to save
    # the HMAC has hex rather than unicode. This is an issues as
    # it does the lookup comparisons without converting the incoming
    # hash to hex. this leads to guaranteed failures as unicode values
    # will never match the hex ones saved inside the db.
    return encodings.from_bytes(secure.sign(cookie))


def delete_user_session(session: LocalProxy, signed_cookie: str) -> None:
    """Delete user session.

    :param sqlalchemy.Session session: session object
    :param str signed_cookie: user cookie
    """
    cookie_id: str = secure.decoded_message(signed_cookie)
    (
        session
        .query(models.SessionTable)
        .filter(models.SessionTable.cookie_id == cookie_id)
        .delete(synchronize_session=False)
    )

    logger.info("successfully deleted session")


def delete_prexisting_session(session: LocalProxy, user_uuid: str) -> None:
    """Delete session via user UUID.

    :param LocalProxy session: db session
    :param str user_uuid: The user uuid to delete
    """
    (
        session
        .query(models.SessionTable)
        .filter(models.SessionTable.user_uuid == user_uuid)
        .delete(synchronize_session=False)
    )

    logger.info("successfully deleted pre-existing session")


def create_invite(
    session: LocalProxy,
    cookie: str,
) -> str:
    """Create a user requested invite token.

    :param sqlalchemy.Session session: session object
    :param str cookie: session cookie of the user creating the invite
    :returns: plaintext invite token
    :rtype: str
    """
    creator: models.UserTable = utils.current_user(session, cookie)
    return create_invite_for_user(session, creator.uuid)


def create_invite_for_user(
    session: LocalProxy,
    creator_uuid: str,
) -> str:
    """Create and persist a single-use invite.

    The plaintext token is returned to the caller but is never stored in the
    database. Only a deterministic hash of the token is persisted.

    The caller owns the surrounding transaction and is responsible for
    committing or rolling it back.

    Note: this exists as a separate function to allow system accounts to bypass
    needing to login with a password when creating tokens. System accounts will
    create tokens when `"Request invite"` is used on the client.

    :param sqlalchemy.Session session: session object
    :param str creator_uuid: UUID of user creating the invite
    :returns: plaintext invite token
    :rtype: str
    :raises InviteCreationError: if the invite cannot be persisted
    """
    token: str = secure.generate_invite_token()
    token_hash: str = secure.hash_invite_token(token)

    invite = models.InviteTable(
        uuid=utils.get_uuid(),
        token_hash=token_hash,
        created_by_user_id=creator_uuid,
        date_created=get_utc_now(),
        expires_at=future(days=3),
    )

    session.add(invite)

    try:
        # Flush rather than commit so that the caller retains ownership of
        # the transaction while database constraint errors surface here.
        session.flush()
    except IntegrityError as error:
        raise InviteCreationError(
            "Failed to create invite"
        ) from error

    logger.info(
        "successfully created invite",
        extra={
            "invite_id": str(invite.uuid),
            "created_by_user_id": str(creator_uuid),
        },
    )

    return token


@utils.transactional
def create_invite_request(
    session: LocalProxy,
    *,
    email_address: str,
    referral_source: str | None = None,
) -> models.InviteRequestTable:
    """Create a pending request for a Corna invite."""
    email_address = email_address.strip().lower()
    referral_source = (
        referral_source.strip()
        if referral_source and referral_source.strip()
        else None
    )

    if email_exists(session, email_address):
        raise InviteRequestExistsError("Email already in use.")

    existing_request = (
        session
        .query(models.InviteRequestTable)
        .filter(
            models.InviteRequestTable.email_address == email_address,
            # if the email has already been sent an invite or is pending
            # we can ignore it as it will be processed at some point
            models.InviteRequestTable.status.in_({
                InviteRequestStatus.PENDING,
                InviteRequestStatus.INVITED,
            }),
        )
        .one_or_none()
    )

    if existing_request is not None:
        raise InviteRequestExistsError(
            "A pending invite request already exists for this email address."
        )

    invite_request = models.InviteRequestTable(
        uuid=utils.get_uuid(),
        email_address=email_address,
        referral_source=referral_source,
        date_created=get_utc_now(),
        status=models.InviteRequestStatus.PENDING,
    )

    session.add(invite_request)
    session.flush()

    return invite_request
