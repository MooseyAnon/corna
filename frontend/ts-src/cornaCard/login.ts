/* Corna login page. */

import {
    RequestReturnType as RRT,
    handleNetworkError,
    request,
} from "./../lib/network.js";

import {
    clean,
    isEmail,
    handlePromise,
    spaceAtStart,
    spaceAtEnd
} from "./../lib/utils.js";

import { closeOverlay, resetMessages } from "./utils.js";


/**
 * Login schema.
 */
interface LoginData {
    email: string;
    password: string;
}


/**
 * Add click event listener.
 *
 * @returns { void }
 */
export function login(refreshCallback: () => Promise<void>): void {
    const loginButton = document.getElementById("signIn") as HTMLButtonElement;

    if (!loginButton) { return; }

    loginButton.addEventListener("click", async function(e: UIEvent) {
        e.preventDefault();
        await parseForm(refreshCallback);
    })

    const inputs = document.getElementsByClassName("inputs") as HTMLCollectionOf<HTMLInputElement>;
    if (inputs) {
        const input = inputs[0]
        input.addEventListener("keydown", async function(e: KeyboardEvent) {
            if (e.key === "Enter") {
                e.preventDefault();
                await parseForm(refreshCallback);
            }
        })
    }
}


/**
 * Grab all inputs and validate.
 * 
 * @param { () => Promise<void> } refreshCallback: A callback to refersh the
 *      nav bar after logging in successfully. It is done here because we need
 *      to wait till we ensure that login has been done successfully until we
 *      make the transition. The parent code that calls this does not know when
 *      the login process has been completed.
 * @returns { void }
 */
async function parseForm(refreshCallback: () => Promise<void>): Promise<void> {
    // remove any previous error message
    resetMessages();

    const postUrl: string = "v1/auth/login";

    const emailInput = document.getElementById("emailInput") as HTMLInputElement;
    const passwordInput = document.getElementById("passwordInput") as HTMLInputElement;

    // these functions will call error handling functions
    if (!isValidEmail(emailInput) || !isValidPassword(passwordInput)) { return; }

    const loginData: LoginData = {
        email: clean(emailInput.value),
        password: passwordInput.value,
    }

    const [error, response] = await handlePromise(request(postUrl, "post", loginData)) as RRT;

    // these can never both be defined
    if (response) {
        await refreshCallback();
        closeOverlay();
    }

    if (error) {
        const errMsg: string = handleNetworkError(error);
        errorMessage(errMsg);

        emailInput.value = "";  // clear inputs
        passwordInput.value = "";  // clear inputs
    }
}


/**
 * Validate user email.
 *
 * @param { HTMLInputElement | null } email: email to validate
 * @returns { booloan }
 */
function isValidEmail(email: HTMLInputElement | null): boolean {

    // very basic check, server side will do most of the checking
    const hasErrd: boolean = (
        !email
        || !email.value
        || !isEmail(clean(email.value))
    );

    if (hasErrd) { errorMessage("Please enter a valid email address"); }

    return !hasErrd
}


/**
 * Validate user password.
 *
 * @param { HTMLInputElement | null } password: password to validate
 * @returns { booloan }
 */
function isValidPassword(password: HTMLInputElement | null): boolean {
    const hasErrd: boolean = (
        !password
        || !password.value
        || spaceAtStart(password.value)
        || spaceAtEnd(password.value)
    );

    if (hasErrd) {
        errorMessage(
            "Please ensure your password does "
            + "not start or end with a space."
        )
    }
    return !hasErrd
}

/**
 * Display error message.
 *
 * @param { string } msg: the error message to display
 * @returns { void }
 */
function errorMessage(msg: string): void {
    const errorMessage = document.getElementById("validation") as HTMLDivElement;
    errorMessage.textContent = msg;
}
