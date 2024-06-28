/* Character cards */

import {
    RequestReturnType as RRT,
    handleNetworkError,
    request,
} from "./../lib/network";

import { createDivElement, handlePromise } from "./../lib/utils.js";

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


const identiferIcons: string[] = ["🪄", "🎀", "⛑️", "🎩"]


export async function characters() {
    const charactersContainer = document.getElementById("charactersContainer") as HTMLDivElement;
    const roles: Role[] = await getCharacterList();

    for (let i = 0; i < roles.length; i++) {
        const role: Role = roles[i];
        const skills: string[] = await getCharacterSkills(role.roleName, role.domainName);
        const members: string[] = await getMembers(role.roleName, role.domainName);

        const idx: number = Math.floor(Math.random() * identiferIcons.length)

        const character: Character = {
            "name": role.roleName,
            "domainName": role.domainName,
            "identifier": identiferIcons[idx],
            "default": i == 0 ? "DEFAULT" : "",
            "skill": skills,
            "member": members,
        }

        const characterHtml: HTMLDivElement = buildCharacter(character);

        charactersContainer.appendChild(characterHtml);
    }
}


function buildCharacter(permission: Character): HTMLDivElement {
    const character = createDivElement(["character"]) as HTMLDivElement;
    const identifier = createDivElement(["characterIdentifer"]) as HTMLDivElement;
    const characterName = createDivElement(["characterName"]) as HTMLDivElement;
    const pill = createDivElement(["pill"]) as HTMLDivElement;

    character.setAttribute("hx-get", "cornaCore/characterCard"); // Example URL, replace with your actual endpoint
    character.setAttribute("hx-trigger", "click");
    character.setAttribute("hx-target", "#permissionsContainer");
    character.setAttribute("hx-swap", "outerHTML");

    character.addEventListener("click", function() {
        document.addEventListener("htmx:afterSwap", function() {
            characterInfor(permission);
        }, { once: true });
    });

    characterName.textContent = permission.name;
    pill.textContent = permission.default;
    identifier.textContent = permission.identifier;

    if (permission.default === "" || null) {
        pill.style.opacity = "0";
    }

    character.appendChild(characterName);
    character.appendChild(identifier);
    character.appendChild(pill);

    return character;
}


function characterInfor(permission: Character) {
    const memberButton = document.getElementById("addMemeber");

    const headerCopy = document.getElementById("modalHeaderCopy") as HTMLDivElement;
    headerCopy.textContent = "YOUR CHARACTER";

    const membersDetails = document.getElementById("membersDetails") as HTMLDivElement;
    const identifierDetails = document.getElementById("identifierDetails") as HTMLDivElement;

    const characterCardName = document.getElementById("characterCardName") as HTMLDivElement;
    characterCardName.textContent = permission.name;

    const characterIdentifer = document.getElementById("characterIdentifer") as HTMLDivElement;
    characterIdentifer.textContent = permission.identifier;

    const skills = document.getElementById("skills") as HTMLDivElement;
    for (let i = 0; i < permission.skill.length; i++) {
        const skillElement = createDivElement(["value"]);
        skillElement.textContent = permission.skill[i];

        skills.appendChild(skillElement);
    }

    for (let i = 0; i < permission.member.length; i++) {
        const memberElement = createDivElement(["member"]);

        const fullname = permission.member[i]
        const initals = fullname.split(" ").map((part: any) => part.charAt(0)).join("");
        memberElement.textContent = initals;

        memberElement.addEventListener("mouseover", function() {
            deleteButton.style.display = "flex";
        });

        memberElement.addEventListener("mouseout", function() {
            deleteButton.style.display = "none";
        });

        const deleteButton = createDivElement(["deleteMemeber"]);
        deleteButton.textContent = "remove";
        deleteButton.style.display = "none";
        memberElement.appendChild(deleteButton);

        deleteButton.addEventListener("click", function() {
            console.log(`deleting the member: ${fullname}`);
        });

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

    else if (error) {
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
