import pytest

from corna.middleware import permissions as perms


@pytest.mark.parametrize("perm_list,expected",
    [
        ([], 0),
        (["read"], 1),
        (["read", "write", "edit"], 7),
        (["read", "comment", "like", "follow"], 449),
        (["write", "edit", "delete", "change_theme", "change_permissions"], 62),
        (["i-do-not-exist", "neither-do-i", "should-return-nothing"], 0)
    ]
)
def test_create_role(perm_list, expected):
    """A role is a set of permissions with a name attached."""
    assert perms.create_role(perm_list) == expected


@pytest.mark.parametrize("perm_list",
    [
        ([]),
        (["read"]),
        (["read", "write", "edit"]),
        (["read", "comment", "like", "follow"]),
        (["write", "edit", "delete", "change_theme", "change_permissions"]),
        ([
            "read", "write", "edit", "delete", "change_theme",
            "change_permissions", "comment", "like", "follow",
        ]),
    ]
)
def test_role_has_perms(perm_list):
    role = perms.create_role(perm_list)
    expected = {
        "change_theme": False,
        "comment": False,
        "delete": False,
        "edit": False,
        "follow": False,
        "like": False,
        "read": False,
        "change_permissions": False,
        "write": False
    }

    for item in perm_list:
        expected[item] = True

    assert perms.perms(role) == expected


@pytest.mark.parametrize("perm_list,check_perm,expected",
    [
        ([], "read", False),
        (["read"], "read", True),
        (["read", "write", "edit"], "delete", False),
        (["read", "comment", "like", "follow"], "write", False),
        (["write", "edit", "delete", "change_theme"], "follow", False),
        (["write", "fake-perm"], "fake-perm", False),
    ]
)
def test_has_perm(perm_list, check_perm, expected):
    role = perms.create_role(perm_list)
    assert perms.has_perm(role, check_perm) == expected


@pytest.mark.parametrize("perm_list,perm_to_add",
    [
        ([], "read"),
        (["read", "write", "edit"], "delete"),
        (["read", "comment", "like", "follow"], "write"),
        (["write", "edit", "delete", "change_theme"], "change_permissions"),
    ]
)
def test_add_perm(perm_list, perm_to_add):
    role = perms.create_role(perm_list)
    # ensure perm isn't already in role
    assert perms.has_perm(role, perm_to_add) == False

    # updated role
    role = perms.add_perm(role, perm_to_add)
    assert perms.has_perm(role, perm_to_add) == True


def test_add_perm__none_existing_perm():
    role = perms.create_role(["read", "write"])
    # ensure perm isn't already in role
    assert perms.has_perm(role, "fake-perm") == False
    # updated role
    role = perms.add_perm(role, "fake-perm")
    assert perms.has_perm(role, "fake-perm") == False
    # ensure role has other perms
    assert perms.has_perm(role, "read") == True
    assert perms.has_perm(role, "write") == True    


@pytest.mark.parametrize("perm_list,perm_to_add,expected",
    [
        (["read"], "read", 1),
        (["read", "write", "edit"], "edit", 7),
        (["read", "comment", "like", "follow"], "follow", 449),
        (
            ["write", "edit", "delete", "change_theme","change_permissions"],
            "write", 62,
        ),
    ]
)
def test_add_perm__same_perm_to_role(perm_list, perm_to_add, expected):
    role = perms.create_role(perm_list)
    assert role == expected
    # add one of the same roles
    assert perms.add_perm(role, perm_to_add) == expected


@pytest.mark.parametrize("perm_list,perm_to_remove",
    [
        (["read"], "read"),
        (["read"], "write"),
        (["read", "write", "edit"], "edit"),
        (["read", "comment", "like", "follow"], "comment"),
        (["write", "edit", "delete", "change_theme"], "change_theme"),
        (["write", "edit", "delete"], "change_theme"),
    ]
)
def test_remove_perm(perm_list, perm_to_remove):
    role = perms.create_role(perm_list)
    # updated role
    role = perms.remove_perm(role, perm_to_remove)
    assert perms.has_perm(role, perm_to_remove) == False


def test_composite_roles():
    reader = perms.create_role(["read"])
    editor = perms.create_role(["edit", "write"])
    # ensure composite has correct perms
    assert (reader | editor) == 7


def test_composite_role__with_overlapping_perms():
    reader = perms.create_role(["read", "write"])
    editor = perms.create_role(["edit", "write"])
    # ensure composite has correct perms
    assert (reader | editor) == 7
