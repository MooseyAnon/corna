/* Corna login page. */


import { getApiUrl, postData } from "./lib/network.js";
import {
    clean,
    isEmail,
    spaceAtStart,
    spaceAtEnd
} from "./lib/utils.js";

interface LoginData {
    /* Login schema. */
    email_address: string;
    password: string;
}


export function onPageLoad(): void {
    /* add click event listener.
    *
    * @returns { void }
    */

    const loginButton = document.getElementById("Login") as HTMLButtonElement;

    if (!loginButton) { return; }

    loginButton.addEventListener("click", function(e: UIEvent) {
        e.preventDefault();
        parseForm();
    })
}


export function parseForm(): void {
    /* Grab all inputs and validate.
    *
    * @returns { void }
    */

    const emailInput = document.getElementById("userEmailInput") as HTMLInputElement;
    const passwordInput = document.getElementById("userPasswordInput") as HTMLInputElement;

    // these functions will call error handling functions
    if (!isValidEmail(emailInput) || !isValidPassword(passwordInput)) { return; }

    const dataToSend: LoginData = {
        email_address: clean(emailInput.value),
        password: passwordInput.value,
    }
    postData(dataToSend,"v1/auth/login", errorMessage);
}


export function isValidEmail(email: HTMLInputElement | null): boolean {
    /* Validate user email.
    *
    * @param { HTMLInputElement | null } email: email to validate
    * @returns { booloan }
    */

    // very basic check, server side will do most of the checking
    const hasErrd: boolean = (
        !email
        || !email.value
        || !isEmail(clean(email.value))
    );

    if (hasErrd) { errorMessage("Please enter a valid email address"); }

    return !hasErrd
}


export function isValidPassword(password: HTMLInputElement | null): boolean {
    /* Validate user password.
    *
    * @param { HTMLInputElement | null } password: password to validate
    * @returns { booloan }
    */

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


export function errorMessage(msg: string): void {
    /* Display error message.
    *
    * @param { string } msg: the error message to display
    * @returns { void }
    */
    const errorMessage = document.getElementById("errorMessage") as HTMLDivElement;
    errorMessage.textContent = msg;
}


document.addEventListener("DOMContentLoaded", function() {
    /* Initialize on page load.*/
    onPageLoad();

    const regButton = document.getElementById("createAccount") as HTMLButtonElement;

    if (!regButton) { return; }
    regButton.addEventListener("click", function() {
        window.location.href = `${getApiUrl()}/register`;
    });
});
