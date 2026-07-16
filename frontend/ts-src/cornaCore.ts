/* Core JS script that will be injected into each Corna.

Fundamentally, the relationship between - the generated - cornaCore.js and
navBar.js is as follows:
    - All client facing files will use cornaCore.js. This will create the
    iFrame which contains the nav bar and also correctly display it on the
    page, there is an accompanying cornaCore.css.

    - navBar.js on the other hand is only embedded inside the nav bar itself
    i.e. the code inside the iFrame. That code is what actually coordinates the
    nav bar's behaviour and actions. It also has an accompanying navBar.css
*/

import { createMessage, MESSAGE_VERSION, ToolbarMessage } from "./lib/messages.js";
import { createDivElement, createIframeElement } from "./lib/utils.js";

const NAV_ORIGIN = "https://mycorna.com";
const NAV_FRAME_SRC = `${NAV_ORIGIN}/nav?mode=fragment`;
const ENLARGED_CLASS = "enlargeIframe";


/**
 * Init the navbar iFrame and the message listener.
 */
function initialiseNavigationFrame(): void {
    const frame = createNavigationFrame();

    window.addEventListener("message", (event: MessageEvent<unknown>) => {
        handleNavigationMessage(event, frame);
    });
}


/**
 * Create navbar iFrame.
 * 
 * @returns { HTMLIFrameElement }
 */
function createNavigationFrame(): HTMLIFrameElement {
    const frameContainer = createDivElement([
        "frameContainer",
    ]) as HTMLDivElement;

    const frame = createIframeElement(
        NAV_FRAME_SRC,
    ) as HTMLIFrameElement;

    frameContainer.appendChild(frame);
    document.body.appendChild(frameContainer);

    return frame;
}


/**
 * Handle messages from the navbar.
 * 
 * @param { MessageEvent<unknown> } event: the incoming message
 * @param { HTMLIFrameElement } frame: the iFrame
 * @returns { void }
 */
function handleNavigationMessage(
    event: MessageEvent<unknown>,
    frame: HTMLIFrameElement,
): void {
    if (!isMessageFromNavigationFrame(event, frame)) { return; }
    if (!isToolbarMessage(event.data)) { return; }

    if (event.data.type === "toolbar:open") {
        setFrameEnlarged(frame, true);
        return;
    }

    if (event.data.type === "toolbar:close") {
        setFrameEnlarged(frame, false);
        return;
    }

    if (event.data.type === "toolbar:navigate") {
        navigateToCorna(event.data.payload.domainName);
    }

    if (event.data.type === "toolbar:ready") {
        handleToolbarReady(frame);
        return
    }
}


/**
 * Validate message is from our iFrame.
 * 
 * @param { unknown } data: the message
 * @returns { ToolbarMessage }: if message is valid
 */
function isToolbarMessage(data: unknown): data is ToolbarMessage {
    if (!isMessage(data)) {
        return false;
    }

    return data.type.startsWith("toolbar:");
}


/**
 * Check message.
 * 
 * This function is here to essentially validate then convert the data to
 * a known type for the compiler to catch errors.
 * 
 * @param { unknown } data: incoming message
 * @returns the message cast to the correct type
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


/**
 * Validate message is actually from our frame.
 * 
 * @param { MessageEvent<unknown> } event: the incoming message
 * @param { HTMLIFrameElement } frame: the iFrame
 * @returns { boolean }: true if message is from our frame, else false
 */
function isMessageFromNavigationFrame(
    event: MessageEvent<unknown>,
    frame: HTMLIFrameElement,
): boolean {
    return (
        event.origin === NAV_ORIGIN &&
        event.source === frame.contentWindow
    );
}


/**
 * Toggle modal enlargement.
 * 
 * Modal enlargement is essentially adding or removing a class. This function
 * ensures that toggling is idempotent.
 * 
 * @param { HTMLIFrameElement } frame: the iFrame
 * @param { boolean } enlarged: the state to change to.
 * @returns { void }
 */
function setFrameEnlarged(
    frame: HTMLIFrameElement,
    enlarged: boolean,
): void {
    frame.classList.toggle(ENLARGED_CLASS, enlarged);
}


/**
 * Validate domain name.
 * 
 * @param { string } domainName: the string to validate
 * @returns { boolean }
 */
function isValidDomainName(domainName: string): boolean {
    /*
     * Corna domain names are treated as a single DNS label.
     *
     * This permits:
     * - lowercase ASCII letters
     * - numbers
     * - internal hyphens
     *
     * It rejects dots, slashes, ports, whitespace and leading/trailing
     * hyphens.
     */
    const domainNamePattern = /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/;

    return domainNamePattern.test(domainName);
}


/**
 * Navigate to a users Corna.
 * 
 * This is idempotent so navigation only takes place if the user is
 * not already on their own Corna.
 * 
 * @param { string } domainName: the users domain name
 * @returns { void }
 */
function navigateToCorna(domainName: string): void {
    if (!isValidDomainName(domainName)) { return; }

    const targetHostname = `${domainName}.mycorna.com`;

    if (window.location.hostname === targetHostname) { return; }

    const targetUrl = new URL(`https://${targetHostname}`);
    window.location.assign(targetUrl);
}


/**
 * Handle incoming toolbar handshake message.
 * 
 * @param { HTMLIFrameElement } frame: the iframe
 */
function handleToolbarReady(frame: HTMLIFrameElement): void {
    // for now just do a simple boolean switch. We want to keep this
    // separate from the navigation function as this will likely get more
    // complicated.
    frame.dataset.ready = "true";


/**
 * Send host intent to the toolbar.
 * 
 * @param { HTMLIFrameElement } frame: the frame object
 * @param { string } intent: the data to be passed down
 */
function sendHostIntent(
    frame: HTMLIFrameElement,
    intent: string,
): void {
    if (!frame.contentWindow) { return; }

    const message = createMessage(
        "host:intent",
        {
            intent,
        },
    );

    frame.contentWindow.postMessage(message, "*");
}

document.addEventListener("DOMContentLoaded", initialiseNavigationFrame);
