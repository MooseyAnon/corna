/* Main CornaCard view */

import {
    RequestReturnType as RRT,
    handleNetworkError,
    request,
} from "./../lib/network";

import { handlePromise } from "./../lib/utils.js";

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


function cardInit(): CornaCardElements {
    const username = document.getElementById("username") as HTMLHeadingElement;
    const cred = document.getElementById("cred") as HTMLSpanElement;
    const role = document.getElementById("role") as HTMLParagraphElement;
    const avatar = document.getElementById("avatarImage") as HTMLImageElement;

    return {
        username,
        cred,
        role,
        avatar,
    }
}


function init(): StateManager {
    const cornaCardElements: CornaCardElements = cardInit();
    const closeButton = document.getElementById("close") as HTMLButtonElement;

    return {
        closeButton,
        cornaCardElements,
    }
}


export async function cornaCardInit(): Promise<void> {
    stateManager = init();

    const currentUser: CornaCard | null = await getUserDetails();

    if (currentUser) {
        stateManager.cornaCardElements.username.textContent = currentUser.username;
        stateManager.cornaCardElements.cred.textContent = currentUser.cred;
        stateManager.cornaCardElements.role.textContent = currentUser.role;
        stateManager.cornaCardElements.avatar.src = currentUser.avatar;
    }
}


// global state manager, gets created at HTMX swap time
let stateManager: StateManager;
