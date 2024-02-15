/* Core JS script that will be injected into each Corna. */

import {
    AxiosError,
    AxiosResponse,
} from "axios";

import { request } from "./lib/network.js";

import { handlePromise, createIframeElement } from "./lib/utils.js";


interface LoginCheck {
    /* Login check response. */

    is_loggedin: boolean;
}


export async function loginCheck(): Promise<string> {
    /* Check if user is logged in. */

    let defaultSrc: string = "https://mycorna.com/loginButton";
    await (async () => {
        const [, response] = await handlePromise(
            request("v1/auth/login_status")
        ) as [(AxiosError | undefined), (AxiosResponse | undefined)];

        if (response) {
            const checkRes: LoginCheck = response.data;
            if (checkRes.is_loggedin) {
                defaultSrc = "https://mycorna.com/createButton";
            }
        }
    })();

    return defaultSrc;
}


document.addEventListener("DOMContentLoaded", async function() {
    /* Create iframe on page load. */
    const frameSrc: string = await loginCheck();
    const frame = createIframeElement(frameSrc, ["openeditor"]) as HTMLIFrameElement;
    document.body.appendChild(frame);
});
