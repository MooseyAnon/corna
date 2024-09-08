import pytest

from corna import enums
from corna.controls import subdomain_control as control
from corna.db import models
from corna.middleware import permissions as perms
from corna.utils import errors
from tests.shared_data import ASSET_DIR, corna_info, single_user


def create_corna(client, corna_permissions=[]):
    resp = client.post(
        f"/api/v1/corna/{corna_info['domain_name']}",
        json={
            "title": corna_info["title"],
            "permissions": corna_permissions,
        },
    )
    assert resp.status_code == 201


def test_can_not_read_posts(session, client, login):
    # create private corna
    create_corna(client)
    
    try:
        control.post_list(session, corna_info['domain_name'])
        assert False
    except errors.UnauthorizedActionError:
        # we shouldn't have permissions to see anything on the page
        assert True


def test_user_can_read__read_perms_set_on_corna(session, client, login):
    create_corna(client, corna_permissions=["read"])
    
    try:
        # anyone should be able to read page
        control.post_list(session, corna_info['domain_name'])
        assert True
    except errors.UnauthorizedActionError:
        assert False


def test_user_can_read__private_corna_but_owner(session, client, login):
    # create private corna
    create_corna(client)
    cookie = client.get_cookie(enums.SessionNames.SESSION.value)
    assert cookie is not None
    
    try:
        # Owner should be able to see page
        control.post_list(
            session,
            corna_info['domain_name'],
            cookie=cookie.value,
        )
        assert True
    except errors.UnauthorizedActionError:
        assert False


def test_single_post__can_not_read(session, client, login):
    # create private corna
    create_corna(client)
    
    try:
        control.single_post(
            session,
            "fake-url-extension",
            corna_info['domain_name'],
        )
        assert False
    except errors.UnauthorizedActionError:
        # we shouldn't have permissions to see anything on the page
        assert True
