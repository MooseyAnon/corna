/* Main CornaCard view */

import {
    RequestReturnType as RRT,
    handleNetworkError,
    request,
} from "./../lib/network";

import { handlePromise, queryOptional } from "./../lib/utils.js";

import { displayErrorMessage } from "./utils.js";


interface CornaCardElements {

    username: HTMLHeadingElement;
    cred: HTMLSpanElement;
    role: HTMLParagraphElement;
    avatar: HTMLImageElement;
}


interface StateManager {
    closeButton: HTMLButtonElement;
    cornaCardElements: CornaCardElements;
}


interface CornaCard {
    username: string;
    cred: string;
    role: string;
    avatar: string;
}


/**
 * Get the root element for the Corna card fragment.
 *
 * This fragment is HTMX-swapped, so we should scope DOM queries to the swapped
 * container to avoid collisions with other views.
 *
 * @returns {HTMLElement | null} Root container for this fragment.
 */
function getCornaCardRoot(): HTMLElement | null {
    return document.getElementById("cornaCardContainer");
}


async function getUserDetails(): Promise<CornaCard | null> {
    let userDetails: CornaCard | null = null;

    const [error, response] = await handlePromise(request("v1/user")) as RRT;

    if (response) {
            userDetails = response.data;
    }
    else if (error) {
        const errMsg: string = handleNetworkError(error);
        displayErrorMessage(errMsg)
    }

    return userDetails;
}


function cardInit(root: HTMLElement): CornaCardElements | null {
    const username = queryOptional<HTMLHeadingElement>(root, "#username");
    const cred = queryOptional<HTMLSpanElement>(root, "#cred");
    const role = queryOptional<HTMLParagraphElement>(root, "#role");
    const avatar = queryOptional<HTMLImageElement>(root, "#avatarImage");

    if (!username || !cred || !role || !avatar) {
        displayErrorMessage("Corna card failed to load (missing UI elements).");
        return null;
    }

    return {
        username,
        cred,
        role,
        avatar,
    };
}


function init(root: HTMLElement): StateManager | null {
    const cornaCardElements = cardInit(root);
    if (!cornaCardElements) { return null; }

    const closeButton = queryOptional<HTMLButtonElement>(root, "#close");
    if (!closeButton) {
        displayErrorMessage("Corna card failed to load (missing close button).");
        return null;
    }

    return {
        closeButton,
        cornaCardElements,
    };
}


export async function cornaCardInit(): Promise<void> {
    const root = getCornaCardRoot();
    if (!root) {
        displayErrorMessage("Corna card failed to load (missing container).");
        return;
    }

    const stateManager = init(root);
    if (!stateManager) { return; }

    const currentUser: CornaCard | null = await getUserDetails();

    if (currentUser) {
        stateManager.cornaCardElements.username.textContent = currentUser.username;
        stateManager.cornaCardElements.cred.textContent = currentUser.cred;
        stateManager.cornaCardElements.role.textContent = currentUser.role;
        stateManager.cornaCardElements.avatar.src = currentUser.avatar;
    }
}
