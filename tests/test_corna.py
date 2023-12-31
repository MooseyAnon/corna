import pytest

from corna import enums
from corna.controls import corna_control as control
from corna.db import models
from corna.utils.errors import NoneExistingUserError
from corna.utils import secure
from tests.shared_data import corna_info, single_user


def test_corna_create(session, client, login):

    resp = client.post(
        f"/api/v1/corna/{corna_info['domain_name']}",
        json={"title": corna_info["title"]},
    )
    assert resp.status_code == 201
    
    # check everything saved correctly in db
    assert len(session.query(models.CornaTable).all()) == 1
    corna = (
        session.query(models.CornaTable)
        .filter(models.CornaTable.domain_name == corna_info["domain_name"])
        .one_or_none()
    )
    assert corna is not None
    user = single_user()
    assert corna.user.username == user["user_name"]


def test_when_user_not_logged_in(session):

    data = {
        "cookie": secure.sign("some-fake-cookie"),
        "title": corna_info["title"],
        "domain_name": corna_info["domain_name"],
    }

    # an exception should be raised
    try:
        control.create(session, data)
        assert False
    except NoneExistingUserError:
        assert True


def test_when_user_not_logged_in_client(client):

    resp = client.post(
        f"/api/v1/corna/{corna_info['domain_name']}",
        json={"title": corna_info["title"]},
    )
    assert resp.status_code == 400
    assert "Login required for this action" in resp.json["message"]


def test_user_attempt_with_invalid_cookie(client):
    client.set_cookie(
        "/",
        key=enums.SessionNames.SESSION.value,
        value="this-is-a-fake-cookie"
    )
    resp = client.post(
        f"/api/v1/corna/{corna_info['domain_name']}",
        json={"title": corna_info["title"]},
    )
    assert resp.status_code == 400
    assert "Login required for this action" in resp.json["message"]


def test_user_already_has_corna(client, corna):
    resp = client.post(
        "/api/v1/corna/new-corna-name",
        json={"title": corna_info["title"]},
    )
    assert resp.status_code == 400
    assert resp.json["message"] == "User has pre-existing Corna"


def test_domain_name_not_unique(session, client, corna):
    # make new adhoc user
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email_address": "new.email@tester.com",
            "password": "some-fake=password",
            "user_name": "nunu-user",
            }
        )
    assert resp.status_code == 201

    # login
    resp = client.post("/api/v1/auth/login",
        json={
            "email_address": "new.email@tester.com",
            "password": "some-fake=password",
        }
    )
    assert resp.status_code == 200
    # attempt to make corna
    resp = client.post(
        f"/api/v1/corna/{corna_info['domain_name']}",
        json={"title": corna_info["title"]},
    )
    assert resp.status_code == 400
    assert resp.json["message"] == "Domain name in use"


def test_relationships(session, client, login):

    resp = client.post(
        f"/api/v1/corna/{corna_info['domain_name']}",
        json={"title": corna_info["title"]},
    )
    assert resp.status_code == 201

    # check everything saved correctly in db
    assert len(session.query(models.CornaTable).all()) == 1
    corna = (
        session.query(models.CornaTable)
        .filter(models.CornaTable.domain_name == corna_info["domain_name"])
        .one_or_none()
    )

    usr = (
        session.query(models.UserTable)
        .filter(models.UserTable.username == "john_snow")
        .one_or_none()
    )
    assert usr is not None
    assert corna.user is usr
    assert usr.corna[0] is corna



def test_domain_name_available_check__when_not_avail(client, corna):
    # the "corna" fixture creates this domain
    domain_name = "some-fake-domain"
    resp = client.get(f"/api/v1/corna/domain/available?domain_name={domain_name}")
    assert resp.status_code == 200

    expected = {
        "domain_name": domain_name,
        "available": False,
    }
    assert resp.json == expected


def test_domain_name_available_check__when_avail(client):
    domain_name = "some-fake-domain"
    resp = client.get(f"/api/v1/corna/domain/available?domain_name={domain_name}")
    assert resp.status_code == 200

    expected = {
        "domain_name": domain_name,
        "available": True,
    }
    assert resp.json == expected
