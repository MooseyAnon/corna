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


class PreExistingCornaError(ValueError):
    """Pre-existing corna error.

    Raised when user tries to create a new corna while
    already having one.

    We currently dont allow for a single user to have
    multiple corna's.
    """


class DomainExistsError(ValueError):
    """Domain exists error.

    Raised when domain name is already in use
    by another user.
    """


class CornaOwnerError(ValueError):
    """Corna owner error.

    Raised when corna is not owned by user.
    """
