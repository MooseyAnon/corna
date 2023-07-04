# Shared data for tests


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
