# Shared data for tests
import pathlib

ASSET_DIR = pathlib.Path(__file__).parent.absolute() / "assets"

blog_info = {
        "domain_name": "some-fake-domain",
        "title": "some-fake-title",
    }


simple_text_post = {
    "type": "text",
    "content": \
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed "
        "do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut "
        "enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi "
        "ut aliquip ex ea commodo consequat. Duis aute irure dolor in "
        "reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla "
        "pariatur. Excepteur sint occaecat cupidatat non proident, sunt in "
        "culpa qui officia deserunt mollit anim id est laborum.",
    "title": "this is a title of a post",
}


post_with_picture = {
    "type": "picture",
    "caption": "this is a picture I did not take",
    "pictures": (ASSET_DIR / "anders-jilden.jpg").open("rb"),
}


def single_user(
    email_address="azor_ahi@starkentaprise.wstro",
    password="Dany",
    user_name="john_snow"
):
    return {
        "email_address": email_address,
        "password": password,
        "user_name": user_name,
    }
