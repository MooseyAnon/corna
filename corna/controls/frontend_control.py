"""Code for building frontend pages."""

from sqlalchemy.orm import load_only


def simplified_post_list(corna_object, domain_name):

    simplified_post_list = [
        {
            "post_uuid": post.post_uuid,
            "domain_name": domain_name,
            "created": post.created,
            "type": post.type,
            "title": _post_title(post),
            "post_url": \
                (
                    "http://192.168.1.152:8080/api/v1/frontend/"
                    f"{domain_name}/post/{post.type}/{post.post_uuid}"
                )
        } for post in corna_object.posts
    ]

    return simplified_post_list


def _post_title(post):

    # jinja2 doesn't render an empty string but ill render None, so its safer
    # to leave it as an empty string and a caller does not need to worry about
    # any conditional checking
    title = ""
    if post.type == "text":
        obj = post.mapper.text

        if obj.title:
            title = obj.title


    if post.type == "picture":
        obj = post.mapper.photo

        if obj.caption:
            title = obj.caption if len(obj.caption) < 90 else obj.caption[:91]

    return title
