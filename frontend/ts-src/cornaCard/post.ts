/* Handle creating a new user post. */

import { AxiosError, AxiosResponse } from "axios";
import { uploadMediaFile } from "./../lib/media.js"
import { getApiUrl, request, handleNetworkError } from "./../lib/network";
import {
    createImageElement,
    createVideoElement,
    queryRequired,
} from "./../lib/utils";

import { State, initState } from "./../editor.js";

import {
    closeOverlay,
    displayErrorMessage,
    displayStatusMessage,
    resetMessages,
} from "./utils.js";

/**
 * Some typedef's to make post orchestration scale better.
 */
type PostType = "text" | "picture" | "video";


interface FormControls {
    createButton: HTMLDivElement;
    closeButton: HTMLDivElement;
    dropArea: HTMLDivElement;
    inputFile: HTMLInputElement;
    formFields: FormFields;
}


interface FormFields {
    editor: State;
    postTitle: HTMLDivElement;
    uploadedImages: string[];
}


interface StateManager {
    modalRoot: HTMLDivElement;
    cardContainer: HTMLDivElement;
    formControls: FormControls;
    domainName: string;
    postType: PostType;
    sessionId: number;
    isActive: boolean;
}


interface PostData {
    content?: string | null;
    inner_html?: string | null;
    title?: string | null;
    type: string;
    uploaded_images?: string[];
}


interface PostTypeConfig {
    allowedFileKind: "image" | "video";
    maxFiles: number;
    uploadLabel: string;  // used for user-facing messaging
}


const POST_CONFIG: Record<PostType, PostTypeConfig> = {
    text: { allowedFileKind: "image", maxFiles: 1, uploadLabel: "header image" },
    picture: { allowedFileKind: "image", maxFiles: 1, uploadLabel: "image" },
    video: { allowedFileKind: "video", maxFiles: 1, uploadLabel: "video" },
};


/**
 * Map postType -> modal root element id.
 *
 * @param { PostType } postType: the post type being created
 * @returns { string } the modal root id for that post type
 */
function getModalRootId(postType: PostType): string {
    if (postType === "text") return "textModal";
    if (postType === "picture") return "imageModal";
    return "videoModal";
}


/**
 * Get the config for a given post type.
 *
 * @param { PostType } postType: the post type being created
 * @returns { PostTypeConfig } config values for that post type
 */
function getPostConfig(postType: PostType): PostTypeConfig {
    return POST_CONFIG[postType];
}


function filesValid(files: FileList): boolean {
    // let the config object handle the details for each post type.
    // this function shouldn't care.
    const cfg = getPostConfig(stateManager.postType)

    if (files.length > cfg.maxFiles) {
        displayErrorMessage(`Can only upload ${cfg.maxFiles} file per post`);
        return false;
    }

    for (let i = 0; i < files.length; i++) {
        const file: File = files[i];
        const fileType: string = file.type.split("/")[0]

        if (fileType !== cfg.allowedFileKind) {
            displayErrorMessage("Incorrect file type");
            return false;
        }
    }

    return true;
}


function addEventListeners(): void {
    const root = stateManager.modalRoot;

    // Prevent stacking listeners if the same modal is swapped in multiple times.
    if (root.dataset.bound === "1") { return; }
    root.dataset.bound = "1";

    stateManager.formControls.createButton.addEventListener("click", function() {
        resetMessages();
        createPost();
    });

    stateManager.formControls.closeButton.addEventListener("click", function() {
        // Mark inactive so async callbacks don't mutate a closed/swapped modal.
        stateManager.isActive = false;
        resetMessages();
        closeOverlay();
    });

    stateManager.formControls.dropArea.addEventListener("dragover", function(event: DragEvent) {
        event.preventDefault();
    });

    stateManager.formControls.dropArea.addEventListener("drop", function(event: DragEvent) {
        event.preventDefault();
        resetMessages();

        if (event.dataTransfer) {
            mediaFilePreview(event.dataTransfer.files);
        }
    });

    stateManager.formControls.inputFile.addEventListener("change", function() {
        resetMessages();
        mediaFilePreview(stateManager.formControls.inputFile.files);
    });
}


/**
 * Given a urlExtension build an image element to pull it from server.
 * 
 * @param { string } urlExtension: The url of the image
 * @param { string[] } classList: A list of CSS classes to add to new element
 * @returns { HTMLImageElement }
 */
function buildImgTag(
    urlExtension: string,
    classList: string[] = [],
): HTMLImageElement {
    
    const srcUrl: string = `${getApiUrl()}/v1/media/download/${urlExtension}`;
    const img = createImageElement(classList, srcUrl) as HTMLImageElement;

    /* 
    * use url extension as id so we can grab all images again before creating
    * full post. url extension are needed to build DB relationships later on.
    * This also allows us to not have to worry about images being removed during
    * the editing process as we can get all images at once afterwards.
    */
    img.id = urlExtension;
    return img;
}


/**
 * Given a urlExtension build an video element to pull it from server.
 * 
 * @param { string } urlExtension: The url of the video
 * @param { string[] } classList: A list of CSS classes to add to new element
 * @returns { HTMLVideoElement }
 */
function buildVideoTag(
    urlExtension: string,
    classList: string[] = [],
): HTMLVideoElement {
    /* Create video element. */

    const srcUrl: string = `${getApiUrl()}/v1/media/download/${urlExtension}`;
    const video = createVideoElement(srcUrl, classList) as HTMLVideoElement;

    video.id = urlExtension;
    return video;
}


/**
 * Create media file preview.
 * 
 * @param { FileList } files: list of files to create preview for
 * @returns { void }
 */
function mediaFilePreview(files: FileList | null): void {
    if (!files || !filesValid(files)) return;

    const sessionId = stateManager.sessionId;

    const sliderContainer = document.createElement("div") as HTMLDivElement;
    sliderContainer.id = "slider-container";
    sliderContainer.classList.add("slider-container");

    // Clear UI immediately (current behaviour)
    stateManager.formControls.dropArea.innerHTML = "";
    stateManager.formControls.dropArea.appendChild(sliderContainer);

    for (let i = 0; i < files.length; i++) {
        const file: File = files[i];
        const fileType: string = file.type.split("/")[0];

        uploadMediaFile(file)
        .then((response: AxiosResponse) => {
            // Bail if this modal is no longer the active session.
            if (!stateManager.isActive || stateManager.sessionId !== sessionId) { return; }

            const imageData = response.data;
            const urlExtension: string = imageData.url_extension;

            if (fileType === "image") {
                const media = buildImgTag(urlExtension, ["slider-image"]) as HTMLImageElement;
                sliderContainer.appendChild(media);
            } else if (fileType === "video") {
                const media = buildVideoTag(urlExtension, ["slider-video"]) as HTMLVideoElement;
                sliderContainer.appendChild(media);
            }

            stateManager.formControls.formFields.uploadedImages.push(urlExtension);
        })
        .catch((error: AxiosError) => {
            if (!stateManager.isActive || stateManager.sessionId !== sessionId) { return; }
            const errMsg: string = handleNetworkError(error);
            displayErrorMessage(errMsg);
        });
    }
}


/**
 * Try make after post cleanup sexy - thats what she said.
 * 
 * @param { boolean } successful: whether post was successful or not
 * @returns { void }
 */
function afterPostCleanUp(successful: boolean): void {

    setTimeout(() => {
        // this closes the window in an oldschool tv style way - from top to bottom
        stateManager.cardContainer.classList.add("dropped");
    }, 700);

    setTimeout(() => {
        // this removes the entire card after the form (above) as been closed
        stateManager.modalRoot.classList.remove("clicked");
        stateManager.cardContainer.classList.remove("dropped");

        if (successful) {
            // close the modal and overlay if we created post successfully
            closeOverlay();
        }
    }, 1200);
}


/**
 * Get all the info from the post form and return the data ready to b posted.
 * 
 * @returns { PostData } correctly formatted object to post
 */
function parsePostForm(): PostData {
    // this will be typecast to PostData at the end of this function
    const payload: Partial<PostData> = {}
    /*
    * Traditionally you would not want to use innerText because
    * it is less performant than textContent (in some browsers its
    * literally a wrapper around textContent), however, we would like
    * to keep the "layout" properties of the document content because
    * it prevents things like deleting new lines which result in weird
    * word concatenations at the ends of words.
    * As we improve the editor we probably will not need to do this
    * any more but for not it should be fine as this gets called only
    * once during the post creation process.
    */
    const content: string | null = (
        stateManager
        .formControls
        .formFields
        .editor
        .editorConfig
        .modalContent
        .textContent
    );  // this is probs too long - she defo did not say this
    const innerHtml: string | null = (
        stateManager
        .formControls
        .formFields
        .editor
        .editorConfig
        .modalContent
        .innerHTML
    );

    // put in required fields
    payload.type = stateManager.postType;
    payload.uploaded_images = stateManager.formControls.formFields.uploadedImages;

    // We only want to add optional fields if they exist, the backend will handle
    // missing fields.
    const title: string | null = stateManager.formControls.formFields.postTitle.textContent;
    if (title) { payload.title = title; }

    if (innerHtml) {
        // the container is stripped from the `innerHTML` sting so we want to
        // add it back again. This will make displaying content easier later on
        payload.inner_html = `<section>${innerHtml}</section>`;

        // although this could lead to a bug down the road, it would be safe
        // to assume that if innerHTML exists on the container then content will
        // also exist.
        //
        // It may make more sense to invert this assumption *thinks*
        payload.content = content;
    }

    return payload as PostData
}


/* submit post */
function post(): void {
    // get form data
    const payload: PostData = parsePostForm();

    // fail fast
    if (stateManager.postType === "text" && (!payload.content || !payload.inner_html)) {
        resetMessages();
        displayErrorMessage("Text post needs...text ;)");
        afterPostCleanUp(false);
        return;
    }

    const method: ("get" | "delete" | "post" | "put") = "post";
    const headers: { [key: string]: string } = {"Content-Type": "application/json"};
    const urlExtension: string = `v1/posts/${stateManager.domainName}/post`;

    request(urlExtension, method, payload, headers)
    .then((response: AxiosResponse) => {
        if (response.status === 201) {
            displayStatusMessage("Your post was created successfully :)");
            afterPostCleanUp(true);
        }
    })
    .catch((error: AxiosError) => {
        const errMsg: string = handleNetworkError(error);
        afterPostCleanUp(false);
        displayErrorMessage(errMsg);
    })
}


function createPost(): void {
    displayStatusMessage("Please wait whilst the magic happens...");
    stateManager.modalRoot.classList.add("clicked");
    post();
}


function initFormFields(root: HTMLElement): FormFields {
    const editor: State = initState();
    const postTitle = queryRequired<HTMLDivElement>(root, "#modalTitle", "modalTitle");
    const uploadedImages: string[] = [];

    return {
        editor,
        postTitle,
        uploadedImages,
    };
}


function initFormControls(root: HTMLElement): FormControls {
    const createButton = queryRequired<HTMLDivElement>(root, "#createPost", "createPost");
    const closeButton = queryRequired<HTMLDivElement>(root, "#closePost", "closePost");
    const dropArea = queryRequired<HTMLDivElement>(root, "#drop-area", "drop-area");
    const inputFile = queryRequired<HTMLInputElement>(root, "#input-file", "input-file");
    const formFields: FormFields = initFormFields(root);

    return {
        createButton,
        closeButton,
        dropArea,
        inputFile,
        formFields,
    };
}



function init(postType: PostType, domainName_: string): StateManager {
    const rootId = getModalRootId(postType);
    const modalRoot = document.getElementById(rootId) as HTMLDivElement | null;

    if (!modalRoot) {
        throw new Error(`post.ts: modal root not found (#${rootId})`);
    }

    const cardContainer = document.getElementById("cardContainer") as HTMLDivElement;
    const formControls: FormControls = initFormControls(modalRoot);

    return {
        modalRoot,
        cardContainer,
        domainName: domainName_,
        formControls,
        postType,
        sessionId: (stateManager?.sessionId ?? 0) + 1,
        isActive: true,
    };
}



export function createPostTest(postType: string, domainName: string | null): void {
    if (!domainName) return;

    const typedPostType = postType as PostType;

    try {
        stateManager = init(typedPostType, domainName);
        addEventListeners();
    } catch (e) {
        displayErrorMessage("Failed to load post creator. Please try again.");
        // Also surface the real error in dev tools
        console.error(e);  // eslint-disable-line no-console
    }
}


// global state manager
let stateManager: StateManager;
