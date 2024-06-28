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


function character() {

    stateManager.characterNameInput.value = "";
    stateManager.chosenIdentifer.textContent = "";
    stateManager.skills.forEach((skill) => {
        skill.classList.remove("activeSelection");
    });

    // Listen to the characterName
    stateManager.characterNameInput.addEventListener("input", function () {
        this.value;
    });

    // skills event listeners
    stateManager.skills.forEach((skill: HTMLDivElement) => {
        skill.addEventListener("click", function () {
            if (this.classList.contains("activeSelection")) {
                this.classList.remove("activeSelection");
                const index = stateManager.selectedSkills.indexOf(this.textContent!);
                if (index !== -1) {
                    stateManager.selectedSkills.splice(index, 1);
                }
            } else {
                stateManager.selectedSkills.push(skill.textContent!);
                this.classList.add("activeSelection");
            }
        });
    });
}


function addEventListeners() {
    stateManager.createCharacterButton.addEventListener("click", submitCharacter);
    //Allow for selection of identifier and highlight the selected one
    stateManager.identifierOptions.forEach((option) => {
        option.addEventListener("click", function () {
            stateManager.chosenIdentifer.textContent = option.textContent;
            option.classList.add("activeSelection");

            stateManager.identifierOptions.forEach((otherOption) => {
                if (otherOption !== option) {
                    otherOption.classList.remove("activeSelection");
                }
            });
        });
    });
}


function submitCharacter() {

    // clear any messages
    resetMessages();

    const data = {
        "domain_name": stateManager.domainName,
        "name": stateManager.characterNameInput.value,
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
    if (!domainName) { return; }

    stateManager = elementsInit(domainName as string);
    addEventListeners();
    character();
}

// holds global state
let stateManager: CharacterCreateElements;
