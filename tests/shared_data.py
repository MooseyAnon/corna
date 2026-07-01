# Shared data for tests
import pathlib

ASSET_DIR = pathlib.Path(__file__).parent.absolute() / "assets"

corna_info = {
        "domain_name": "some-fake-domain",
        "title": "some-fake-title",
    }


def single_user(
    email_address="azor_ahi@starkentaprise.wstro",
    password="Dany",
    user_name="john_snow"
):
    return {
        "email": email_address,
        "password": password,
        "username": user_name,
    }


def mock_post(
    type_="text",
    with_content=False,
    with_title=False,
    with_image=False,
    with_html=False,
):
    post = {"type": type_}

    if with_title:
        post["title"] = "this is a title of a post"

    if with_content:
        post["content"] = (
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed "
            "do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut "
            "enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi "
            "ut aliquip ex ea commodo consequat. Duis aute irure dolor in "
            "reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla "
            "pariatur. Excepteur sint occaecat cupidatat non proident, sunt in "
            "culpa qui officia deserunt mollit anim id est laborum."
        )

    if with_html:
        post["inner_html"] = (
            "<section><h1>Welcome to My Website</h1>"
            "<p>This is a basic paragraph explaining the purpose of the site.</p></section>"
        )

    if with_image:
        post["uploaded_images"] = ["abcdef"]


    return post
