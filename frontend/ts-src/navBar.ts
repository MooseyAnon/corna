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

import { createMessage, HostMessage, MESSAGE_VERSION } from "./lib/messages.js";
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


/**
 * Toolbar view lifecycle.
 */
interface ToolbarRoute {
    selector: string;
    handler: () => void | Promise<void>;
}


// Helper: enforce domain existence for flows that require it
const requireDomain = (): string | null => {
    if (!state.domainName) {
        displayErrorMessage(
            "No Corna domain found. Please create one or re-login.");
        return null;
    }
    return state.domainName;
};


/**
 * Map swapped-in toolbar views to their initialisation handlers.
 */
const toolbarRoutes: ToolbarRoute[] = [
    // swaps in html/signin.html
    {
        selector: "#signInContainer",
        handler: () => login(refreshNav),
    },

    // swaps in html/register.html
    {
        selector: "#registerContainer",
        handler: () => processNewUser(),
    },

    // swaps in html/cornaCard.html
    {
        selector: "#cornaCardContainer",
        handler: () => cornaCardInit(),
    },

    // swaps in html/permissions.html
    {
        selector: "#permissionsContainer",
        handler: () => characters(),
    },

    // swaps in html/characterCreator.html
    {
        selector: "#characterCreator",
        handler: () => {
            const domainName = requireDomain();
            if (!domainName) { return; }

            createCharacter(domainName);
        },
    },

    // swaps in textModal.html
    {
        selector: "#textModal",
        handler: () => {
            const domainName = requireDomain();
            if (!domainName) { return; }

            createPostTest("text", domainName);
        },
    },

    // swaps in imageModal.html
    {
        selector: "#imageModal",
        handler: () => {
            const domainName = requireDomain();
            if (!domainName) { return; }

            createPostTest("picture", domainName);
        },
    },

    // swaps in videoModal.html
    {
        selector: "#videoModal",
        handler: () => {
            const domainName = requireDomain();
            if (!domainName) { return; }

            createPostTest("video", domainName);
        },
    },
];


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

    for (const route of toolbarRoutes) {
        if (content.querySelector(route.selector)) {
            await route.handler();
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

/* ----- message handling stuff. -------- */

/**
 * Handle incoming messages from the host.
 * 
 * @param { MessageEvent<unknown> } event: the incoming message
 */
function handleHostMessage(event: MessageEvent<unknown>): void {
    if (!isMessageFromHost(event)) { return; }

    if (!isHostMessage(event.data)) { return; }

    if (event.data.type === "host:intent") {
        handleHostIntent(event.data.payload.intent);
    }
}


/**
 * Ensure incoming message is actually from the host.
 * 
 * @param { MessageEvent<unknown> } event: the incoming message
 * @returns { boolean }: true if message is from the host, else false
 */
function isMessageFromHost(
    event: MessageEvent<unknown>,
): boolean {
    return (
        isValidCornaOrigin(event.origin)
        && event.source === window.parent
    );
}


/**
 * Ensure incoming message is a valid host message.
 * 
 * We also do some type casting once we've confirmed message is valid.
 * 
 * @param { unknown } data: contents of the message
 * @returns { HostMessage | boolean }:
 */
function isHostMessage(data: unknown): data is HostMessage {
    if (!isMessage(data)) {
        return false;
    }

    return data.type.startsWith("host:");
}


/**
 * Ensure message origin is actually from a valid Corna URL.
 * 
 * @param { string } origin: the URL in question
 * @returns { boolean }:
 */
function isValidCornaOrigin(origin: string): boolean {
    try {
        const url = new URL(origin);

        return (
            url.protocol === "https:"
            && (
                url.hostname === "mycorna.com"
                || url.hostname.endsWith(".mycorna.com")
            )
        );
    } catch {
        return false;
    }
}


/**
 * Validate message contents.
 * 
 * @param { unknown } data: message contents
 * @returns validated message or false
 */
function isMessage(
    data: unknown,
): data is {
    version: number;
    type: string;
    payload: unknown;
} {
    if (typeof data !== "object" || data === null) {
        return false;
    }

    if (!("version" in data) || data.version !== MESSAGE_VERSION) {
        return false;
    }

    if (!("type" in data) || typeof data.type !== "string") {
        return false;
    }

    if (!("payload" in data)) {
        return false;
    }

    return true;
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

        // send message to parent to close the modal window
        const message = createMessage(
            "toolbar:close",
            {},
        );

        window.parent.postMessage(message, "*");
    });

    // let the parent know the toolbar is ready
    const message = createMessage(
        "toolbar:ready",
        {},
    );

    window.parent.postMessage(message, "*");

});


// init global state manager
const state: State = init();
