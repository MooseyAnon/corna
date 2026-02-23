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
    queryOptional,
    queryRequired,
    spaceAtStart,
    spaceAtEnd
} from "./../lib/utils.js";

import { closeOverlay, resetMessages, displayErrorMessage } from "./utils.js";


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
    const root = document.getElementById("signInContainer") as HTMLElement | null;
    if (!root) { return; }

    // Prevent stacking listeners if the sign-in view is swapped in multiple times.
    if (root.dataset.bound === "1") { return; }
    root.dataset.bound = "1";

    const loginButton = queryOptional<HTMLButtonElement>(root, "#signIn");
    if (!loginButton) { return; }

    loginButton.addEventListener("click", async function(e: UIEvent) {
        e.preventDefault();
        await parseForm(root, refreshCallback);
    });

    // Listen for Enter anywhere inside the inputs container.
    const inputsContainer = queryOptional<HTMLElement>(root, ".inputs");
    if (inputsContainer) {
        inputsContainer.addEventListener("keydown", async function(e: KeyboardEvent) {
            if (e.key === "Enter") {
                e.preventDefault();
                await parseForm(root, refreshCallback);
            }
        });
    }
}


/**
 * Grab all inputs and validate.
 * 
 * @param { HTMLElement } root: the modal root element to scope the query
 * @param { () => Promise<void> } refreshCallback: A callback to refersh the
 *      nav bar after logging in successfully. It is done here because we need
 *      to wait till we ensure that login has been done successfully until we
 *      make the transition. The parent code that calls this does not know when
 *      the login process has been completed.
 * @returns { void }
 */
async function parseForm(
    root: HTMLElement,
    refreshCallback: () => Promise<void>
): Promise<void> {
    // remove any previous error message
    resetMessages();

    const postUrl: string = "v1/auth/login";

    const emailInput = queryRequired<HTMLInputElement>(root, "#emailInput", "emailInput");
    const passwordInput = queryRequired<HTMLInputElement>(root, "#passwordInput", "passwordInput");

    // these functions will call error handling functions
    if (!isValidEmail(emailInput) || !isValidPassword(passwordInput)) {
        displayErrorMessage("Invalid email or password");
        return;
    }

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
        displayErrorMessage(errMsg);

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

    return !hasErrd
}
