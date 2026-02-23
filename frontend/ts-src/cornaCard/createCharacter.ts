/* create a character */

import {
    AxiosError,
    AxiosResponse,
} from "axios";

import {
    handleNetworkError,
    request,
} from "./../lib/network.js";

import { queryRequired } from "./../lib/utils.js";
import {
    closeOverlay,
    displayErrorMessage,
    displayStatusMessage,
    resetMessages
} from "./utils.js";


interface CharacterCreateElements {
    root: HTMLElement;
    chosenIdentifer: HTMLDivElement;
    skills: NodeListOf<HTMLDivElement>;
    characterNameInput: HTMLInputElement;
    identifierOptions: NodeListOf<HTMLDivElement>;
    createCharacterButton: HTMLButtonElement;
    selectedSkills: string[];
    domainName: string;
}


/**
 * Find the current fragment root for the character creator UI.
 *
 * We intentionally *avoid* global document-wide selectors because:
 * - HTMX swaps can leave old fragments in the DOM briefly
 * - multiple modals/fragments can exist over time
 * - IDs repeat across fragments (common in your UI)
 *
 * Strategy:
 * 1) Anchor on the one element we know must exist: the submit button (#createCharacter)
 * 2) Walk up to a sensible "root" container via .closest(...)
 *
 * @returns { HTMLElement | null } Root container for scoping queries, or null if not found.
 */
function findCreateCharacterRoot(): HTMLElement | null {
    const submit = document.getElementById("createCharacter") as HTMLElement | null;
    if (!submit) return null;

    // Prefer your shared modal container class, otherwise fall back to the parent element.
    return (submit.closest(".bodyLargeContainer") as HTMLElement | null) ?? submit.parentElement;
}


/**
 * Bind listeners only once per fragment root.
 *
 * HTMX swaps can call init multiple times; without a guard, you'd stack listeners
 * and duplicate actions.
 *
 * @param { HTMLElement } root: fragment root
 * @returns { boolean } true if we should bind, false if already bound.
 */
function shouldBind(root: HTMLElement): boolean {
    const key = "createCharacterBound";
    if (root.dataset[key] === "1") return false;
    root.dataset[key] = "1";
    return true;
}


/**
 * Reset the UI state so the fragment is deterministic each time it appears.
 *
 * - clears input + identifier
 * - removes selection styling
 * - clears selectedSkills array (critical: avoids stale data between opens)
 *
 * @param { CharacterCreateElements } el: state for this fragment
 * @returns { void }
 */
function resetForm(el: CharacterCreateElements): void {
    el.characterNameInput.value = "";
    el.chosenIdentifer.textContent = "";
    el.selectedSkills.length = 0;

    el.skills.forEach((skill) => skill.classList.remove("activeSelection"));
    el.identifierOptions.forEach((opt) => opt.classList.remove("activeSelection"));
}


/**
 * Validate character name.
 *
 * Keep this strict + cheap: the server should remain the source of truth.
 *
 * @param { string } characterName: the name to validate
 * @returns { boolean } true if valid
 */
function isValid(characterName: string): boolean {
    const hasErrd: boolean = !characterName || !characterName.trim();
    if (hasErrd) displayErrorMessage("Character needs to be given a name.");
    return !hasErrd;
}


/**
 * Bind all UI event listeners for the character creator.
 *
 * Identifier icons are essentially gimmicky little icons associated with each
 * character. A character can only have one of them so most of the logic inside
 * the loops is making sure that there is only one icon selected.
 * 
 * Important invariants:
 * - only bind once per fragment root
 * - never reference global stateManager inside handlers (handlers close over `el`)
 *
 * @param { CharacterCreateElements } el: scoped state for this fragment
 * @returns { void }
 */
function bindEventListeners(el: CharacterCreateElements): void {
    // submit button
    el.createCharacterButton.addEventListener("click", () => submitCharacter(el));

    // ---- skill toggles ----
    // Each skill is a toggle:
    // - adds/removes "activeSelection" CSS
    // - adds/removes skill text from selectedSkills
    el.skills.forEach((skill) => {
        skill.addEventListener("click", () => {
            const value = (skill.textContent ?? "").trim();
            if (!value) return;

            if (skill.classList.contains("activeSelection")) {
                // Unselect: remove highlight + remove from selectedSkills
                skill.classList.remove("activeSelection");

                const index: number = el.selectedSkills.indexOf(value);
                if (index !== -1) el.selectedSkills.splice(index, 1);
                return;
            }

            // Select: highlight + append add if skill is not already selected
            const index: number = el.selectedSkills.indexOf(value)
            if (index === -1) el.selectedSkills.push(value);
            skill.classList.add("activeSelection");
        });
    });

    // ---- identifier (single-select) ----
    // Only one identifier can be active at a time.
    // The chosen identifier is displayed in el.chosenIdentifer.
    el.identifierOptions.forEach((option) => {
        option.addEventListener("click", () => {
            const val = (option.textContent ?? "").trim();
            el.chosenIdentifer.textContent = val;

            // mark this as active, clear all others
            el.identifierOptions.forEach((other) => {
                other.classList.toggle("activeSelection", other === option);
            });
        });
    });
}


/**
 * Submit a new character/role to the API.
 *
 * @param { CharacterCreateElements } el: scoped state for this fragment
 * @returns { void }
 */
function submitCharacter(el: CharacterCreateElements): void {
    resetMessages();

    const name = el.characterNameInput.value;
    if (!isValid(name)) return;

    const data = {
        // NOTE: identifier is currently UI-only. So we can leave it out
        domain_name: el.domainName,
        name: name.trim(),
        permissions: el.selectedSkills,
    };

    request("v1/roles", "post", data)
    .then((response: AxiosResponse) => {
        if (response.status === 201) {
            displayStatusMessage("Successfully created role");
            // Small delay so user sees the success message.
            setTimeout(() => { closeOverlay(); }, 1200);
        }
    })
    .catch((error: AxiosError) => {
        const errMsg: string = handleNetworkError(error);
        displayErrorMessage(errMsg);
    });
}


/**
 * Initialize element references *scoped to the fragment root*.
 *
 * This prevents collisions with other swapped fragments that reuse the same IDs.
 *
 * @param { HTMLElement } root: fragment root container
 * @param { string } domainName_: corna domain for request payload
 * @returns { CharacterCreateElements }
 */
function elementsInit(root: HTMLElement, domainName_: string): CharacterCreateElements {

    const chosenIdentifer = queryRequired<HTMLDivElement>(root, "#selectedIdentifer", "selectedIdentifer");
    const characterNameInput = queryRequired<HTMLInputElement>(root, "#characterNameInput", "characterNameInput");
    const createCharacterButton = queryRequired<HTMLButtonElement>(root, "#createCharacter", "createCharacter");
    const skills = root.querySelectorAll(".skills .skillOption") as NodeListOf<HTMLDivElement>;
    const identifierOptions = root.querySelectorAll(
        ".identifierOptionContainer .identiferIcon",
    ) as NodeListOf<HTMLDivElement>;

    return {
        root,
        chosenIdentifer,
        skills,
        characterNameInput,
        identifierOptions,
        createCharacterButton,
        selectedSkills: [],
        domainName: domainName_,
    };
}

/**
 * Entry point called after the HTMX swap.
 *
 * - finds root
 * - scopes all queries to root
 * - binds listeners once
 * - resets form deterministically
 *
 * @param { string | null } domainName
 * @returns { void }
 */
export function createCharacter(domainName: string | null): void {
    if (!domainName) return;

    const root = findCreateCharacterRoot() as HTMLElement | null;
    if (!root) return;

    // Build a fresh scoped state object for this fragment instance.
    const el: CharacterCreateElements = elementsInit(root, domainName);

    // Bind once per root to avoid stacked listeners.
    if (shouldBind(root)) {
        bindEventListeners(el);
    }

    // Always reset UI so it opens cleanly every time.
    resetForm(el);
}
