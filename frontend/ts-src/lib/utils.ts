/* Utility functions. */


export function isEmail(email: string): boolean {
    /* Very, very basic greedy email regex.
    *
    * stolen from: https://stackoverflow.com/a/4964766
    * Essentially here we are testing for the following:
    *    - '@' symbol has at least 1 char before it
    *    - '@' symbol has at least 1 char after it
    *    - '.' (period) has at least one char after it (although might omit this
    *      or at least make it optional)
    *
    * @param { string } email: the email being checked
    * @returns { boolean }
    */

    const regex: RegExp = /^\S+@\S+\.\S+$/;
    return regex.test(email);
}


export function spaceAtStart(str: string): boolean {
    /* Check for space at the start of a string. 
    *
    * Spaces are allowed inside passwords but not at the start or
    * end because this can lead to subtle issues where users
    * accidentally add a space before/after the password without
    * realising.
    *
    * @param { string } str: the string being checked
    * @returns { boolean }
    */

    const regex: RegExp = /^\s+/;
    return regex.test(str)
}


export function spaceAtEnd(str: string): boolean {
    /* Check for space at the end of a string. 
    *
    * Spaces are allowed inside passwords but not at the start or
    * end because this can lead to subtle issues where users
    * accidentally add a space before/after the password without
    * realising.
    *
    * @param { string } str: the string being checked
    * @returns { boolean }
    */

    const regex: RegExp = /\s+$/;
    return regex.test(str)
}


export function hasSpace(str: string): boolean {
    /* Check if a string contains any space characters.
    *
    * @param { string } str: the string being checked
    * @returns { boolean }
    */

    const regex: RegExp = /\s/;
    return regex.test(str);
}


export function hasCapitalLetter(str: string): boolean {
    /* Ensure a string has at least one capital letter.
    *
    * @param { string } str: the string to check against
    * @return { boolean }
    */

    const regex: RegExp = /[A-Z]/;
    return regex.test(str);
}


export function hasDigit(str: string): boolean {
    /* Ensure a string has at least one numerical digit.
    *
    * @param { string } str: the string to check against
    * @return { boolean }
    */

    const regex: RegExp = /\d/;
    return regex.test(str);
}


export function clean(str: string): string {
    /* Make string lower case and remove spaces at start and end.
    *
    * @param { string } str: the string being cleaned
    * @returns { string }
    */

    return str.toLowerCase().trim();
}


// html element list:
// https://microsoft.github.io/PowerBI-JavaScript/interfaces/_node_modules_typedoc_node_modules_typescript_lib_lib_dom_d_.htmlelement.html
export function createElement(
    type: string,
    classList: string[] = []
): HTMLElement {
    /* HTML create factory. 
    *
    * Callers need to cast to the appropriate element type.
    *
    * @param { string } type: the type of html element to make
    *     e.g. 'div', 'img', 'input' etc
    * @param { string[] } classList: optional CSS classes to add
    *     to the new element
    * @returns { HTMLElement }
    */

    const newElement = document.createElement(type) as HTMLElement;
    if (classList) { newElement.classList.add(...classList); }
    return newElement;
}


export function createDivElement(
    classList: string[] = [],
    textContent?: string
): HTMLDivElement {
    /* Create a new div element.
    *
    * @param { string[] } classList: CSS classes to add to new element
    * @param { string } textContent: Optional textContent to add to
    *     the new element
    * @returns { HTMLDivElement }
    */

    const newDiv = createElement("div", classList) as HTMLDivElement;
    if (textContent) { newDiv.textContent = textContent; }
    return newDiv;
}


export function createImageElement(
    classList: string[] = [],
    src?: string
): HTMLImageElement {
    /* Create a new img element.
    *
    * @param { string[] } classList: CSS classes to add to new element
    * @param { string } src: image source href
    * @returns { HTMLImageElement }
    */

    const newImage = createElement("img", classList) as HTMLImageElement;
    if (src) { newImage.src = src; }
    return newImage;
}


export function createIframeElement(
    src: string,
    classList: string[] = [],
): HTMLIFrameElement {
    /* Create a new iframe element.
    *
    * @param { string } src: iframe source href
    * @param { string[] } classList: CSS classes to add to new element
    * @returns { HTMLIFrameElement }
    */
    const newIframe = createElement("iframe", classList) as HTMLIFrameElement;
    newIframe.src = src;
    newIframe.frameBorder = "0";  // remove all borders
    return newIframe
}


// This is copied from here:
// - https://github.com/tysoncadenhead/cartesian-js/blob/master/src/handle.ts
export function handlePromise<E, T>(
    promise: Promise<unknown>
): Promise<[E, T]> {
    /* Generalised promise handling.
    *
    * @param { Promise<unknown> } promise
    * @returns { Promise<[E, T]> }
    */

    return promise
    .then((data) => Promise.resolve([undefined, data]) as Promise<[E, T]>)
    .catch((error) => Promise.resolve([error, undefined]) as Promise<[E, T]>);
}
