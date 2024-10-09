/* create a character */

import {
    AxiosError,
    AxiosResponse,
} from "axios";

import {
    handleNetworkError,
    request,
} from "./../lib/network";

import {
    closeOverlay,
    displayErrorMessage,
    displayStatusMessage,
    resetMessages
} from "./utils.js";


interface CharacterCreateElements {

    chosenIdentifer: HTMLDivElement;
    skills: NodeListOf<HTMLDivElement>;
    characterNameInput: HTMLInputElement;
    identifierOptions: NodeListOf<HTMLDivElement>;
    createCharacterButton: HTMLButtonElement;
    selectedSkills: string[];
    domainName: string;
}


/**
 * Event listeners for creating a new character.
 * 
 * The main functionality here is selecting the character "skills" and
 * giving the character a name.
 */
function character() {

    stateManager.characterNameInput.value = "";
    stateManager.chosenIdentifer.textContent = "";
    stateManager.skills.forEach((skill) => {
        // reset all skills to unselected
        skill.classList.remove("activeSelection");
    });

    // Listen to the characterName
    stateManager.characterNameInput.addEventListener("input", function () {
        this.value;
    });

    // skills event listeners
    // toggle selection and add/remove from selected skills list
    stateManager.skills.forEach((skill: HTMLDivElement) => {
        skill.addEventListener("click", function () {

            // remove highlighting from a previously highlighted skill selection
            if (this.classList.contains("activeSelection")) {
                this.classList.remove("activeSelection");

                const index = stateManager.selectedSkills.indexOf(this.textContent!);
                if (index !== -1) stateManager.selectedSkills.splice(index, 1);

            // add newly selected skill
            } else {
                stateManager.selectedSkills.push(skill.textContent!);
                this.classList.add("activeSelection");
            }
        });
    });
}


/**
 * Add event listeners for submit button and selecting character icons.
 *
 * I identifier icons are essentially gimmicky little icons associated with each
 * character. A character can only have one of them so most of the logic inside
 * the loops is making sure that there is only one icon selected.
 */
function addEventListeners() {
    // submit button
    stateManager.createCharacterButton.addEventListener("click", submitCharacter);

    //Allow for selection of identifier and highlight the selected one
    stateManager.identifierOptions.forEach((option) => {
        option.addEventListener("click", function () {
            // if an icon is selected, deselect other icons
            // this implementation means as soon as one icon is pressed it can
            // only be "unselected" by clicking another icon
            stateManager.chosenIdentifer.textContent = option.textContent;
            option.classList.add("activeSelection");

            // Deselect any other clicked icons
            stateManager.identifierOptions.forEach((otherOption) => {
                if (otherOption !== option) {
                    otherOption.classList.remove("activeSelection");
                }
            });
        });
    });
}


/**
 * validate character name.
 * 
 * @param { string } characterName: the name to validate
 * @returns { boolean }
 */
function isValid(characterName: string): boolean {
    const hasErrd: boolean = !characterName || !characterName.trim()
    if (hasErrd) displayErrorMessage("Character needs to be given a name.");
    // we want to return the inverse of whatever `hasErrd` is.
    return !hasErrd
}


/**
 * Create a new Character
 */
function submitCharacter() {

    // clear any messages
    resetMessages();

    if (!isValid(stateManager.characterNameInput.value)) return;

    const data = {
        "domain_name": stateManager.domainName,
        "name": stateManager.characterNameInput.value.trim(),
        "permissions": stateManager.selectedSkills,
    }

    request("v1/roles", "post", data)
    .then((response: AxiosResponse) => {
        if (response.status === 201) {
            displayStatusMessage("Successfully created role");
            // wait for a second before closing overlay
            setTimeout(() => { closeOverlay(); }, 1200);
        }
    })
    .catch((error: AxiosError) => {
        const errMsg: string = handleNetworkError(error);
        displayErrorMessage(errMsg);

    })
}


function elementsInit(domainName_: string): CharacterCreateElements {
    const chosenIdentifer = document.getElementById("selectedIdentifer") as HTMLDivElement;
    const skills = document.querySelectorAll(".skills .skillOption") as NodeListOf<HTMLDivElement>;
    const characterNameInput = document.getElementById("characterNameInput") as HTMLInputElement;
    const identifierOptions = document.querySelectorAll(".identifierOptionContainer .identiferIcon") as NodeListOf<HTMLDivElement>;
    const createCharacterButton = document.getElementById("createCharacter") as HTMLButtonElement;
    const selectedSkills: string[] = [];
    const domainName: string = domainName_;

    return {
        chosenIdentifer,
        skills,
        characterNameInput,
        identifierOptions,
        createCharacterButton,
        selectedSkills,
        domainName,
    }

}


export function createCharacter(domainName: string | null) {
    if (!domainName) return;

    stateManager = elementsInit(domainName as string);
    addEventListeners();
    character();
}

// holds global state
let stateManager: CharacterCreateElements;
