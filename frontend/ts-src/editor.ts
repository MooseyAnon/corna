/*
* Corna Rich Text Editor.
* 
* This is the first version of Corna's rich text editor, the core features
* its supports (via the toolbar) are:
*     - insert image (centred block)
*     - insert link (to highlighted text)
*     - bold/italic/underlined (to highlighted text)
*     - bullet point list
*     - numbered list
*     - left/centre/right align text
*     - insert headers and subheaders (H1 - H3)
*     - Change test colour
*
* While there are still some platform related issues (e.g. paste on MacOS uses
* command button and not ctrl), for now it achieves all basic features on
* most broswers.
*/

import { AxiosError, AxiosPromise, AxiosResponse } from "axios";
import { getApiUrl, request, handleNetworkError } from "./lib/network";
import { createElement, createImageElement, handlePromise } from "./lib/utils";

interface ToolBar {
    /* Toolbar elements */

    boldButton: HTMLButtonElement;
    bulletButton: HTMLButtonElement;
    centreAlignedButton: HTMLButtonElement;
    colorInput: HTMLInputElement;
    italicButton: HTMLButtonElement;
    leftAlignedButton: HTMLButtonElement;
    linkButton: HTMLButtonElement;
    numberedButton: HTMLButtonElement;
    pictureButton: HTMLInputElement;
    rightAlignedButton: HTMLButtonElement;
    typefaceOption: NodeListOf<HTMLOptionElement>;
    underlineButton: HTMLButtonElement;
}


interface EditorConfig {
    /* Global editor configuration */

    modalContent: HTMLDivElement;
    toolBar: ToolBar;
} 


export interface State {
    /* Holds the state of the editor. */

    previousKey: string;
    previousRange: Range | null;
    uploadedImages: string[];
    editorConfig: EditorConfig;
}


export function handleIndents(e: KeyboardEvent): void {

    const selection = window.getSelection() as Selection;
    const range = selection.getRangeAt(0) as Range;
    const lineNode = range.commonAncestorContainer as Node;

    if (e.key === "Tab" && e.shiftKey) {
        e.preventDefault();

        if (selection.rangeCount > 0) {
            let currentIndent: number = parseInt(
                /*
                * we could have used `parentElement` here instead of casting
                * to HTMLElement, however there are some weird edge cases with
                * parentElement that could lead to very confusing bugs that are
                * not worth the hassle of dealing with. More info here:
                * - https://stackoverflow.com/q/8685739
                */
                (lineNode.parentNode as HTMLElement).style.marginLeft, 10) || 0;

                currentIndent = Math.max(currentIndent - 20, 0);

            (lineNode.parentNode as HTMLElement).style.marginLeft = `${currentIndent}px`; 
        }
    }

    else if (e.key === "Tab") {
        e.preventDefault();

        if (selection.rangeCount > 0) {
            let currentIndent: number = parseInt(
                (lineNode.parentNode as HTMLElement).style.marginLeft, 10) || 0;

            currentIndent += 20;

            (lineNode.parentNode as HTMLElement).style.marginLeft = `${currentIndent}px`;
        }
    }

    state.previousRange = range;
}


export function parseTitle(): string | null {
    /* Attempt to file title for post. */

    const h1ElementList = state.editorConfig.modalContent.getElementsByTagName("h1") as HTMLCollectionOf<HTMLHeadingElement>;
    const title: string | null = h1ElementList.length > 0 ? h1ElementList[0].textContent : null;

    return title;
}


export function parseImageExtension(): string[] {
    /* Grab the IDs of all images on the page. */

    const imgList = state.editorConfig.modalContent.getElementsByTagName("img") as HTMLCollectionOf<HTMLImageElement>;
    const urlExtensionList: string[] = []

    for (let i = 0; i < imgList.length; i++) {
        if (imgList[i].id) {
            urlExtensionList.push(imgList[i].id);
        }
    }

    return urlExtensionList;
}


export async function getDomainName(): Promise<string | null> {

    let domainName: string | null = null;

    await (async () => {
        const [error, response] = await handlePromise(
            request("v1/corna")
        ) as [(AxiosError | undefined), (AxiosResponse | undefined)]; 

        if (response) {
            domainName = response.data.domain_name;
        }
        else if (error) {
            const errMsg: string = handleNetworkError(error);
            state.editorConfig.modalContent.textContent = errMsg;
        }
    })();
    return domainName;
}


export function toggleTextDecoration(style: string | undefined): boolean {
    /* Add or remove text decoration from selected range */

    let success: boolean = false;

    if (style === undefined) { return success; }

    try {

        success = document.execCommand(style, false);
    }

    catch (e) {
        console.error("Error with execCommand: ", e);  // eslint-disable-line no-console
    }

    if (!success) {
        console.error(  // eslint-disable-line no-console
            "Unable able to toggle style, execCommand not supported. "
            + "Attempted to toggle to: ", style);
    }

    return success;
}


export function inverseHighlight(element: HTMLElement): void {
    /* Toggle toolbar element highlighting. */

    const backgroundColor: string | undefined = element.style.backgroundColor;

    if (!backgroundColor || backgroundColor === "transparent") {
        element.style.backgroundColor = "#ececec";
    }

    else {
        element.style.backgroundColor = "transparent";
    }
}


export function bold(): void {
    /* Toggle bold on and off for selected range. */

    const toggled: boolean = toggleTextDecoration("bold");

    if (toggled) {
        inverseHighlight(state.editorConfig.toolBar.boldButton);
    }
}


export function ul(): void {
    /* Insert unordered list i.e. bullets. */

    toggleTextDecoration("insertUnorderedList");
}


export function ol(): void {
    /* Insert ordered list i.e. numbered list. */

    toggleTextDecoration("insertOrderedList");
}


export function justify(direction: "right" | "center" | "left"): void {
    /* Justify text right, center or left. */

    const insert: string = `justify${direction.charAt(0).toUpperCase()}${direction.slice(1)}`;
    toggleTextDecoration(insert);
}


export function italic(): void {
    /* Toggle italic on and off for selected range. */

    const toggled: boolean = toggleTextDecoration("italic");

    if (toggled) {
        inverseHighlight(state.editorConfig.toolBar.italicButton);
    }

}


export function underline(): void {
    /* Toggle underline on and off for selected range. */

    const toggled: boolean = toggleTextDecoration("underline");

    if (toggled) {
        inverseHighlight(state.editorConfig.toolBar.underlineButton);
    }
}


export function currentSelection(): Selection | null {
    /* Get current window selection. */

    let selection: Selection | null = null;

    if (window.getSelection) {
        selection = window.getSelection();
    }

    return selection;
}


export function currentRange(): Range | null {
    /* Get the current selected range. */

    const selection: Selection | null = currentSelection();
    let range: Range | null = null;

    if (selection && selection.getRangeAt && selection.rangeCount) {
        range = selection.getRangeAt(0) as Range;
    }

    return range;
}


export function createAnchorelement(
    href: string,
    target: string = "_blank",
    classList: string[] = [],
    text?: string
): HTMLAnchorElement {
    /* Create a new anchor tag. */

    const newAnchor = createElement("a", classList) as HTMLAnchorElement;
    newAnchor.href = href;
    newAnchor.target = target;

    if (text) {
        newAnchor.text = text;
    }

    return newAnchor;
}


export function changeColor(color: string | undefined): void {

    if (color === undefined) { return; }

    document.execCommand("foreColor", false, color);
}



export function link(): void {
    /* Add link to selected range. */

    const url: string | null = prompt("Enter your link here:", "https://www.");
    
    if (!url) {
        return;
    }

    const range: Range | null = currentRange();

    if (!range) {
        return;
    }

    const anchor = createAnchorelement(url) as HTMLAnchorElement;
    const clone = range.cloneContents() as DocumentFragment;

    /*
    * There is a bug here. If the child already contains an anchor tag
    * we can get weird behaviour with overlapping anchors and anchor
    * tags being recursively added to body (not sure why).
    *
    * The simplest solution is to ignore adding the new url if there is
    * already an anchor tag inside the range. This can be done by looking
    * at the childNodes of the clone or running querySelectorAll("a")
    * and seeing if the array.length > 0.
    *
    * While it would be relatively straight forward to overwrite an anchor
    * tag, the issue comes when the selection boundaries overlap i.e. selection
    * two overlaps with a part of the document which already contains a link.
    * Even when manually writing HTML it is not common to an anchor inside an
    * anchor because the user experience doesn't even make sense.
    *
    * Moreover, most users tend to select a small portion of text when adding
    * a link (usually one or two words at most), it is not particularly
    * rude of us (lol) to require users to manually back out of a link but
    * removing and rewriting a word when they fuck it up *shrug*.
    */

    if (clone.querySelectorAll("a").length > 0) {
        return;
    }

    anchor.appendChild(clone);
    range.deleteContents();
    range.insertNode(anchor);

    state.previousRange = range;
}


export function fileFromInput(): File | null {
    /* Grab file from input. */

    const input = state.editorConfig.toolBar.pictureButton as HTMLInputElement;
    let file: File | null = null;

    if (input.files) {
        file = input.files[0];
    }

    return file
}


export function uploadImage(image: File): AxiosPromise {
    /* Make image upload request to server. */

    const urlExtension: string = "v1/media/upload";
    const method: ("get" | "delete" | "post" | "put") = "post";
    const payload: { image: File } = { image: image };
    const headers: { [key: string]: string } = { "Content-Type": "multipart/form-data" };
    
    return request(urlExtension, method, payload, headers);

}


export function BuildImgTag(urlExtension: string): HTMLImageElement {
    /* Given a urlExtension build an image element to pull it from server. */
    
    const srcUrl: string = `${getApiUrl()}/v1/media/download/${urlExtension}`;
    const img = createImageElement([], srcUrl) as HTMLImageElement;

    /* 
    * use url extension as id so we can grab all images again before creating
    * full post. url extension are needed to build DB relationships later on.
    * This also allows us to not have to worry about images being removed during
    * the editing process as we can get all images at once afterwards.
    */
    img.id = urlExtension;

    // make image thumbnail size so it does not take up all the space in the
    // editor.
    img.width = 480;
    img.height = 270;

    // we want the display to always be block and the img to be aligned center
    img.style.margin = "auto";
    img.style.display = "block";

    return img;

}


export function insertImage() {
    /* Insert an image. */

    const file: File | null = fileFromInput();

    if (!file) {
        return;
    }

    uploadImage(file)
    .then((response: AxiosResponse) => {
        const imageData = response.data;
        const urlExtension: string = imageData.url_extension;
        const img = BuildImgTag(urlExtension) as HTMLImageElement;
        // we need to focus into the editor otherwise the image will
        // get added in some random place on the screen
        state.editorConfig.modalContent.focus();
        // get insert location from range

        if (state.previousRange) {
            state.previousRange.insertNode(img);        
        }

        else {
            const range: Range | null = currentRange();
            if (range) {
                range.insertNode(img);
                state.previousRange = range;
            }
        }
    })
    .catch((e: AxiosError) => {
        const errMsg: string = handleNetworkError(e);
        console.error(errMsg);  // eslint-disable-line no-console
    })

}

export function initToolbar(): ToolBar {

    const boldButton = document.getElementById("bold") as HTMLButtonElement;
    const italicButton = document.getElementById("italic") as HTMLButtonElement;
    const underlineButton = document.getElementById("underline") as HTMLButtonElement;
    const bulletButton = document.getElementById("bullet") as HTMLButtonElement;
    const numberedButton = document.getElementById("numbered") as HTMLButtonElement;
    const leftAlignedButton = document.getElementById("leftAligned") as HTMLButtonElement;
    const centreAlignedButton = document.getElementById("centreAligned") as HTMLButtonElement;
    const rightAlignedButton = document.getElementById("rightAligned") as HTMLButtonElement;
    const pictureButton = document.getElementById("picture") as HTMLInputElement;
    const linkButton = document.getElementById("link") as HTMLButtonElement;
    const typefaceOption = document.querySelectorAll(".selectTypeface") as NodeListOf<HTMLOptionElement>;
    const colorInput = document.getElementById("colorInput") as HTMLInputElement;

    return {
        boldButton,
        bulletButton,
        centreAlignedButton,
        colorInput,
        italicButton,
        leftAlignedButton,
        linkButton,
        numberedButton,
        pictureButton,
        rightAlignedButton,
        underlineButton,
        typefaceOption,
    }

}


export function initEditor(): EditorConfig {

    const modalContent = document.getElementById("modalDescription") as HTMLDivElement;

    const toolBar: ToolBar = initToolbar();

    return {
        modalContent,
        toolBar,
    }

}


function addEventListeners(): void {
    // toolbar event listners
    state.editorConfig.toolBar.boldButton.addEventListener("click", bold);
    state.editorConfig.toolBar.italicButton.addEventListener("click", italic);
    state.editorConfig.toolBar.underlineButton.addEventListener("click", underline);
    state.editorConfig.toolBar.bulletButton.addEventListener("click", ul);
    state.editorConfig.toolBar.numberedButton.addEventListener("click", ol);
    state.editorConfig.toolBar.pictureButton.addEventListener("change", insertImage);
    state.editorConfig.toolBar.linkButton.addEventListener("click", link);
    state.editorConfig.toolBar.leftAlignedButton.addEventListener("click", () => { justify("left"); });
    state.editorConfig.toolBar.centreAlignedButton.addEventListener("click", () => { justify("center"); });
    state.editorConfig.toolBar.rightAlignedButton.addEventListener("click", () => { justify("right"); });
    state.editorConfig.toolBar.colorInput.addEventListener("change", () => {
        changeColor(state.editorConfig.toolBar.colorInput.value);
    });
    // H1, H2, H3 and P selectors
    state.editorConfig.toolBar.typefaceOption.forEach((button: HTMLOptionElement) => {
        button.addEventListener("change", () => {
            document.execCommand(button.id, false, button.value);
        });
    });
    // text area event listener
    state.editorConfig.modalContent.addEventListener("keydown", (e: KeyboardEvent) => {
        handleIndents(e);
    });

}


function init(): State {

    const editorConfig: EditorConfig = initEditor();
    // const domainName: string | null = await getDomainName();

    return {
        /*
        * When adding an image users have to click the "Add Image" icon which
        * causes the caret to disappear (I think there may be a fix for this but
        * I have not figured it out). The default location of the insertion seems
        * to be the top left hand corner of the editor. In order to stop this and
        * add the image to wherever the caret was most recently placed we need to
        * save the most recent range and use that as the location to create the
        * image tag, rather than the default location. There may be better ways to
        * do this but currently, this works pretty well.
        */
        previousRange: null,
        uploadedImages: [],
        /*
        * On macs the command key (keyCode: 'Meta') is the special key used to
        * things like copy/paste. Simultaneously clicking ctrl + <some-other-key>
        * is free in the browser because each press comes with a ctrlKey boolean
        * which lets us know if they ctrl key was also pressed during the KeyEvent.
        * We dont get any such behaviour for MacOS keybindings so we need to take
        * care of the manually. As such knowing the last key press is useful.
        *
        * This is only a temp solution (hacky) as we will add platform specific
        * functionality in the future which will take care of these differences.
        */
        previousKey: "",
        editorConfig: editorConfig,
    }

}


export function initState(): State {
    state = init();
    addEventListeners();

    return state;
}

// // holds the global state of the editor during its lifetime
let state: State;
