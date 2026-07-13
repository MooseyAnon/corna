"""Control code for a users Corna client experience."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import logging
import pathlib
from typing import Any, Dict, List, Literal, Optional, TypeVar

from markupsafe import Markup
from sqlalchemy.orm.scoping import scoped_session as Session

from corna import enums
from corna.db import models
from corna.middleware import alchemy, check
from corna.utils import errors, image_proc, utils

logger = logging.getLogger(__name__)

SessionT = TypeVar("SessionT", bound=Session)
ModeT = Literal["pagination", "load_more", "infinite_scroll"]


class CornaNotFoundError(ValueError):
    """No Corna exists for the given subdomain."""


class PostNotFoundError(ValueError):
    """Post not found."""


@dataclass(frozen=True)
class Post:
    """Dataclass representation of a post for templates and JSON.

    Notes:
    - ``type`` is kept as ``str`` to match template checks like
        ``post.type == "picture"``.
    - HTML fields are wrapped with ``Markup`` where present for safe rendering.

    :ivar str uuid: post uuid.
    :ivar str href: Absolute URL for the post.

    :ivar str created: timestamp as a string.
    :ivar str type: post type.
    :ivar str domain_name: the subdomain extension.
    :ivar Optional[str] title: post title
    :ivar Optional[str] created_display: formatted timestamp for templates.
    :ivar str full_href: the post url.
    :ivar Optional[Markup] text_html: the markup to be rendered on the client
        this is only applicable to text posts.
    :ivar Optional[Markup] caption_html: the markup to be rendered on the
        client, this is only applicable to video/image posts.
    :ivar list[Media] media: any media associated with the post e.g. header
        images for text posts.
    """

    uuid: str
    href: str
    created: str
    type: str
    domain_name: str
    title: Optional[str]
    full_href: str
    created_display: Optional[str] = None
    text_html: Optional[Markup] = None
    caption_html: Optional[Markup] = None
    media: List[Media] = field(default_factory=list)

    @classmethod
    def _parse_media_list(cls, post: models.PostTable) -> List[Media]:
        """Parse all media rows attached to a post.

        :param PostTable post: post row whose media should be parsed.
        :returns: parsed media payloads.
        :rtype: List[Media]
        """
        if not post.media:
            return []

        return [Media.from_model(media) for media in post.media]

    @classmethod
    def _full_post_href(cls, subdomain: str, url_extension: str) -> str:
        """Return the full href of a post.

        :param str subdomain: the corna subdomain
        :param str url_extension: the post extension
        :returns: fully resolved client ready URL for a post
        :rtype: str
        """
        return f"https://{subdomain}.mycorna.com/p/{url_extension}"

    @classmethod
    def _post_title(cls, post: models.PostTable) -> Optional[str]:
        """Get the post title if one exists.

        :param PostTable post: the post in question
        :returns: the title of the post if available else None
        :rtype: Optional[str]
        """
        title: Optional[str] = (
            post.text.title if (post.text and post.text.title) else None
        )
        return title

    @classmethod
    def _post_html_fragment(cls, post: models.PostTable) -> Optional[Markup]:
        """Encode the HTML string into valid markup.

        :param PostTable post: the parent post
        :returns: post content as markup, if present
        :rtype: Optional[Markup]
        """
        html_content: Optional[Markup] = (
            Markup(post.text.inner_html)
            if (post.text and post.text.inner_html)
            else None
        )
        return html_content

    @classmethod
    def _ordinal(cls, day: int) -> str:
        """Return the ordinal representation of a day number.

        :param int day: day of the month.
        :returns: ordinal suffixed day, e.g. ``10th``.
        :rtype: str
        """
        # 11th, 12th, and 13th are super weird and don't follow the rules of
        # the rest of the numbers in the date system. Yay English.
        #
        # This check essentially is a special check for those three numbers.
        if 11 <= day <= 13:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")

        return f"{day}{suffix}"

    @classmethod
    def _created_display(cls, created: datetime) -> str:
        """Return a human-readable timestamp for templates.

        :param datetime created: timestamp from the database.
        :returns: formatted date string.
        :rtype: str
        """
        weekday = created.strftime("%A")
        month = created.strftime("%B")
        return f"{weekday}, {cls._ordinal(created.day)} {month}"

    @classmethod
    def from_model(cls, post: models.PostTable, subdomain: str) -> Post:
        """Create a ``Post`` from a row in the database.

        :param PostTable post: a post
        :param str subdomain: the domain the post belongs to

        :returns: a parse post object
        :rtype: Post
        """
        # type stored in DB is text; keep as string for template compatibility
        post_type: str = str(post.type)

        title = cls._post_title(post)
        full_href = cls._full_post_href(subdomain, post.url_extension)

        text_html: Optional[Markup] = None
        caption_html: Optional[Markup] = None
        if post_type == enums.ContentType.TEXT.value:
            text_html = cls._post_html_fragment(post)
        else:
            caption_html = cls._post_html_fragment(post)

        return cls(
            uuid=str(post.uuid),
            href=post.url_extension,
            created=post.created.isoformat(),
            type=post_type,
            domain_name=subdomain,
            title=title,
            created_display=cls._created_display(post.created),
            full_href=full_href,
            text_html=text_html,
            caption_html=caption_html,
            media=cls._parse_media_list(post),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize post data to an dict.

        :returns: the post as a dict
        :rtype: dict
        """
        out: Dict[str, Any] = {
            "uuid": self.uuid,
            "href": self.href,
            "created": self.created,
            "type": self.type,
            "domain_name": self.domain_name,
            "title": self.title,
            "created_display": self.created_display,
            "full_href": self.full_href,
            # convert Markup to str for JSON compatibility
            "content": (
                str(self.text_html)
                if self.text_html is not None
                else None
            ),
            "caption": (
                str(self.caption_html)
                if self.caption_html is not None
                else None
            ),
            "media": [
                {
                    "href": media.href,
                    "type": media.type,
                    "width": media.width,
                    "height": media.height,
                    "aspect_ratio": media.aspect_ratio,
                }
                for media in self.media
            ],
        }
        # Remove None-only fields based on post type for cleaner output
        if self.type == enums.ContentType.TEXT.value:
            out.pop("caption", None)
        else:
            out.pop("content", None)
        return out


@dataclass(frozen=True)
class Media:
    """Dataclass representing media attached to a post.

    :ivar str href: Absolute URL for the media asset.
    :ivar str type: Media type, e.g. ``image`` or ``video``.
    :ivar Optional[int] width: Media width in pixels, if known.
    :ivar Optional[int] height: Media height in pixels, if known.
    :ivar Optional[str] aspect_ratio: Simplified aspect ratio string, if known.
    """

    href: str
    type: str
    width: Optional[int]
    height: Optional[int]
    aspect_ratio: Optional[str]

    @classmethod
    def _media_api_href(cls, url_extension: str) -> str:
        """Return full media download URL.

        :param str url_extension: the url for a media asset.
        :returns: fully resolved client ready HREF for a media asset.
        :rtype: str
        """
        return f"{utils.UNVERSIONED_API_URL}/v1/media/download/{url_extension}"

    @classmethod
    def _media_dimensions(
        cls,
        media: models.Media,
    ) -> tuple[Optional[int], Optional[int]]:
        """Return the stored dimensions for a media item.

        :param Media media: media row to inspect.
        :returns: media height and width, in that order.
        :rtype: tuple[Optional[int], Optional[int]]
        """
        if media.image:
            return media.image.height, media.image.width

        if media.video:
            return media.video.height, media.video.width

        return None, None

    @classmethod
    def _media_aspect_ratio(
        cls,
        width: Optional[int],
        height: Optional[int],
    ) -> Optional[str]:
        """Return a simplified aspect ratio for a media item.

        :param Optional[int] width: Media width in pixels.
        :param Optional[int] height: Media height in pixels.
        :returns: Simplified aspect ratio string, if it can be derived.
        :rtype: Optional[str]
        """
        if width is None or height is None:
            return None

        try:
            return image_proc.aspect_ratio(height, width)
        except ValueError:
            return None

    @classmethod
    def from_model(cls, media: models.Media) -> Media:
        """Parse a media row into a public ``Media``.

        :param Media media: media row to parse.
        :returns: parsed media payload.
        :rtype: Media
        """
        height, width = cls._media_dimensions(media)

        return Media(
            href=cls._media_api_href(media.url_extension),
            type=str(media.type),
            width=width,
            height=height,
            aspect_ratio=cls._media_aspect_ratio(width, height),
        )


@dataclass(frozen=True)
class Pagination:
    """Dataclass describing listing navigation state.

    :ivar bool has_next: Whether a subsequent page is available.
    :ivar bool has_prev: Whether a previous page is available.
    :ivar Optional[str] next_href: URL for the next page, if available.
    :ivar Optional[str] prev_href: URL for the previous page, if available.
    :ivar Optional[int] current_page: Current page number, if page-numbered.
    :ivar int page_size: Number of items represented by this listing payload.
    :ivar Optional[str] cursor: Cursor used to fetch the current slice, if any.
    :ivar Optional[str] next_cursor: Cursor for the next slice, if any.
    """

    has_next: bool
    has_prev: bool
    next_href: Optional[str]
    prev_href: Optional[str]
    current_page: Optional[int]
    page_size: int
    cursor: Optional[str]
    next_cursor: Optional[str]


@dataclass(frozen=True)
class Render:
    """Dataclass describing how the listing should be rendered.

    :ivar bool is_fragment: Whether this payload is intended for fragment
        rendering.
    :ivar Optional[str] fragment_name: Named fragment identifier,
        if applicable.
    """

    is_fragment: bool
    fragment_name: Optional[str]


@dataclass(frozen=True)
class Behaviour:
    """Dataclass describing client-side listing interaction behaviour.

    :ivar Literal["pagination", "load_more", "infinite_scroll"] mode:
        The expected listing interaction mode.
    """

    mode: Literal["pagination", "load_more", "infinite_scroll"]


@dataclass(frozen=True)
class Listing:
    """Dataclass representing the stable listing contract for templates.

    :ivar List[Post] items: Posts included in the current listing payload.
    :ivar bool has_items: Whether the listing contains any posts.
    :ivar Pagination paging: Paging metadata for the listing.
    :ivar Render render: Rendering metadata for the listing.
    :ivar Behaviour behaviour: Client interaction metadata for the listing.
    """

    items: List[Post]
    has_items: bool
    paging: Pagination
    render: Render
    behaviour: Behaviour

    @classmethod
    def from_posts(
        cls,
        posts: List[Post],
        *,
        is_fragment: bool = False,
        fragment_name: Optional[str] = None,
        mode: ModeT = "pagination",
    ) -> Listing:
        """Build a listing contract from parsed posts.

        :param List[Post] posts: Parsed posts for the listing.
        :param bool is_fragment: Whether the listing is intended as a fragment.
        :param Optional[str] fragment_name: Named fragment identifier, if any.
        :param ModeT mode: Interaction mode expected by the client.
        :returns: Stable listing payload for template rendering.
        :rtype: Listing
        """
        paging = Pagination(
            has_next=False,
            has_prev=False,
            next_href=None,
            prev_href=None,
            current_page=None,
            page_size=len(posts),
            cursor=None,
            next_cursor=None,
        )
        render = Render(
            is_fragment=is_fragment,
            fragment_name=fragment_name,
        )
        behaviour = Behaviour(mode=mode)

        return cls(
            items=posts,
            has_items=bool(posts),
            paging=paging,
            render=render,
            behaviour=behaviour,
        )


@dataclass(frozen=True)
class CornaPage:
    """Aggregate dataclass that encapsulates the assembly of a Corna page.

    :ivar Listing listing: Stable listing payload for the page.
    :ivar Optional[str] title: Page title, if one is available.
    :ivar str theme_path: Path to the theme template.
    """

    subdomain: str
    title: Optional[str]
    theme_path: str
    listing: Listing

    @classmethod
    def _current_corna(
        cls,
        session: SessionT,
        subdomain: str,
    ) -> models.CornaTable:
        """Get the details for the current corna we're working with.

        :param SessionT session: connection to the db.
        :param str subdomain: the subdomain extension.
        :returns: corna details.
        :rtype: CornaTable
        """
        return _current_corna(session, subdomain)

    @classmethod
    def _title(cls, session: SessionT, subdomain: str) -> Optional[str]:
        """Get the title for the current corna.

        :param SessionT session: connection to the db.
        :param str subdomain: the subdomain extension.
        :returns: title is the corna has one.
        :rtype: str
        """
        curr_corna = cls._current_corna(session, subdomain)
        return curr_corna.title if (curr_corna and curr_corna.title) else None

    @classmethod
    def _theme(cls, session: SessionT, subdomain: str) -> str:
        """Get the theme path for the current corna.

        :param SessionT session: connection to the db.
        :param str subdomain: the subdomain extension.
        :returns: the path to the chosen theme.
        :rtype: str
        """
        curr_corna = cls._current_corna(session, subdomain)
        theme_homepage = str(theme(session, curr_corna) / "index.html")
        return theme_homepage

    @classmethod
    def _post_list(
        cls,
        session: SessionT,
        subdomain: str,
        cookie: Optional[str] = None,
    ) -> List[Post]:
        """Get the posts for a given Corna.

        :param SessionT session: connection to the db.
        :param str subdomain: the subdomain extension.
        :param Optional[str] cookie: the current user cookie.
        :returns: post list for the corna
        :rtype: list[Post]
        :raise UnauthorizedActionError: if user is not allowed to see the
            contents of the page.
        """
        curr_corna = cls._current_corna(session, subdomain)

        if not can_read(session, subdomain, cookie):
            raise errors.UnauthorizedActionError("User not allowed to read")

        posts: List[Optional[models.PostTable]] = (
            session
            .query(models.PostTable)
            .filter(models.PostTable.corna_uuid == curr_corna.uuid)
            # We're disabling pylints (singleton-comparison) check because
            # in sqlalchemy equality checking against the boolean is actually
            # important for the generated SQL statement. Its not a python-land
            # thing.
            .filter(models.PostTable.deleted == False)  # pylint: disable=C0121
            .order_by(models.PostTable.created.desc())
            .all()
        )
        parsed_posts = [Post.from_model(post, subdomain) for post in posts]
        return parsed_posts

    @classmethod
    def load(
        cls,
        session: SessionT,
        subdomain: str,
        cookie: Optional[str] = None,
    ) -> CornaPage:
        """Load the details for a Corna.

        :param SessionT session: connection to the db.
        :param str subdomain: the subdomain extension.
        :param Optional[str] cookie: the current user cookie.
        :returns: dataclass representation of a corna page.
        :rtype: CornaPage
        """
        posts = cls._post_list(session, subdomain, cookie)
        listing = Listing.from_posts(posts)
        title = cls._title(session, subdomain)
        theme_path = cls._theme(session, subdomain)

        return cls(
            subdomain=subdomain,
            title=title,
            theme_path=theme_path,
            listing=listing,
        )


@dataclass(frozen=True)
class AboutDTO:
    """Simple data transfer object for the about page.

    :ivar str owner: the corna owner
    :ivar str theme_path: the path to the theme about page
    :ivar Optional[str] about: The text for the about page
    :ivar Optional[str] title: the corna title
    :ivar Optional[str] avatar_url: the url for the community avatar
    """
    owner: str
    theme_path: str
    about: Optional[str]
    title: Optional[str]
    avatar_url: Optional[str]


def _current_corna(session: SessionT, subdomain: str) -> models.CornaTable:
    """Get Corna details for a given subdomain.

    :param SessionT session: db session
    :param str subdomain: the Corna subdomain

    :returns: Corna information associated with the subdomain
    :rtype: model.Corna
    :raises CornaNotFoundError: if there is no corna for subdomain
    """
    corna: Optional[models.CornaTable] = (
        session
        .query(models.CornaTable)
        .filter(models.CornaTable.domain_name == subdomain)
        .one_or_none()
    )

    if not corna:
        logger.warning("No corna names %s found", subdomain)
        raise CornaNotFoundError(
            f"No Corna with the domain {subdomain} found.")

    return corna


def can_read(
    session: SessionT,
    subdomain: str,
    cookie: Optional[str] = None,
) -> bool:
    """Ensure user has read access to a Corna.

    :param SessionT session: a DB session
    :param str subdomain: the corna subdomain
    :param Optional[str] cookie: user cookie

    :returns: True if user has read access, else no
    :rtype: bool
    """
    username: Optional[str] = None
    if cookie:
        try:
            user: models.UserTable = alchemy.current_user(session, cookie)
            username = user.username

        except errors.NotLoggedInError:
            # we can just ignore this as its not a required param
            pass

    return check.can_read(session, subdomain, username=username)


def theme(session: SessionT, corna: models.CornaTable) -> pathlib.Path:
    """Return the correct single post view template file.

    Note: all themes have deterministic naming so they can be easily found
    in the file system. The naming convention is:
        - <theme-name>/index.html -> main homepage
        - <theme-name>/spv.html -> single post view template
    Themes are then allowed to an arbitrary amount of jinja fragments the
    can load in at run time for e.g. displaying errors.

    :param SessionT session: db connection
    :param CornaTable corna: details about a corna
    :returns: path to SPV for the theme
    :rtype: str
    :raises ValueError: if corna has no theme
    """
    # To avoid circular deps, we explicitly save the the theme uuid on the
    # corna table instead of creating a relationship
    theme_: Optional[models.Themes] = (
        session
        .query(models.Themes)
        .filter(models.Themes.uuid == corna.theme)
        .one_or_none()
    )
    if not theme_:
        raise ValueError("No theme found for Corna")

    # We can just return the top level path name and let the callee decide on
    # the exact page to serve. Each theme has a predictible set of page names:
    # - index -> main hompage
    # - post -> single page view
    # - about -> the about page
    #
    # All three of these sit beneth the top level name.
    parent_path = pathlib.Path(theme_.path).parent
    return parent_path


def single_post(
    session: SessionT,
    url_extension: str,
    subdomain: str,
    cookie: Optional[str] = None,
) -> tuple[Post, str]:
    """Get a single post.

    :param SessionT session: a db session
    :param str url_extension: url extension of post
    :param str subdomain: the Corna the post lives on
    :param Optional[str] cookie: user cookie

    :returns: a parsed post and post theme
    :rype: tuple[Post, str]
    :raises errors.UnauthorizedActionError: if user is not allowed to read
    :raises PostNotFoundError: if no post is found
    """
    if not can_read(session, subdomain, cookie):
        raise errors.UnauthorizedActionError("User not allowed to read")

    corna: models.CornaTable = _current_corna(session, subdomain)
    post: Optional[models.PostTable] = (
        session
        .query(models.PostTable)
        .filter(models.PostTable.url_extension == url_extension)
        .one_or_none()
    )

    if not post or post.deleted is True or post.corna_uuid != corna.uuid:
        logger.warning(
            "post with extension %s does not exist on corna with domain %s",
            url_extension,
            subdomain,
        )
        raise PostNotFoundError("Post does not exist.")

    theme_path = str(theme(session, corna) / "post.html")
    return Post.from_model(post, subdomain), theme_path


def build_page(
    session: SessionT,
    subdomain: str,
    cookie: Optional[str] = None,
) -> CornaPage:
    """Build page for Corna and return a ``CornaPage``.

    :param SessionT session: a db session
    :param str subdomain: Corna subdomain
    :param Optional[str] cookie: user cookie
    :returns: Renderable page payload with stable listing contract.
    :rtype: CornaPage
    """
    # page builder checks if the corna exists and whether or not it is private
    # so we don't need to do any safety checks here. Endpoint will catch errors
    page = CornaPage.load(session, subdomain, cookie=cookie)
    return page


def about(
    session: SessionT,
    subdomain: str,
    cookie: Optional[str] = None,
) -> AboutDTO:
    """Build about page for a corna.

    :param SessionT session: db connection
    :param str subdomain: corna we care about
    :param Optional[str] cookie: the user cookie, if available.

    :returns: The details for the corna about page.
    :rtype: AboutDTO
    :raises UnauthorizedActionError: if page is private
    """
    def about_text(session: SessionT, uuid: str) -> Optional[str]:
        """Get the about text data.

        :param SessionT session: connection to db
        :param str uuid: UUID for text to lookup in content table
        :return: raw about content
        :rtype: Optional[str]
        """
        about_: Optional[models.TextContent] = (
            session
            .query(models.TextContent)
            .filter(models.TextContent.uuid == uuid)
            .one_or_none()
        )

        if not about_:
            return None

        return about_.content

    def user_avatar(
        session: Session,
        user: models.UserTable,
    ) -> Optional[str]:
        """Get owner avatar.

        This is temp. Eventually we'll give each corna an icon/logo.
        We'll use that for the about pages rather than just the owners
        avatar.

        :param SessionT session: db connection
        :param UserTable user: user data required for lookup
        :returns: avatar url if corna has avatar
        :rtype: Optional[str]
        """
        if not user.avatar:
            return None
        # unless something catastrophic happened, the user avatar should
        # point to an valid entry in the db
        # this will raise an error if no rows are found
        avatar: models.Media = (
            session
            .query(models.Media)
            .filter(models.Media.uuid == user.avatar)
            .one()
        )

        return avatar.url_extension

    if not can_read(session, subdomain, cookie):
        raise errors.UnauthorizedActionError("User not allowed to read")

    corna: models.CornaTable = _current_corna(session, subdomain)
    # grab all useful data we need
    owner = corna.user.username
    theme_path = str(theme(session, corna) / "about.html")
    title = corna.title if corna.title else None

    about_text_ = None
    if corna.about:
        about_text_ = about_text(session, corna.about)

    if (avatar_url := user_avatar(session, corna.user)):
        # create the full url
        avatar_url = \
            f"{utils.UNVERSIONED_API_URL}/v1/media/download/{avatar_url}"

    return AboutDTO(
        owner=owner,
        theme_path=theme_path,
        about=about_text_,
        title=title,
        avatar_url=avatar_url,
    )
