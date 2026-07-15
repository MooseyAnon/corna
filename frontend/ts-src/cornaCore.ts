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
    if (typeof event.data !== "string") { return; }

    if (event.data === "open") {
        setFrameEnlarged(frame, true);
        return;
    }

    if (event.data === "close") {
        setFrameEnlarged(frame, false);
        return;
    }

    // parsing includes simple domain validation
    const domainName = parseDomainNameMessage(event.data);

    if (domainName !== null) {
        navigateToCorna(domainName);
    }
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
 * Parse domain name from message.
 *
 * @param { string } message: The incoming message
 * @returns { string | null }: the domain name if it's valid.
 */
function parseDomainNameMessage(message: string): string | null {
    const prefix = "domainName=";

    if (!message.startsWith(prefix)) {
        return null;
    }

    const domainName = message.slice(prefix.length).trim();

    if (!isValidDomainName(domainName)) {
        return null;
    }

    return domainName;
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
    const targetHostname = `${domainName}.mycorna.com`;

    if (window.location.hostname === targetHostname) { return; }

    const targetUrl = new URL(`https://${targetHostname}`);
    window.location.assign(targetUrl);
}

document.addEventListener("DOMContentLoaded", initialiseNavigationFrame);
