/* Handle logged-in invite generation. */

import {
    RequestReturnType as RRT,
    handleNetworkError,
    request,
} from "./../lib/network.js";

import {
    handlePromise,
    queryRequired,
} from "./../lib/utils.js";


interface InviteResponse {
    join_url: string;
}


const INVITE_BASE_URL = "https://mycorna.com";


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


function buildInviteUrl(joinUrl: string): string {
    const path = joinUrl.startsWith("/") ? joinUrl : `/${joinUrl}`;
    return `${INVITE_BASE_URL}${path}`;
}


async function createInvite(
    inviteInput: HTMLInputElement,
    statusElement: HTMLElement,
    regenerateButton: HTMLButtonElement,
    copyButton: HTMLButtonElement,
): Promise<void> {
    regenerateButton.disabled = true;
    copyButton.disabled = true;
    inviteInput.value = "Generating invite...";
    setStatus(statusElement, "Generating invite...", "loading");

    const [error, response] = await handlePromise(
        request("v1/auth/invite", "post"),
    ) as RRT;

    regenerateButton.disabled = false;

    if (response) {
        const data = response.data as InviteResponse;
        inviteInput.value = buildInviteUrl(data.join_url);
        copyButton.disabled = false;
        setStatus(statusElement, "Invite ready.", "success");
        return;
    }

    if (error) {
        inviteInput.value = "Invite could not be generated";
        setStatus(statusElement, handleNetworkError(error), "error");
    }
}


async function copyInvite(
    inviteInput: HTMLInputElement,
    statusElement: HTMLElement,
): Promise<void> {
    if (!inviteInput.value || inviteInput.value === "Generating invite...") {
        setStatus(statusElement, "No invite to copy yet.", "error");
        return;
    }

    if (!navigator.clipboard) {
        setStatus(statusElement, "Clipboard is unavailable.", "error");
        return;
    }

    try {
        await navigator.clipboard.writeText(inviteInput.value);
        setStatus(statusElement, "Invite copied.", "success");
    } catch {
        setStatus(statusElement, "Invite could not be copied.", "error");
    }
}


export function generateInvite(): void {
    const root = document.getElementById(
        "generateInviteContainer",
    ) as HTMLElement | null;
    if (!root) { return; }

    // Prevent stacking listeners if the view is swapped in multiple times.
    if (root.dataset.bound === "1") { return; }
    root.dataset.bound = "1";

    const inviteInput = queryRequired<HTMLInputElement>(
        root,
        "#generatedInviteInput",
        "generatedInviteInput",
    );
    const regenerateButton = queryRequired<HTMLButtonElement>(
        root,
        "#regenerateInvite",
        "regenerateInvite",
    );
    const copyButton = queryRequired<HTMLButtonElement>(
        root,
        "#copyInvite",
        "copyInvite",
    );
    const statusElement = queryRequired<HTMLElement>(
        root,
        "#generateInviteStatus",
        "generateInviteStatus",
    );

    regenerateButton.addEventListener("click", async function(e: UIEvent) {
        e.preventDefault();
        await createInvite(
            inviteInput,
            statusElement,
            regenerateButton,
            copyButton,
        );
    });

    copyButton.addEventListener("click", async function(e: UIEvent) {
        e.preventDefault();
        await copyInvite(inviteInput, statusElement);
    });

    void createInvite(
        inviteInput,
        statusElement,
        regenerateButton,
        copyButton,
    );
}
