/* Corna frontend network utilities. */

// axios types: https://github.com/axios/axios/blob/v1.x/index.d.ts
import axios from "axios";
import {
    AxiosError,
    AxiosPromise,
    AxiosRequestConfig,
    AxiosResponse,
    RawAxiosRequestHeaders
} from "axios";

import { handlePromise } from "./utils.js";


// return type of handlePromise when making a network request
export type RequestReturnType = [(AxiosError | undefined), (AxiosResponse | undefined)]


/**
 * Return the Corna service URL derived from the current window location.
 *
 * This relies on an application invariant: Corna application code runs either
 * on the root service domain or inside an iframe served from that domain.
 *
 * Do not use this function directly from a themed Corna page. In that context,
 * `window.location` points to the Corna's subdomain rather than the root
 * service domain.
 *
 * @returns { URL } The root Corna service URL.
 */
export function serviceUrl(): URL {
    // for more details on URL object: https://id.javascript.info/url
    return new URL(window.location.origin);
}


/**
 * Return the Corna API URL derived from the current service URL.
 *
 * This relies on the same invariant as `serviceUrl()`: the current window must
 * belong to the root Corna service domain. The API is always expected to be
 * available at the `api` subdomain of that service.
 *
 * For example:
 *   https://testingcorna.test -> https://api.testingcorna.test
 *   https://mycorna.com       -> https://api.mycorna.com
 *
 * Do not use this function directly from a themed Corna page.
 *
 * @returns { string } The Corna API URL.
 */
export function getApiUrl(): string {
    const baseServiceUrl = serviceUrl();
    return `${baseServiceUrl.protocol}//api.${baseServiceUrl.hostname}`;
}


export function request<T>(
    urlExtension: string,
    method: ("get" | "delete" | "post" | "put") = "get",
    payload?: T,
    headers?: RawAxiosRequestHeaders,
    // pass through any other AxiosRequestConfig options when needed without
    // breaking the signature on any pre-existing uses of this function.
    // Also ensure we omit the fields handled by the function e.g. method, headers etc
    extras?: Omit<AxiosRequestConfig, "method" | "url" | "data" | "headers">,
): AxiosPromise {
    /* Generalised requestion function that wraps axios.request.
    *
    * @param { string } urlExtension: the API url extension
    * @param { ("get" | "delete" | "post" | "put") } method:
    *     http method for the request
    * @param { optional<T> } payload: any payload to send
    * @param { optional<AxiosHeaders> } headers: any headers to send
    *     with request
    * @returns { AxiosPromise }
    */

    const url: string = `${getApiUrl()}/${urlExtension}`;
    const requestConf: AxiosRequestConfig = {
        method: method,
        url: url,
        data: payload,
        withCredentials: true,
        headers: headers,
        ...(extras ?? {}),

    }; 
    return axios.request(requestConf);
}


export function handleNetworkError(
    error: AxiosError,
    errorMessage: string = "There was a problem, please try again :(",
): string {
    /* Handle any network errors.
    *
    * @param { AxiosError } error: network error
    * @param { string } errorMessage: a generic error message to be used
    *     in case error does not come with message
    * @return { string }
    */
    let errMsg: string;

    if (error.status && error.status === 422) {
        errMsg = "There is an error on our end, sorry! Please try again."
    }

    else if (error.response) {
        const er: AxiosResponse = error.response;
        errMsg = er.data.message ? er.data.message : errorMessage;
    }

    else {
        errMsg = errorMessage;
    }

    return errMsg;
}


export async function postData<T, E>(
    data: T,
    urlExtension: string,
    errorMessageCallback: (errMsg: string) => E,
    redirectUrlExtension?: string,
    redirectCallback?: (urlExtension: string) => Promise<void>,
): Promise<void> {
    /* Post user data to backend.
    *
    * @param { T } data: user data to send
    * @param { string } urlExtension: the API url extension to call
    * @param { (errMsg: string) => any }: callback for error handling
    * @param { string } redirectUrlExtension: optional redirect url
    * @param { (urlExtension: string) => Promise<void> } redirectCallback:
    *     optional redirect callback (the backend will do the actual
    *     redirect)
    * @returns { Promise<void> }
    */
    await (async () => {
        const [error, response] = await handlePromise(
            request(urlExtension, "post", data))

        if (response && (redirectUrlExtension && redirectCallback)) {
            redirectCallback(redirectUrlExtension)
        }

        else if (error) {
            const errMsg: string = handleNetworkError(error as AxiosError);
            errorMessageCallback(errMsg);
        }
    })();

}
