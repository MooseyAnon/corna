/* Handle invite requests. */

import {
    RequestReturnType as RRT,
    handleNetworkError,
    request,
} from "./../lib/network.js";

import {
    clean,
    handlePromise,
    isEmail,
    queryRequired,
} from "./../lib/utils.js";

import { displayStatusMessage } from "./utils.js";


interface InviteRequestData {
    email: string;
    referral_source: string | null;
}


function setStatus(
    statusElement: HTMLElement,
    message: string,
    status: "error" | "success" | "loading",
): void {
    statusElement.textContent = message;
    statusElement.classList.remove("error", "success");

    if (status !== "loading") {
        statusElement.classList.add(status);
    }
}


function isValidEmail(email: string): boolean {
    return Boolean(email && isEmail(email));
}


export function requestInvite(): void {
    const root = document.getElementById(
        "requestInviteContainer",
    ) as HTMLElement | null;
    if (!root) { return; }

    // Prevent stacking listeners if the view is swapped in multiple times.
    if (root.dataset.bound === "1") { return; }
    root.dataset.bound = "1";

    const submitButton = queryRequired<HTMLButtonElement>(
        root,
        "#requestInviteSubmit",
        "requestInviteSubmit",
    );
    const emailInput = queryRequired<HTMLInputElement>(
        root,
        "#requestInviteEmailInput",
        "requestInviteEmailInput",
    );
    const referralSourceInput = queryRequired<HTMLTextAreaElement>(
        root,
        "#requestInviteReferralSourceInput",
        "requestInviteReferralSourceInput",
    );
    const statusElement = queryRequired<HTMLElement>(
        root,
        "#requestInviteStatus",
        "requestInviteStatus",
    );

    submitButton.addEventListener("click", async function(e: UIEvent) {
        e.preventDefault();

        const email = clean(emailInput.value);
        const referralSource = referralSourceInput.value.trim();

        if (!isValidEmail(email)) {
            setStatus(statusElement, "Please enter a valid email address", "error");
            return;
        }

        if (referralSource.length > 1000) {
            setStatus(
                statusElement,
                "Please keep your answer under 1000 characters",
                "error",
            );
            return;
        }

        const payload: InviteRequestData = {
            email: email,
            referral_source: referralSource || null,
        };

        submitButton.disabled = true;
        setStatus(statusElement, "Sending request...", "loading");

        const [error, response] = await handlePromise(
            request("v1/auth/invite-request", "post", payload),
        ) as RRT;

        submitButton.disabled = false;

        if (response) {
            emailInput.value = "";
            referralSourceInput.value = "";
            setStatus(
                statusElement,
                "Invite requested. We'll be in touch.",
                "success",
            );
            displayStatusMessage("Congratulations!!");
            return;
        }

        if (error) {
            setStatus(statusElement, handleNetworkError(error), "error");
        }
    });
}
