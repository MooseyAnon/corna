"""Base Schema and Parser classes to enforce Marshamallow 2 behavior."""

from marshmallow import EXCLUDE, Schema
from webargs.flaskparser import FlaskParser


class ExcludeParser(FlaskParser):
    """Flask parser to overwrite default Marshmallow schema behaviour.

    This class inherits webargs.flaskparser.FlaskParser and overrides the
    DEFAULT_UNKNOWN_BY_LOCATION class attribute. This ensures that when
    Schema.load() is called, the `unknown` keyword argument is set to `EXCLUDE`.
    This forces marshmallow 2 behavior where extra fields in the json payload
    are ignored.
    """
    DEFAULT_UNKNOWN_BY_LOCATION = {"json": EXCLUDE}


class BaseSchema(Schema):
    """Base Schema class to enforce Marshamallow 2 behavior in nested schemas.

    The unknown keyword argument in schema.load() is always set by the
    FlaskParser and therefore overrides self.unknown in any schema. However,
    the unknown value is passed to the schema’s load() call. It therefore only
    applies to the top layer when nesting is used. To control unknown at
    multiple layers within nested schema, this BaseSchema sets meta.unknown to
    EXCLUDE and therefore forces marshmallow 2 behaviour.
    """
    class Meta:  # pylint: disable=missing-class-docstring
        unknown = EXCLUDE
