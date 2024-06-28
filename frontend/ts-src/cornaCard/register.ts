/* Handle registration. */

import {
    RequestReturnType as RRT,
    handleNetworkError,
    postData,
    request,
} from "./../lib/network.js";

import {
    clean,
    createDivElement,
    createImageElement,
    handlePromise,
    hasCapitalLetter,
    hasDigit,
    hasSpace,
    isEmail,
    spaceAtStart,
    spaceAtEnd
} from "./../lib/utils.js";

import {
    displayErrorMessage,
    resetMessages,
} from "./utils.js";


interface RegisterConfig {
    blocked: boolean;
    domainName: HTMLInputElement;
    email: HTMLInputElement;
    hasScrolled: boolean;
    password: HTMLInputElement;
    selectedAvatar: string | null;
    selectedThemeUUID: string | undefined;
    themeDetailsSection: HTMLDivElement;
    themeGallery: HTMLDivElement;
    title: HTMLInputElement;
    username: HTMLInputElement;

}


/**
 * Holds base user details when creating an account
 */
interface UserDetails {
    username: string;
    email: string;
    password: string;
}


/**
 * For displaying theme options during setup.
 */
interface ThemeOption {
    thumbnail: string;
    name: string;
    creator: string;
    id: string;
    description?: string;
}


/* ------------------------ general ------------------------ */

/**
 * For scrolling to various parts of the registration form.
 * 
 * The way the registration process currently works users fill in a section
 * and then, if information is valid, we move onto the next section. The main
 * reason we do this is so we can give users as much feedback as possible
 * without having them wait till the end of the registration process.
 * 
 * @param { HTMLButtonElement } parentNode: reference to the parent container
 *      which is used to show or hide certain parts of the form.
 * @returns { void }
 */
function scrollTo(parentNode: HTMLButtonElement): void {
    const registerButton = document.getElementById("Register") as HTMLButtonElement;
    registerButton.addEventListener("click", async function() {
        // register theme selection
        await createCorna();
    });

    registerButton.style.display = "block"
    parentNode.style.display = "none";

    regConf.themeDetailsSection.style.display = "flex";
    regConf.themeDetailsSection.style.opacity = "1";
    regConf.themeDetailsSection.scrollIntoView({ behavior: "smooth", block: "start" });

    regConf.hasScrolled = true;
}


/* ------------------------ validation ------------------------ */

/**
 * Validate username.
 *
 * @param { string } username: the username to validate
 * @returns { boolean }: true if username is valid
 */
function isValidUsername(username: string | null): boolean {

    const hasErrd: boolean = !username || hasSpace(clean(username));

    if (hasErrd) {
        displayErrorMessage("Make sure your username does not contain any spaces.")
    }
    return !hasErrd;
}


/**
 * Validate user email.
 *
 * @param { HTMLInputElement | null } email: email to validate
 * @returns { booloan }
 */
function isValidEmail(email: string | null): boolean {
    // very basic check, server side will do most of the checking
    const hasErrd: boolean = !email || !isEmail(clean(email));

    if (hasErrd) { displayErrorMessage("Please enter a valid email address"); }

    return !hasErrd
}


/**
 * Validate user password.
 *
 * @param { HTMLInputElement | null } password: password to validate
 * @returns { booloan }
 */
function isValidPassword(
    password: string | null,
    expectedLength: number = 8,
): boolean {
    const hasErrd: boolean = (
        !password
        || (password.length < expectedLength)
        || spaceAtStart(password)
        || spaceAtEnd(password)
        || !hasCapitalLetter(password)
        || !hasDigit(password)
    );

    if (hasErrd) {
        displayErrorMessage(
             "Oh no, invalid password! Ensure password has at least "
            + `${expectedLength} characters, a capital letter and a number.`
        )
    }
    return !hasErrd
}


/**
 * Validate domain name.
 *
 * @param { string } domain name: the domain name to validate
 * @returns { boolean }: true if domain name is valid
 */
function isValidDomainName(domainName: string): boolean {
    const hasErrd: boolean = !domainName || hasSpace(clean(domainName));

    if (hasErrd) {
        displayErrorMessage(
            "Make sure your domain name does not contain any spaces.")
    }
    return !hasErrd;
}


/**
 * Check if some field e.g. username, domain is available.
 * 
 * @param { string } url: the avilability check URL
 * @returns { Promise<boolean> }: the result of the check
 */
async function isAvailable(url: string): Promise<boolean> {

    let available: boolean = false;
    const [error, response] = await handlePromise(request(url)) as RRT;

    if (response) {
        available = response.data.available;
    } else if (error) {
        const errMsg = handleNetworkError(error);
        displayErrorMessage(errMsg);
    }

    return available;
}


/**
 * Check if a username is available.
 *
 * This allows us to not need to wait till the end of
 * the registration process just to let the user know
 * their chosen username is not available.
 *
 * @param { string } username: username to check availability for
 * @returns { Promise<boolean> }: true, if username is available
 */
async function usernameIsAvailable(username: string): Promise<boolean> {
    const checkUrl: string = `v1/auth/username/available?username=${username}`;
    const errMsg: string = `Unfortunately '${username}' is taken :(`;
    const usernameAvailable: boolean = await isAvailable(checkUrl);

    if (!usernameAvailable) {
        displayErrorMessage(errMsg);
    }

    return usernameAvailable;
}


/**
 * Check if an email address is available.
 *
 * This allows us to not need to wait till the end of
 * the registration process just to let the user know
 * their chosen email address is not available.
 *
 * @param { string } email: email to check availability for
 * @returns { Promise<boolean> }: true, if email is available
 */
async function emailIsAvailable(email: string): Promise<boolean> {
    const checkUrl: string = `v1/auth/email/available?email=${email}`;
    const emailAvailable: boolean = await isAvailable(checkUrl);
    const errMsg: string = `Unfortunately '${email}' is taken :(`;

    if (!emailAvailable) {
        displayErrorMessage(errMsg);
    }

    return emailAvailable;
}


/**
 * Check if a domainName is available.
 *
 * This allows us to not need to wait till the end of
 * the registration process just to let the user know
 * their chosen domainName is not available.
 *
 * @param { string } domainName: domainName to check availability for
 * @returns { Promise<boolean> }: true, if domainName is available
 */
async function domainIsAvailable(domainName: string): Promise<boolean> {
    const checkUrl: string = `v1/corna/domain/available?domain_name=${domainName}`;
    const errMsg: string = `Unfortunately '${domainName}' is taken :(`;
    const available: boolean = await isAvailable(checkUrl);

    if (!available) {
        displayErrorMessage(errMsg);
    }

    return available;    
}


/* ------------------------ themes ------------------------ */

/**
 * Build theme selection options.
 */
async function themeSelection(): Promise<void> {
    const themes = await themeList() as ThemeOption[];

    for (let i = 0; i < themes.length; i++) {
        const theme: ThemeOption = themes[i];

        const thumbnail: HTMLImageElement = createImageElement(["theme"], theme.thumbnail);
        thumbnail.alt = theme.description ?? "";

        const themeSelector: HTMLDivElement = createDivElement(["themeSelector"]);
        themeSelector.addEventListener("click", function() {
            selectTheme(theme.id, this);
        });

        // build theme container
        const themeContainer: HTMLDivElement = createDivElement(["themeContainer"]);

        themeContainer.appendChild(themeSelector);
        themeContainer.appendChild(thumbnail);
        regConf.themeGallery.appendChild(themeContainer);

    }
}


/**
 * Get list of theme options from the server.
 * 
 * @returns { Promise<ThemeOptions[]> }: list of theme options.
 */
async function themeList(): Promise<ThemeOption[]> {

    let themeList: ThemeOption[] = [];

    const [error, response] = await handlePromise(request("v1/themes")) as RRT;

    if (response) {
        themeList = response.data.themes;
    } else if (error) {
        const errMsg = handleNetworkError(error);
        displayErrorMessage(errMsg);
    }

    return themeList;
}


/**
 * Theme selection logic.
 * 
 * @param { string } themeUUID: The uuid of the selected theme
 * @param { HTMLDivElement } parentNode: the parent node of the current element
 *      This is to allow us to change the styling of the element.
 * @returns { void }
 */
function selectTheme(themeUUID: string, parentNode: HTMLDivElement): void {
    regConf.selectedThemeUUID = themeUUID;
    // unselect any other selections
    const allSelectors = document.getElementsByClassName("themeSelector") as HTMLCollectionOf<HTMLDivElement>;
    for (let i = 0; i < allSelectors.length; i++) {
        const selector: HTMLDivElement = allSelectors[i]
        selector.style.background = ""
    }
    // we only want out current selection to be shown
    parentNode.style.background = "white";
}


/**
 * Get a random user avatar from the server.
 * 
 * @returns { Promise<{ url: string, slug: string }> }: details for an avatar.
 */
async function getAvatar(): Promise<{ url: string, slug: string }> {

    const avatar: { url: string, slug: string } = { "url": "", "slug": "" }
    // request a random avatar
    const [error, response] = await handlePromise(request("v1/media/avatar")) as RRT;

    if (response) {
        const serverData: { url: string, slug: string } = response.data;
        avatar.url = serverData.url;
        avatar.slug = serverData.slug;

    } else if (error) {
        const errMsg = handleNetworkError(error);
        displayErrorMessage(errMsg);
    }

    return avatar;
}


/**
 * Display user avatar
 */
function displayAvatar(src: string): void {
    const avatar = document.getElementById("avatar") as HTMLImageElement;
    avatar.src = src;
}


/**
 * Create a new user Corna.
 * 
 * We post Corna user details to the server and redirect user to their homepage.
 * 
 * @returns { Promise<void> }
 */
async function createCorna(): Promise<void> {

    const validDomain = (
        isValidDomainName(regConf.domainName.value)
        && domainIsAvailable(regConf.domainName.value)
    )

    // validation code takes care of error messaging
    if (!validDomain) { return; }

    if (!regConf.selectedThemeUUID) {
        displayErrorMessage("You must select a theme!");
        return;
    }

    // we need to log user in before creating corna
    await postData({
        email: regConf.email.value,
        password: regConf.password.value, 
    },"v1/auth/login", displayErrorMessage);

    await postData({
        title: regConf.title.value,
        theme_uuid: regConf.selectedThemeUUID,
        about_me: "this is a placeholder",
    }, `v1/corna/${regConf.domainName.value}`, displayErrorMessage);

    // send message to parent page for handling redirect.
    window.parent.postMessage(`domainName=${regConf.domainName.value}`);
}


/**
 * Register user details.
 * 
 * @returns { Promise<void> }
 */
async function userRegister(): Promise<void> {

    const validEmail: boolean = (
        isValidEmail(regConf.email.value)
        && await emailIsAvailable(regConf.email.value)
    )
    const validUsername: boolean = (
        isValidUsername(regConf.username.value)
        && await usernameIsAvailable(regConf.username.value)
    )
    regConf.blocked = (
        !validEmail
        || !validUsername
        || !isValidPassword(regConf.password.value)
    );

    if (regConf.blocked) { return; }

    await postData({
        avatar: regConf.selectedAvatar,
        username: regConf.username.value,
        email: regConf.email.value,
        password: regConf.password.value,
    } as UserDetails, "v1/auth/register", displayErrorMessage);

}


/**
 * Initialize global state manager
 * 
 * @returns { RegisterConfig }
 */
function initState(): RegisterConfig {
    const username = document.getElementById("usernameInput") as HTMLInputElement;
    const email = document.getElementById("emailInput") as HTMLInputElement;
    const password = document.getElementById("passwordInput") as HTMLInputElement;
    const themeDetailsSection = document.getElementById("themeDetails") as HTMLDivElement;
    const themeGallery = document.getElementById("themeGallery") as HTMLDivElement;
    const domainName = document.getElementById("urlInput") as HTMLInputElement;
    const title = document.getElementById("tabtitleInput") as HTMLInputElement;

    const hasScrolled: boolean = false;
    const blocked: boolean = false;
    const selectedThemeUUID: string | undefined = undefined;
    const selectedAvatar: string | null = null;

    return {
        blocked,
        domainName,
        email,
        hasScrolled,
        password,
        selectedAvatar,
        selectedThemeUUID,
        themeDetailsSection,
        themeGallery,
        title,
        username,
    }
}


/**
 * Process new user.
 * 
 * This is the entry point used by external consumers when registering a new
 * user.
 */
export async function processNewUser(): Promise<void> {
    // init the conf here because we need to do it at HTMX swap time not
    // at import time, which will cause it to be empty
    regConf = initState();

    // we want to show an avatar when the user starts the registration process
    const avatar: { url: string, slug: string } = await getAvatar();
    displayAvatar(avatar.url);

    // set selected avatar here
    regConf.selectedAvatar = avatar.slug;

    // build theme options
    await themeSelection();

    const nextToThemeButton = document.getElementById("nextToTheme") as HTMLButtonElement;
    nextToThemeButton.addEventListener("click", async function() {
        resetMessages();
        await userRegister();
        if (!regConf.blocked) {
            scrollTo(this);
        }
    })

}

// global variable that will be initialised when the page
// is swapped in by HTMX
let regConf: RegisterConfig;
