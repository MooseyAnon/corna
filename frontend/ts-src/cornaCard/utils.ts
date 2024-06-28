/* Shared utilities for CornaCard */

import { createDivElement } from "./../lib/utils.js";


/* The base elements that are on every CornaCard view. */
interface CornaCardElements {
    cardContainer: HTMLDivElement;
    errorMessage: HTMLParagraphElement;
    overlay: HTMLDivElement;
    statusMessage: HTMLParagraphElement;
}


/**
 * Holds the different "Views" of the CornaCard.
 * 
 * These are the elements that actually hold each of the different
 * CornCard views.
 *
 * Only one of these is open at any given time but we need to remove
 * them from the DOM when closing the overlay for the modals.
 */
interface Views {
    characterCard: HTMLElement | null;
    characterCreator: HTMLElement | null;
    cornaCardContainer: HTMLElement | null;
    imageModal: HTMLElement | null;
    permission: HTMLElement | null;
    registerContainer: HTMLElement | null;
    signInContainer: HTMLElement | null;
    textModal: HTMLElement | null;
    videoModal: HTMLElement | null;
}


/**
 * Displays error messages on each View.
 * 
 * @param { string } message: message to display.
 */
export function displayErrorMessage(message: string): void {
    stateManager.errorMessage.textContent = message;
}


/**
 * Clear any error message on a View.
 */
export function clearErrorMessage(): void {
    displayErrorMessage("");
}


/**
 * Displays the status message on a View.
 * 
 * Typically, a status message occurs to give informative updates to the user
 * during some of the more complex process/actions e.g. registration.
 * 
 * @param { string } message: The status message
 * @returns { void }
 */ 
export function displayStatusMessage(message: string): void {
    stateManager.statusMessage.textContent = message;
}


/**
 * Clear any status message on a view.
 */
export function clearStatusMessage(): void {
    displayStatusMessage("");
}


/**
 * Clear all message on a view
 */ 
export function resetMessages(): void {
    clearErrorMessage();
    clearStatusMessage();
}


/**
 * Show the overlay for views.
 */
export function showOverlay(): void {
    stateManager.overlay.style.display = "flex";
    stateManager.overlay.addEventListener("click", function() {
        closeOverlay();
        // We send a message to the parent page because that is who deals
        // with page resizing.
        window.parent.postMessage("close", "*");
    })
}


/**
 * Close the view overlay.
 */
export function closeOverlay(): void {
    // remove any elements that are in view
    removeViews(views());

    stateManager.overlay.style.display = "none";
    // replace view with empty card (modal)
    const emptyContentDiv: HTMLDivElement = createDivElement();
    emptyContentDiv.id = "content";
    stateManager.cardContainer.appendChild(emptyContentDiv);
}


/**
 * Remove any views that currently on display.
 * 
 * @param { Views } views: object containing references to all views.
 * @returns { void }
 */
function removeViews(views: Views): void {
    views.characterCard && views.characterCard.remove()
    views.characterCreator && views.characterCreator.remove()
    views.cornaCardContainer && views.cornaCardContainer.remove()
    views.imageModal && views.imageModal.remove()
    views.permission && views.permission.remove()
    views.registerContainer && views.registerContainer.remove()
    views.signInContainer && views.signInContainer.remove()
    views.textModal && views.textModal.remove()
    views.videoModal && views.videoModal.remove()
}


/**
 * Initialize views manager object.
 * 
 * @returns { Views }
 */
function views(): Views {
    const characterCard: HTMLElement | null = document.getElementById("characterCard");
    const characterCreator: HTMLElement | null = document.getElementById("characterCreator");
    const cornaCardContainer: HTMLElement | null = document.getElementById("cornaCardContainer");
    const imageModal: HTMLElement | null = document.getElementById("imageModal");
    const permission: HTMLElement | null = document.getElementById("permissionsContainer");
    const registerContainer: HTMLElement | null = document.getElementById("registerContainer");
    const signInContainer: HTMLElement | null = document.getElementById("signInContainer");
    const textModal: HTMLElement | null = document.getElementById("textModal");
    const videoModal: HTMLElement | null = document.getElementById("videoModal");

    return {
        characterCard,
        characterCreator,
        cornaCardContainer,
        imageModal,
        permission,
        registerContainer,
        signInContainer,
        textModal,
        videoModal,
    }
}


/**
 * Initialize object which holds all the base Corna card elements.
 * 
 * "Base" elements are elements that are present on the page regardless of the
 * current view.
 */
function init(): CornaCardElements {
    const cardContainer = document.getElementById("cardContainer") as HTMLDivElement;
    const errorMessage = document.getElementById("validation") as HTMLParagraphElement;
    const overlay = document.getElementById("overlay") as HTMLDivElement;
    const statusMessage = document.getElementById("statusUpdateMessage") as HTMLParagraphElement;

    return {
        cardContainer,
        errorMessage,
        overlay,
        statusMessage,
    }
}


const stateManager: CornaCardElements = init();
