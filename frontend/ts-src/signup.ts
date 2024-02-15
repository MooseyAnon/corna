/* Register a new account on Corna.
*
* The UI emulates a terminal based conversation with the "system".
*/

import {
    AxiosError,
    AxiosResponse,
} from "axios";

import {
    handleNetworkError,
    postData,
    request,
} from "./lib/network";

import {
    clean,
    createDivElement,
    createImageElement,
    handlePromise,
    hasCapitalLetter,
    hasDigit,
    hasSpace,
    isEmail,
    spaceAtEnd,
    spaceAtStart,
} from "./lib/utils.js";


enum QuestionKeys {
    /* Object key for each question. */

    ABOUT = "about",
    DOMAINNAME = "domain_name",
    EMAIL = "email_address",
    PASSWORD = "password",
    THEME = "theme",
    TITLE = "title",
    USERNAME = "user_name",
}


interface RegisterConfig {
    /* Registration config interface.
    *
    * Holds the state of the registration process.
    * This is a global object
    */
    blocked: boolean;
    completed: boolean;
    displayUserInput: HTMLDivElement;
    questionIndex: number;
    typingSpeed: number;
    userInput: HTMLInputElement;
    username: SetupQuestion | undefined;
    userResponses: Partial<UserResponses>;
    userTyping: boolean;
}


interface ThemeOption {
    /* For displaying theme options during setup. */

    thumbnail: string;
    name: string;
    creator: string;
    id: string;
    description?: string;
}


interface SetupQuestion {
    /* "System" conversation interface. */

    answer?: string;
    key: string;
    text: string;
}


interface RegisterUser {
    /* Parameters for registering a new user. */

    email_address: string;
    password: string;
    user_name: string;
}


interface CreateCorna {
    /* Parameters for creating a new Corna. */

    about?: string;
    domain_name: string;
    theme_uuid?: string;
    title: string;
}


interface UserResponses extends CreateCorna, RegisterUser {
    /* UserResponses to send to the server. */
}


const questions: SetupQuestion[] = [
    {
        key: "user_name",
        text: "Welcome to Corna, lets get you started by picking a username",
        answer: "",
    },
    {
        key: "email_address",
        text: "Please choose your email address",
        answer: "",
    },
    {
        key: "password",
        text: "Enter an eight character password - include a capital letter and a number",
        answer: "",
    },
    {
        key: "domain_name",
        text: "Pick a domain name for your Corna (you can change this later)",
        answer: "",
    },
    {
        key: "title",
        text: "Give your corna a title (you can change this later)",
        answer: "",
    },
    {
        key: "theme_uuid",
        text: "Please enter the name of your theme (you can change this later)",
        answer: "",
    },
    {
        key: "about",
        text: "Add your bio (you can change this later)",
        answer: "",
    },
];


export function init(): RegisterConfig {
    /* Initialize global object.
    *
    * @returns { RegisterConfig }
    */

    const usernameDetails: string = "username";
    const username: SetupQuestion | undefined = questions.find((q: SetupQuestion) => q.key === usernameDetails);
    const userInput = document.getElementById("userInput") as HTMLInputElement;
    const displayUserInput = document.getElementById("chat-container") as HTMLDivElement;

    return {
        /*
        Dont ask user the next question as they have entered a
        response which is invalid. If blocked === true then
        the next question does not get asked.
        */
        blocked: false,
        /* We can mark as completed when there are no more question to ask. */
        completed: false,
        displayUserInput: displayUserInput,
        questionIndex: 0,
        typingSpeed: 100,
        userInput: userInput,
        username: username,
        /* This will hold the data we are going to post to the backend. */
        userResponses: {},
        userTyping: false,
    };

}


export function nextQuestion(): void {
    /* Ask user next question.
    *
    * @returns { void }
    */
    if (registerConfig.questionIndex < questions.length) {
        const currentQuestion: SetupQuestion = questions[registerConfig.questionIndex];
        displayMessage("system", currentQuestion.text);
    }
    else {
        registerConfig.completed = true;
    }
}


export function processTheme(name: string, id: string): void {

    if (
        registerConfig.questionIndex < questions.length
        && questions[registerConfig.questionIndex].key === "theme_uuid"
    ) {
        questions[registerConfig.questionIndex].answer = id;
        registerConfig.questionIndex++;
    }
    else {
        const themeQuestion: SetupQuestion | undefined = questions.find(
            (q: SetupQuestion) => q.key === "theme_uuid");
        if (themeQuestion) {
            themeQuestion.answer = id;
        }
    }

    updateUserResponses("theme_uuid", id);
    displayMessage("system", `You've chosen ${name}`);
    nextQuestion();
}


export async function processUserInput(): Promise<void> {
    /* Process incoming user input.
    *
    * @returns { void }
    */

    if (registerConfig.questionIndex >= questions.length) { return; }

    const currentQuestion: SetupQuestion = questions[registerConfig.questionIndex];
    const key: string = currentQuestion.key;
    const userReply: string = registerConfig.userInput.value;

    switch(key) {
        case QuestionKeys.EMAIL: {
            const emailAvailable = await emailIsAvailable(clean(userReply))
            registerConfig.blocked = !emailAvailable ? true : !isValidEmail(userReply);
            break;
        }
        case QuestionKeys.USERNAME: {
            const usernameAvailable = await usernameIsAvailable(clean(userReply));
            registerConfig.blocked = !usernameAvailable ? true : !isValidUsername(userReply);
            break;
        }
        case QuestionKeys.PASSWORD: {
            registerConfig.blocked = !isValidPassword(userReply);
            break;
        }
        case QuestionKeys.DOMAINNAME: {
            const domainNameAvailable: boolean = await domainIsAvailable(clean(userReply));
            registerConfig.blocked = !domainNameAvailable ? true : !isValidDomainName(userReply);
            break;
        }
        case QuestionKeys.THEME: {
            break;
        }
        case QuestionKeys.TITLE: {
            break;
        }
        case QuestionKeys.ABOUT: {
            break;
        }
    }

    // we always want to reset these regardless of what happens
    registerConfig.userInput.value = "";
    registerConfig.userTyping = false;  

    if (!registerConfig.blocked) {
        updateUserResponses(key, userReply);

        registerConfig.questionIndex++;
        currentQuestion.answer = userReply;

        displayMessage("user", userReply);
        nextQuestion();
    }

    // send data if we have no more questions to ask
    if (registerConfig.completed) {

        registerNewUser(registerConfig.userResponses as UserResponses);
    }
 
}


export function displayMessage(
    sender: "user" | "system",
    message: string
): void {
    /* Display message to user.
    *
    * @param { "user" | "system" } sender: who sent the message
    * @param { string } message: the message to display
    * @returns { void }
    */

    const username: (SetupQuestion | undefined) = registerConfig.username;
    const answer: string = (username && username.answer) ? username.answer : "user-1";
    const firstLetter: string = answer.charAt(0);

    if (sender === "user") {
        const messageContainer: HTMLDivElement = buildUserReply(message, firstLetter);
        registerConfig.displayUserInput.appendChild(messageContainer);
    }

    else if (sender === "system") {
        typeSystemMessage(message);
    }

}


export function updateUserResponses(field: string, userReply: string): void {
    /* Update the user responses object.
    *
    * @param { string } field: the field to update
    * @param { string } userReply: The users response
    * @returns { void }
    */

    switch(field){
        case QuestionKeys.EMAIL:
        case QuestionKeys.DOMAINNAME:
        case QuestionKeys.USERNAME:
            userReply = clean(userReply);
            break;
        case QuestionKeys.TITLE:
        case QuestionKeys.ABOUT:
            userReply.trim()
            break;
    }
    registerConfig.userResponses[field as keyof UserResponses] = userReply;
}


export function buildUserReply(
    message: string,
    userPrompt: string
): HTMLDivElement {
    /* Build user reply to be displayed.
    *
    * @param { string } message: the message a user responds to the system
    *     questions with.
    * @param { string } userPrompt: the prompt characters to use when displaying
    *     user response
    * @returns { HTMLDivElement }
    */

    const messageContainer: HTMLDivElement = createDivElement(["userReply"]);
    const replyContainer: HTMLDivElement = createDivElement(["user-chat-container"]);

    const logo: HTMLDivElement = createDivElement(["user-logo"], `${userPrompt} >`);
    replyContainer.appendChild(logo);

    const userReply: HTMLDivElement = createDivElement(["reply"]);
    userReply.textContent = message;
    replyContainer.appendChild(userReply);

    messageContainer.appendChild(replyContainer);

    return messageContainer;

}


export async function buildOptions(element: HTMLDivElement): Promise<void> {
    /* Build HTML elements for questions with options.
    *
    * This is needed for multiple choice questions e.g. picking a theme.
    *
    * @returns { HTMLDivElement }
    */
    const options = await themeList() as ThemeOption[];
    const optionsContainer: HTMLDivElement = createDivElement(["theme"]);

    for (let i = 0; i < options.length; i++) {
        const opt: ThemeOption = options[i];

        const singleOption: HTMLDivElement = createDivElement(["theme-option"]);
        singleOption.id = opt.id

        const imgElement: HTMLImageElement = createImageElement([], opt.thumbnail);
        singleOption.appendChild(imgElement);

        const nameElement: HTMLDivElement = createDivElement([], opt.name);
        singleOption.appendChild(nameElement);

        singleOption.addEventListener("click", function(e: MouseEvent) {
            const tar = e.target || e.srcElement;
            (tar as HTMLElement).style.borderColor = "green";
            processTheme(opt.name, opt.id);
        })

        singleOption.addEventListener("mouseover", function(e) {
            const tar = e.target || e.srcElement;
            if ((tar as HTMLElement).style.borderColor !== "green") {
                (tar as HTMLElement).style.borderColor = "red";
            }
        })

        singleOption.addEventListener("mouseout", function(e) {
            const tar = e.target || e.srcElement;
            if ((tar as HTMLElement).style.borderColor !== "green") {
                (tar as HTMLElement).style.borderColor = "white";
            }
        })

        optionsContainer.appendChild(singleOption);
    }
    // return optionsContainer;
    element.appendChild(optionsContainer);
}


export function typeCharacter(
    index: number,
    message: string,
    element: HTMLDivElement,
): void {
    /* Recursively "type" text onto the screen.
    *
    * @param { number } index: the index of the next character to be displayed
    * @param { string } message: The message being displayed
    * @param { HTMLDivElement } element: the element the message is going into
    * @returns { void }
    */

    if (index < message.length && registerConfig.userTyping) {
        /*
        * print everything because user is already typing. If the user
        * presses enter, it will trigger the next question to start being
        * displayed before the previous one is finished. It can lead to
        * some buggy UI behaviour.
        */
        element.textContent += message.slice(index);
        index = message.length;
    }

    else if (index < message.length) {
        // use this to turn settimeout into an async function and pull out options stuff:
        // https://stackoverflow.com/questions/33289726/combination-of-async-function-await-settimeout
        element.textContent += message.charAt(index);
        /*
        * This queues the function to be called later, so its
        * "asyc-lite". This means we currently cant do the options
        * outside of this function coz the setTimeout doesn't complete
        * before the options block gets appended to the parent
        * element, thus fucking everything up.
        * I dont like this, feels like code smell. It should be fixed
        * for now I blame the original author windowcil :D
        */
        setTimeout(
            () => { typeCharacter(index + 1, message, element); },
            registerConfig.typingSpeed
        );
    }

    // display any options from the "system" for the user e.g. themes
    if (index >= message.length && questions[registerConfig.questionIndex].key === "theme_uuid") {
        // const optionsContainer: HTMLDivElement = buildOptions();
        // element.appendChild(optionsContainer);

        buildOptions(element);
    }

}


export function typeSystemMessage(message: string): void {
    /* Display a message from the "system".
    *
    * @param { string } message: the message to display
    * @returns { void }
    */

    const messageContainer: HTMLDivElement = createDivElement(["systemQuestion"]);
    const messageTextElement: HTMLDivElement = createDivElement(["corna-chat-container"]);

    const cornaLogo: HTMLDivElement = createDivElement(["corna-logo"], ":// >");
    messageTextElement.appendChild(cornaLogo);

    // question textbox
    const questionText: HTMLDivElement = createDivElement(["question"]);

    typeCharacter(0, message, questionText)

    messageTextElement.appendChild(questionText);
    messageContainer.appendChild(messageTextElement)
    registerConfig.displayUserInput.appendChild(messageContainer);

}


export function isValidEmail(email: string): boolean {
    /* Validate email.
    *
    * @param { string } email: the email address to validate
    * @returns { boolean }: true if email is valid
    */

    const hasErrd: boolean = !email || !isEmail(clean(email));

    if (hasErrd) {
        displayMessage("system",
            `Oh on! ${email} is invalid. `
            + "Please enter a valid email"
        )
    }
    return !hasErrd;
}


export function isValidUsername(username: string): boolean {
    /* Validate username.
    *
    * @param { string } username: the username to validate
    * @returns { boolean }: true if username is valid
    */

    const hasErrd: boolean = !username || hasSpace(clean(username));

    if (hasErrd) {
        displayMessage("system",
            "Make sure your username does not contain any spaces."
        )
    }
    return !hasErrd;
}


export function isValidDomainName(domainName: string): boolean {
    /* Validate domain name.
    *
    * @param { string } domain name: the domain name to validate
    * @returns { boolean }: true if domain name is valid
    */

    const hasErrd: boolean = !domainName || hasSpace(clean(domainName));

    if (hasErrd) {
        displayMessage("system",
            "Make sure your domain name does not contain any spaces."
        )
    }
    return !hasErrd;
}


export function isValidPassword(
    password: string,
    expectedLength: number = 8
): boolean {
    /* Validate password.
    *
    * @param { string } password: the password to validate
    * @param { number } expectedLength: the expected length of password
    * @returns { boolean }: true if password is valid
    */

    const hasErrd: boolean = (
        !password
        || (password.length < expectedLength)
        || spaceAtStart(password)
        || spaceAtEnd(password)
        || !hasCapitalLetter(password)
        || !hasDigit(password)
    );

    if (hasErrd) {
        displayMessage("system",
            "Oh no, invalid password! Ensure password does not start "
            + "or end with a space, has a capital letter and a number."
        )
    }
    return !hasErrd;
}


export async function usernameIsAvailable(username: string): Promise<boolean> {
    /* Check if a username is available.
    *
    * This allows us to not need to wait till the end of
    * the registration process just to let the user know
    * their chosen username is not available.
    *
    *@param { string } username: username to check availability for
    *@returns { Promise<boolean> }: true, if username is available
    */

    let usernameAvailable: boolean = false;
    let errMsg: string = `Unfortunately '${username}' is taken :(`;

    await (async () => {
        const [error, response] = await handlePromise(
            request(`v1/auth/username/available?username=${username}`)
        ) as [(AxiosError | undefined), (AxiosResponse | undefined)];

        if (response) { usernameAvailable = response.data.available; }
        else if (error) { errMsg = handleNetworkError(error as AxiosError); }
    })();

    if (!usernameAvailable) { displayMessage("system", errMsg); }

    return usernameAvailable;
}


export async function emailIsAvailable(email: string): Promise<boolean> {
    /* Check if an email address is available.
    *
    * This allows us to not need to wait till the end of
    * the registration process just to let the user know
    * their chosen email address is not available.
    *
    * @param { string } email: email to check availability for
    * @returns { Promise<boolean> }: true, if email is available
    */

    let emailAvailable: boolean = false;
    let errMsg: string = `Unfortunately '${email}' is taken :(`;

    await (async () => {
        const [error, response] = await handlePromise(
            request(`v1/auth/email/available?email=${email}`)
        ) as [(AxiosError | undefined), (AxiosResponse | undefined)];

        if (response) { emailAvailable = response.data.available; }
        else if (error) { errMsg = handleNetworkError(error as AxiosError); }
    })();

    if (!emailAvailable) { displayMessage("system", errMsg); }

    return emailAvailable;
}


export async function domainIsAvailable(domainName: string): Promise<boolean> {
    /* Check if a domainName is available.
    *
    * This allows us to not need to wait till the end of
    * the registration process just to let the user know
    * their chosen domainName is not available.
    *
    * @param { string } domainName: domainName to check availability for
    * @returns { Promise<boolean> }: true, if domainName is available
    */

    let isAvailable: boolean = false;
    let errMsg: string = `Unfortunately '${domainName}' is taken :(`;

    await (async () => {
        const [error, response] = await handlePromise(
            request(`v1/corna/domain/available?domain_name=${domainName}`)
        ) as [(AxiosError | undefined), (AxiosResponse | undefined)];

        if (response) { isAvailable = response.data.available; }
        else if (error) { errMsg = handleNetworkError(error as AxiosError); }
    })();

    if (!isAvailable) { displayMessage("system", errMsg); }

    return isAvailable;    
}


export async function themeList(): Promise<ThemeOption[]> {

    let hasErrd: boolean = false;
    let errMsg: string = "There was a problem fetching theme list";

    let themeList: ThemeOption[] = [];

    await (async () => {
        const [error, response] = await handlePromise(
            request("v1/themes")) as [(AxiosError | undefined), (AxiosResponse | undefined)];

        if (response) {
    
            themeList = response.data.themes;
        }
        else if (error) {
            errMsg = handleNetworkError(error as AxiosError);
            hasErrd = true;
        }
    })();

    if (hasErrd) { displayMessage("system", errMsg); }

    return themeList;
}


export async function registerNewUser(userData: UserResponses): Promise<void> {
    /* Register a new user.
    *
    * @param { UserResponses } userData: users details collected from
    *     registration process
    * @returns { Promise<void> }
    */

    await postData({
        user_name: userData.user_name,
        email_address: userData.email_address,
        password: userData.password,
    } as RegisterUser, "v1/auth/register", typeSystemMessage);

    await postData({
        email_address: userData.email_address,
        password: userData.password, 
    },"v1/auth/login", typeSystemMessage);

    await postData({
        title: userData.title,
        theme_uuid: undefined ?? userData.theme_uuid,
        about: undefined ?? userData.about,
    } as CreateCorna, `v1/corna/${userData.domain_name}`, typeSystemMessage);

    await handlePromise(request("v1/auth/logout", "post"));

}


// initialize global object
const registerConfig: RegisterConfig = init();

document.addEventListener("DOMContentLoaded", function() {
    const inputButton = document.getElementById("inputButton") as HTMLButtonElement;
    inputButton.addEventListener("click", function() {
        processUserInput();
    });
    registerConfig.userInput.addEventListener("keydown", function(event: KeyboardEvent) {
        registerConfig.userTyping = true;
        if (event.key === "Enter") {
            processUserInput();
        }
    });
    nextQuestion();
});
