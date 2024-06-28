/* Handle nav bar functionality */

import {
    RequestReturnType as RRT,
    handleNetworkError,
    request,
} from "./lib/network.js";

import { handlePromise } from "./lib/utils.js";

import { displayErrorMessage, resetMessages, showOverlay } from "./cornaCard/utils.js";
import { createOptionsHover, clickOut, hoverEventListeners } from "./cornaCard/hover.js"; 
import { processNewUser } from "./cornaCard/register.js";
import { createPostTest } from "./cornaCard/post.js";
import { cornaCardInit } from "./cornaCard/card.js";
import { characters } from "./cornaCard/characters.js";
import { createCharacter } from "./cornaCard/createCharacter.js";
import { login } from "./cornaCard/login.js";


/**
 * Login check response.
 */
interface LoginCheck {
    is_loggedin: boolean;
}


/**
 * Holds global state.
 */
interface State {
    isLoggedIn: boolean;
    loggedInNavigation: HTMLUListElement;
    loggedOutNavigation: HTMLUListElement;
    overlay: HTMLDivElement;
    domainName: string | null;
}


/**
 * Refresh the users login status.
 * 
 * @returns { void }
 */
async function refreshLoginStatus(): Promise<void> {

    const [, response] = await handlePromise(request("v1/auth/login_status")) as RRT;

    if (response) {
        const checkRes: LoginCheck = response.data;
        state.isLoggedIn = checkRes.is_loggedin;
    }
}


/**
 * Get the current users Corna domain.
 * 
 * @returns { Promise<string | null> } a promise resulting in either the users
 * corna domain or null.
 */ 
async function getDomain(): Promise<string | null> {
    let domainName: string | null = null;

    const [error, response] = await handlePromise(request("v1/corna")) as RRT;

    if (response) {
        domainName = response.data.domain_name;
    }

    else if (error) {
        const errMsg: string = handleNetworkError(error);
        displayErrorMessage(errMsg);
    }

    return domainName;
}


/**
 * Set the "Your Corna" button on the nav bar.
 * 
 * @param { string | null } domainName: the user corna domain. This can be null
 *      so we need to handle that case.
 * @returns { void }
 */ 
function setYourCorna(domainName: string | null): void {

    if (!domainName) { return; }

    const yourCornaOption = document.getElementById("yourCorna") as HTMLOListElement;

    yourCornaOption.addEventListener("click", async function() {
        /**
         * The nav bar is an iframe that lives on each page of the website.
         * As a result if we make the "Your Corna" button a regular anchor tag
         * it will result in the iframe page changing rather than the main
         * page we are currently viewing.
         * 
         * To solve this we need to send a message to the parent page whenever
         * the button has been clicked. This allows the parent page - which
         * is the page we actually want to change - to handle the redirect.
         */
        window.parent.postMessage(`domainName=${domainName}`, "*");
    })
}


/**
 * Refresh navbar and set appropriate values.
 * 
 * @returns { Promise<void> }
 */
async function refreshNav(): Promise<void> {
    // check login status
    await refreshLoginStatus();

    updateNavigation();
    hoverEventListeners();

    if (state.isLoggedIn) {
        state.domainName = await getDomain();
        setYourCorna(state.domainName);
    }
}


function updateNavigation(): void {
    if (state.isLoggedIn) {
        state.loggedInNavigation.style.display = "flex";
        state.loggedOutNavigation.style.display = "none";
    } else {
        state.loggedInNavigation.style.display = "none";
        state.loggedOutNavigation.style.display = "flex";
    }
}


/**
 * Process the HTMX swaps.
 * 
 * This is the core function that handles interactions with the HTMX events.
 * Typically each event requires use to swap in and/or out some snippet of
 * HTML code.
 * 
 * @param { Event } event: A HTMX event
 * @returns { Promise<void> }
 */
async function processSwaps(event: Event): Promise<void> {

    // the event has no target, there is nothing to do.
    if (!event.target) { return; }

    // remove any error/status messages that may be on screen from last swap.
    resetMessages()

    const target = event.target as HTMLElement;

    if (target.matches("#signInContainer")) {
        login(refreshNav);
        // bellow does not work because we need the system to call the update
        // only after the loging/register button has been clicked

        // await refreshLoginStatus();
        // updateNavigation();
    } else if (target.matches("#registerContainer")) {
        await processNewUser();
    } else if (target.matches("#cornaCardContainer")) {
        cornaCardInit();
    } else if (target.matches("#permissionsContainer")) {
        await characters();
    } else if (target.matches("#characterCreator")) {
        createCharacter(state.domainName);
    } else if (target.matches("#textModal")) {
        createPostTest("text", state.domainName);
    } else if (target.matches("#imageModal")) {
        createPostTest("picture", state.domainName);
    } else if (target.matches("#videoModal")) {
        createPostTest("video", state.domainName);
    }
}


/**
 * initialse the state manager.
 * 
 * @returns { State }: object holding the state.
 */ 
function init(): State {
    const loggedInNavigation = document.getElementById("loggedInNavigation") as HTMLUListElement;
    const loggedOutNavigation = document.getElementById("loggedOutNavigation") as HTMLUListElement;
    const overlay = document.getElementById("overlay") as HTMLDivElement;
    const isLoggedIn: boolean = false;
    const domainName: string | null = null;

    return {
        isLoggedIn,
        loggedInNavigation,
        loggedOutNavigation,
        overlay,
        domainName,
    }
}


document.addEventListener("DOMContentLoaded", async function() {
    await refreshNav();

    document.addEventListener("htmx:beforeSwap", function() {
        // send message to parent page that the modal has been opened.
        window.parent.postMessage("open", "*");
        showOverlay();
    });

    document.addEventListener("htmx:afterSwap", async function(event: Event) {
        const cardContainer = document.getElementById("cardContainer") as HTMLDivElement;
        cardContainer.addEventListener("click", function(event: MouseEvent) {
            // prevent the post model from closing while interacting with it
            event.stopPropagation();
        });

        await processSwaps(event);
    });

    document.getElementById("create")!.addEventListener("click", function(event: MouseEvent) {
        createOptionsHover(event, this as HTMLOListElement);
        document.addEventListener("click", clickOut);
    });
});


// init global state manager
const state: State = init();
