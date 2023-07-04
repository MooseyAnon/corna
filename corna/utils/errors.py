"""Shared errors across the service."""

class UserExistsError(ValueError):
    """ User exists error.

    Raised if a user tries to create an account with details
    that already exist.
    """


class NoneExistingUserError(ValueError):
    """None existing user.

    Raised if user tries to log in with unknown email address.
    """


class IncorrectPasswordError(ValueError):
    """Incorrect password error.

    Raised if user enter wrong password.
    """


class NotLoggedInError(ValueError):
    """Not logged in error.

    Raised if user is not logged in.
    """


class PreExistingBlogError(ValueError):
    """Pre-existing blog error.

    Raised when user tries to create a new blog while
    already having one.

    We currently dont allow for a single user to have
    multiple blogs.
    """


class DomainExistsError(ValueError):
    """Domain exists error.

    Raised when domain name is already in use
    by another user.
    """


class BlogOwnerError(ValueError):
    """Blog owner error.

    Raised when blog is not owned by user.
    """
