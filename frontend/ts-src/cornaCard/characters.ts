/* Character cards */

import htmx from 'htmx.org';

import {
    RequestReturnType as RRT,
    handleNetworkError,
    request,
} from "./../lib/network";

import {
    createDivElement,
    handlePromise,
    queryOptional,
    queryRequired,
} from "./../lib/utils.js";

import { displayErrorMessage, resetMessages } from "./utils.js";


interface Role {
    domainName: string;
    roleName: string;
}


interface Character {
    name: string;
    default: string;
    /**
     * Characters, and thus skills, are bound to a single Corna.
     * This allows characters with the same name to be created for
     * multiple Corna's.
     */
    domainName: string;
    identifier: string;
    member: string[];
    skill: string[];
}


// these are placeholder icons for characters. In the future users will be
// able to create custom characters
const identiferIcons: string[] = ["🪄", "🎀", "⛑️", "🎩"]

/**
 * Keep track of the currently selected character.
 *
 * This avoids race conditions where HTMX swaps in a new fragment
 * and we need to know which character's data should populate it.
 *
 * We store only the minimal identity needed.
 */
let selectedCharacter: Character | null = null;


/**
 * Register a single global HTMX afterSwap listener.
 *
 * IMPORTANT:
 * - We attach this only once.
 * - We aggressively filter events so this does nothing unless
 *   the swap target is #permissionsContainer.
 *
 * Why not attach to #permissionsContainer?
 * Because that element is replaced via outerHTML swap.
 * Attaching to it would cause duplicate bindings.
 */
let htmxListenerRegistered = false;


function registerHtmxSwapListener(): void {
    if (htmxListenerRegistered) return;

    document.body.addEventListener("htmx:afterSwap", function (event: Event) {

        const swapTarget = event.target as HTMLElement | null;
        if (!swapTarget) return;

        // Only care about swaps that target the permissions container
        if (swapTarget.id !== "permissionsContainer") return;

        /**
         * CASE 1:
         * permissions.html has just been swapped in.
         * We should re-render the list of characters.
         */
        if (queryOptional(swapTarget, "#charactersContainer")) {
            characters();  // rebuild tiles
            return;
        }

        /**
         * CASE 2:
         * character.html has just been swapped in.
         * We must render the selected character details.
         */
        const characterRoot = queryOptional(swapTarget, "#characterCard");
        if (characterRoot && selectedCharacter) {
            renderCharacterDetails(characterRoot, selectedCharacter);
        }

    });

    htmxListenerRegistered = true;
}


/**
 * Build character tiles for all existing characters.
 *
 * This function:
 * - Fetches the list of roles
 * - Fetches skills + members in parallel per role
 * - Renders tiles
 *
 * It is safe to call multiple times (container is cleared first).
 */
export async function characters(): Promise<void> {

    registerHtmxSwapListener();

    const charactersContainer = document.getElementById("charactersContainer") as HTMLDivElement;
    if (!charactersContainer) return;

    // Clear previous content to avoid duplication on swap-back
    charactersContainer.innerHTML = "";

    const roles: Role[] = await getCharacterList();

    /**
     * Instead of sequential:
     *   await skills
     *   await members
     *
     * We parallelise per role to avoid slow N+1 waterfall behaviour.
     */
    for (let i = 0; i < roles.length; i++) {

        const role: Role = roles[i];

        const [skills, members] = await Promise.all([
            getCharacterSkills(role.roleName, role.domainName),
            getMembers(role.roleName, role.domainName),
        ]);

        const idx: number = Math.floor(Math.random() * identiferIcons.length);

        const character: Character = {
            name: role.roleName,
            domainName: role.domainName,
            identifier: identiferIcons[idx],
            default: i === 0 ? "DEFAULT" : "",
            skill: skills,
            member: members,
        };

        const characterHtml: HTMLDivElement = buildCharacter(character);

        charactersContainer.appendChild(characterHtml);
    }
}


/**
 * Create a single character tile element.
 *
 * Clicking the tile:
 * - Sets selectedCharacter
 * - Triggers HTMX swap to character view
 */
function buildCharacter(permission: Character): HTMLDivElement {

    const character = createDivElement(["character"]) as HTMLDivElement;
    const identifier = createDivElement(["characterIdentifer"]) as HTMLDivElement;
    const characterName = createDivElement(["characterName"]) as HTMLDivElement;
    const pill = createDivElement(["pill"]) as HTMLDivElement;

    /**
     * Configure HTMX navigation.
     *
     * Clicking this tile will swap #permissionsContainer
     * with character.html.
     */
    character.setAttribute("hx-get", "cornaCore/characterCard");
    character.setAttribute("hx-trigger", "click");
    character.setAttribute("hx-target", "#permissionsContainer");
    character.setAttribute("hx-swap", "outerHTML");

    /**
     * Store selection in memory BEFORE swap.
     * AfterSwap listener will read this.
     */
    character.addEventListener("click", function () {
        selectedCharacter = permission;
    });

    characterName.textContent = permission.name;
    identifier.textContent = permission.identifier;

    /**
     * Only show DEFAULT pill if applicable.
     * Fixes previous logical bug.
     */
    if (permission.default) {
        pill.textContent = permission.default;
    } else {
        pill.style.opacity = "0";
    }

    character.appendChild(characterName);
    character.appendChild(identifier);
    character.appendChild(pill);

    htmx.process(character);

    return character;
}


/**
 * Render character details inside the swapped character card fragment.
 *
 * This function:
 * - Clears previous DOM state
 * - Populates skills
 * - Populates members
 * - Avoids duplication across repeated swaps
 *
 * @param {HTMLElement} root - #characterCard container
 * @param {Character} permission - selected character data
 */
function renderCharacterDetails(
    root: HTMLElement,
    permission: Character,
): void {

    const headerCopy = queryRequired<HTMLDivElement>(root, "#modalHeaderCopy", "modalHeaderCopy");
    const membersDetails = queryRequired<HTMLDivElement>(root, "#membersDetails", "membersDetails");
    const characterCardName = queryRequired<HTMLDivElement>(root, "#characterCardName", "characterCardName");
    const characterIdentifier = queryRequired<HTMLDivElement>(root, "#characterIdentifer", "characterIdentifer");
    const skills = queryRequired<HTMLDivElement>(root, "#skills", "skills")

    // Clear previous content to prevent duplication
    skills.innerHTML = "";
    membersDetails.innerHTML = "";

    headerCopy.textContent = "YOUR CHARACTER";
    characterCardName.textContent = permission.name;
    characterIdentifier.textContent = permission.identifier;

    // Populate skills
    for (const skill of permission.skill) {
        const skillElement = createDivElement(["value"]);
        skillElement.textContent = skill;
        skills.appendChild(skillElement);
    }

    // Populate members
    for (const fullname of permission.member) {

        const memberElement = createDivElement(["member"]);
        const deleteButton = createDivElement(["deleteMember"]);

        const initials = fullname
            .split(" ")
            .map((part: string) => part.charAt(0))
            .join("");

        memberElement.textContent = initials;

        deleteButton.textContent = "remove";
        deleteButton.style.display = "none";

        memberElement.addEventListener("mouseover", function() {
            deleteButton.style.display = "flex";
        });

        memberElement.addEventListener("mouseout", function() {
            deleteButton.style.display = "none";
        });

        deleteButton.addEventListener("click", function() {
            console.log(`deleting member: ${fullname}`);  // eslint-disable-line no-console
        });

        memberElement.appendChild(deleteButton);
        membersDetails.appendChild(memberElement);
    }
}


// ------- networking stuff -------

async function getCharacterList(): Promise<Role[]> {
    // remove any previous error messages
    resetMessages()

    const characters: Role[] = [];

    const [error, response] = await handlePromise(
        request("v1/user/roles/created")) as RRT;

    if (response) {
        // sloppy late definition of the role data type
        type RoleData = { roles: Array<{ domain_name: string, name: string }> };

        const roleData: RoleData = response.data;
        for (let i = 0; i < roleData.roles.length; i++ ) {
            const role: { domain_name: string, name: string } = roleData.roles[i];
            const character: Role = {
                "domainName": role.domain_name,
                "roleName": role.name,
            }
            characters.push(character);
        }
    }

    if (error) {
        const errMsg: string = handleNetworkError(error);
        displayErrorMessage(errMsg);

    }

    return characters;
}


async function getCharacterSkills(
    roleName: string,
    domainName: string,
): Promise<string[]> {

    let permissions: string[] = [];

    const [error, response] = await handlePromise(
        request(`v1/roles/${domainName}/${roleName}/permissions`)) as RRT;

    if (response) {
        permissions = response.data.permissions;
    }

    if (error) {
        const errMsg: string = handleNetworkError(error);
        displayErrorMessage(errMsg);
    }

    return permissions;
}


async function getMembers(
    roleName: string,
    domainName: string
): Promise<string[]> {

    let users: string[] = [];

    const [error, response] = await handlePromise(
        request(`v1/roles/${domainName}/${roleName}/users`)) as RRT;

    if (response) {
        users = response.data.users;
    }

    if (error) {
        const errMsg: string = handleNetworkError(error);
        displayErrorMessage(errMsg);
    }

    return users;
}
