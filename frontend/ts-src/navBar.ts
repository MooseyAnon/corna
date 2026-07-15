/* Handle nav bar functionality 

This is the main entry point for the 'control panel' of Corna i.e. the
sidebar. At its core this is a 'single page application' of multiple views
powered by HMTX.

This script holds centralised data needed by different HTMX components, while
also listening for `htmx-swap` events in in order to trigger the related JS for
said component.

There are probably better ways of using HTMX (components are too large and
we're doing stuff in JS that could be handled by HTML natively e.g. forms) but
we suck at frontend so thats how things work at this current moment.

This file gets linked into `cornaCard.html` which is where all the swaps take
place - grep for `content`, thats the div that holds swapped components.
*/

import { createMessage } from "./lib/messages.js";
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

    flags: {
        modalOpen: boolean;
        hoverBound: boolean;
        createClickOutBound: boolean;
        yourCornaBound: boolean;
    };
}


function openModal(): void {
    if (state.flags.modalOpen) { return; }
    state.flags.modalOpen = true;

    const message = createMessage(
        "toolbar:open",
        {},
    );

    window.parent.postMessage(message, "*");
    showOverlay();
}


function isModalSwap(event: Event): boolean {
    const target = event.target as HTMLElement | null;
    // We only consider swaps into #content as “modal swaps”.
    return !!target && target.id === "content";
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
    const yourCornaOption = document.getElementById("yourCorna") as HTMLElement | null;
    if (!yourCornaOption) { return; }

    // Always update the latest domain on the element.
    if (domainName) {
        yourCornaOption.dataset.domainName = domainName;
    }

    // Bind once.
    if (state.flags.yourCornaBound) { return; }
    state.flags.yourCornaBound = true;

    yourCornaOption.addEventListener("click", function() {
        const dn = (yourCornaOption.dataset.domainName ?? "").trim();
        if (!dn) { return; }
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
        const message = createMessage(
            "toolbar:navigate",
            {
                domainName: dn,
            },
        );

        window.parent.postMessage(message, "*");
    });
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

    // Bind hover listeners once; refreshNav can run after login/register.
    if (!state.flags.hoverBound) {
        hoverEventListeners();
        state.flags.hoverBound = true;
    }


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
 * The calling order of the swaps is as follows (look in comments for html
 * file path):
 *   - CornaCore -> children:
 *      - signin
 *      - register
 *      - post -> children:
 *          - text post
 *          - video post
 *          - image post
 *      - cornaCard -> children:
 *          - (character) permissions
 *          - (character) creator
 * 
 * @param { Event } event: A HTMX event
 * @returns { Promise<void> }
 */
async function processSwaps(): Promise<void> {
    // remove any error/status messages that may be on screen from last swap.
    resetMessages();

    /**
     * Handle post-HTMX swap initialisation.
     *
     * We no longer rely on the event target to determine what was swapped.
     * Instead, we treat `#content` as the single swap mount point for all
     * primary view changes.
     *
     * Using hx-swap="innerHTML" means the container itself remains stable
     * while only its children are replaced. This allows us to:
     * - Avoid fragile event.target assumptions
     * - Always initialise against a known root (#content)
     * - Keep view lifecycle logic deterministic
     *
     * All fragment initialisation should now be derived from the current
     * contents of #content rather than from the swap event payload.
     */
    const content = document.getElementById("content") as HTMLDivElement | null;
    if (!content) { return; }

    // Helper: enforce domain existence for flows that require it
    const requireDomain = (): string | null => {
        if (!state.domainName) {
            displayErrorMessage("No Corna domain found. Please create one or re-login.");
            return null;
        }
        return state.domainName;
    };

    // Map swapped-in container -> handler
    const routes: Array<[string, () => void | Promise<void>]> = [
        // swaps in html/signin.html
        ["#signInContainer", () => login(refreshNav)],

        // swaps in html/register.html
        ["#registerContainer", () => processNewUser()],

        // swaps in html/cornaCard.html
        ["#cornaCardContainer", () => cornaCardInit()],

        // swaps in html/permissions.html
        ["#permissionsContainer", () => characters()],

        // swaps in html/characterCreator.html
        ["#characterCreator", () => {
            const dn = requireDomain();
            if (!dn) { return; }
            createCharacter(dn);
        }],

        // swaps in textModal.html
        ["#textModal", () => {
            const dn = requireDomain();
            if (!dn) { return; }
            createPostTest("text", dn);
        }],

        // swaps in imageModal.html
        ["#imageModal", () => {
            const dn = requireDomain();
            if (!dn) { return; }
            createPostTest("picture", dn);
        }],

        // swaps in videoModal.html
        ["#videoModal", () => {
            const dn = requireDomain();
            if (!dn) { return; }
            createPostTest("video", dn);
        }],
    ];

    for (const [selector, handler] of routes) {
        // Look inside #content for the swapped-in view root
        if (content.querySelector(selector)) {
            await handler();
            return;
        }
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
        flags: {
            modalOpen: false,
            hoverBound: false,
            createClickOutBound: false,
            yourCornaBound: false,
        },
    }
}


document.addEventListener("DOMContentLoaded", async function() {
    await refreshNav();

    document.addEventListener("htmx:beforeSwap", function(event: Event) {
        if (!isModalSwap(event)) { return; }
        openModal();
    });

    // afterSettle fires after transitions/attributes settle rather than on just
    // DOM swaps
    document.addEventListener("htmx:afterSettle", async function() {
        await processSwaps();
    });

    const createEl = document.getElementById("create") as HTMLElement | null;
    if (createEl) {
        createEl.addEventListener("click", function(event: MouseEvent) {
            createOptionsHover(event, this as HTMLOListElement);

            if (!state.flags.createClickOutBound) {
                document.addEventListener("click", clickOut);
                state.flags.createClickOutBound = true;
            }
        });
    }

    // ensure we update state when modal is closed
    document.addEventListener("corna:modalClosed", function() {
        state.flags.modalOpen = false;
    });

});


// init global state manager
const state: State = init();
