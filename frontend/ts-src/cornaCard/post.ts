/* Handle creating a new user post. */

import { AxiosError, AxiosPromise, AxiosResponse } from "axios";
import { getApiUrl, request, handleNetworkError } from "./../lib/network";
import {
    createImageElement,
    createVideoElement,
} from "./../lib/utils";

import { State, initState } from "./../editor.js";

import {
    closeOverlay,
    displayErrorMessage,
    displayStatusMessage,
    resetMessages,
} from "./utils.js";


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
    bodyLargeContainer: HTMLCollectionOf<HTMLDivElement>;
    cardContainer: HTMLDivElement;
    formControls: FormControls;
    domainName: string;
    postType: string;
}


interface PostData {
    content: string | null;
    inner_html: string | null;
    title: string| null;
    type: string;
    uploaded_images: string[];
}


function filesValid(files: FileList): boolean {

    if (files.length > 1) {
        displayErrorMessage("Can only upload 1 file per post");
        return false;
    }

    let isValid: boolean = true;

    for (let i = 0; i < files.length; i++) {
        const file: File = files[i];
        const fileType: string = file.type.split("/")[0]

        isValid = (
            (stateManager.postType === "text" && fileType === "image")
            || (stateManager.postType === "picture" && fileType === "image")
            || (stateManager.postType === "video" && fileType === "video")
        )

        // fail fast
        if (!isValid) {
            displayErrorMessage("Incorrect file type");
            return isValid;
        }
    }

    return isValid;
}


function addEventListeners(): void {

    stateManager.formControls.createButton.addEventListener("click", function() {
        resetMessages();
        createPost();
    });

    stateManager.formControls.dropArea.addEventListener("dragover", function(event: DragEvent) {
        event.preventDefault();
    });

    stateManager.formControls.dropArea.addEventListener("drop", function(event: DragEvent) {
        event.preventDefault();
        resetMessages();

        if (event.dataTransfer){
            imagePreview(event.dataTransfer.files);
        }
    });

    stateManager.formControls.inputFile.addEventListener("change", function() {
        // reset
        resetMessages()
        imagePreview(stateManager.formControls.inputFile.files);
    });
}


function buildImgTag(
    urlExtension: string,
    classList: string[] = [],
): HTMLImageElement {
    /* Given a urlExtension build an image element to pull it from server. */
    
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


function uploadImage(image: File): AxiosPromise {
    /* Make image upload request to server. */

    const fileType: string = image.type.split("/")[0]
    const urlExtension: string = "v1/media/upload";
    const method: ("get" | "delete" | "post" | "put") = "post";
    const payload: { image: File, type: string } = { image: image, type: fileType };
    const headers: { [key: string]: string } = { "Content-Type": "multipart/form-data" };
    
    return request(urlExtension, method, payload, headers);

}


function imagePreview(files: FileList | null): void {
    if (!files || !filesValid(files)) {
        return;
    }

    const sliderContainer = document.createElement("div") as HTMLDivElement;
    sliderContainer.id = "slider-container";
    sliderContainer.classList.add("slider-container");

    for (let i = 0; i < files.length; i++) {
        const file: File = files[i];
        const fileType: string = file.type.split("/")[0]

        uploadImage(file)
        .then((response: AxiosResponse) => {
            const imageData = response.data;
            const urlExtension: string = imageData.url_extension;

            // const is block scoped so we can only use it inside the block
            // hence why we're repeating some code
            if (fileType === "image") {
                const media = buildImgTag(urlExtension, ["slider-image"]) as HTMLImageElement;
                sliderContainer.appendChild(media);

            } else if (fileType === "video") {
                const media = buildVideoTag(urlExtension, ["slider-video"]) as HTMLVideoElement;
                sliderContainer.appendChild(media);
            }

            stateManager.formControls.formFields.uploadedImages.push(urlExtension);
        })
    }

    stateManager.formControls.dropArea.innerHTML = "";
    stateManager.formControls.dropArea.appendChild(sliderContainer);
}


function afterPostCleanUp(successful: boolean): void {

    setTimeout(() => {
        stateManager.cardContainer.classList.add("dropped");
    }, 700);

    setTimeout(() => {
        stateManager.bodyLargeContainer[0]!.classList.remove("clicked");
        stateManager.cardContainer.classList.remove("dropped");

        if (successful) {
            // close the modal and overlay if we created post successfully
            closeOverlay();
        }
    }, 1200);
}


function post(): void {
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
    const content: string | null = stateManager.formControls.formFields.editor.editorConfig.modalContent.textContent;
    const innerHtml: string | null = stateManager.formControls.formFields.editor.editorConfig.modalContent.innerHTML;

    if (stateManager.postType === "text" && (!content || !innerHtml)) {
        resetMessages();
        displayErrorMessage("Text post needs...text ;)");
        afterPostCleanUp(false);
        return;
    }

    // the container is stripped from the `innerHTML` sting so we want to
    // add it back again. This will make displaying content easier later on
    const inner_html: string | null = innerHtml ? `<section>${innerHtml}</section>` : null;
    const title: string | null = stateManager.formControls.formFields.postTitle.textContent;
    const uploaded_images: string[] = stateManager.formControls.formFields.uploadedImages;
    const type: string = stateManager.postType;

    const payload: PostData = {
        content,
        inner_html,
        title,
        type,
        uploaded_images,
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
    stateManager.bodyLargeContainer[0]!.classList.add("clicked");
    post();
}


function initFormFields(): FormFields {
    const editor: State = initState();
    const postTitle = document.getElementById("modalTitle") as HTMLDivElement;
    const uploadedImages: string[] = [];

    return {
        editor,
        postTitle,
        uploadedImages,
    }
}


function initFormControls(): FormControls {

    const createButton = document.getElementById("createPost") as HTMLDivElement;
    const closeButton = document.getElementById("closePost") as HTMLDivElement;
    const dropArea = document.getElementById("drop-area") as HTMLDivElement;
    const inputFile = document.getElementById("input-file") as HTMLInputElement;
    const formFields: FormFields = initFormFields();

    return {
        createButton,
        closeButton,
        dropArea,
        inputFile,
        formFields
    }
}


function init(type: string, domainName_: string): StateManager {
    // these are outside of the form, they the parent containers of the form
    const bodyLargeContainer = document.getElementsByClassName(
        "bodyLargeContainer") as HTMLCollectionOf<HTMLDivElement>
    const cardContainer = document.getElementById("cardContainer") as HTMLDivElement;
    const formControls: FormControls = initFormControls();
    const domainName: string = domainName_;
    const postType: string = type;

    return {
        bodyLargeContainer,
        cardContainer,
        domainName,
        formControls,
        postType,
    }

}


export function createPostTest(postType: string, domainName: string | null): void {
    if (!domainName) { return; }

    stateManager = init(postType, domainName as string);
    addEventListeners();
}


// global state manager
let stateManager: StateManager;
