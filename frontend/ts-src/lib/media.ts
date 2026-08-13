/* Handle the peculiarities of uploading media files. */

import axios from "axios";
import { AxiosError, AxiosPromise } from "axios";

import { request, RequestReturnType as RRT } from "./network.js";
import { handlePromise } from "./utils.js";


const MAX_SIMPLE_UPLOAD = 20 * 1024 * 1024;      // 20 MB (match Nginx)
const DEFAULT_MAX_FILE_SIZE = 100 * 1024 * 1024; // 100 MB (make 0 to disable)
const DEFAULT_CHUNK_SIZE = 5 * 1024 * 1024;      // 5 MB
const SIMPLE_UPLOAD_URL = "v1/media/upload";
const CHUNK_UPLOAD_URL  = "v1/media/chunk";

const MAX_CHUNK_ATTEMPTS = 4;                   // max attempts to resend chunks before aborting
const CHUNK_RETRY_BASE_DELAY_MS = 500;          // base backoff delay

const RETRYABLE_STATUS_CODES = new Set([
    429,
    500,
    502,
    503,
    504,
]);


interface Opts {
    maxFileSize?: number;                      // bytes; default 100MB. Set 0 to disable limit.
    chunkSize?: number;                        // bytes; default 5MB
    onProgress?: (fraction: number) => void;   // 0..1
    signal?: AbortSignal;                      // to cancel
    extraFormFields?: Record<string, string>;  // e.g. { type: "image" }
    uploadUrl?: string;                        // override simple upload URL when needed
}

/**
 * Upload a file.
 * 
 * This function decides if the file should be chunked or uploaded as a whole.
 * This is largely dependant on the file size. If the file size is larger than
 * 20MB it will be chunked regardless of what file type it is.
 * 
 * @param { File } file: the file to upload
 * @param { object } opts: extra parameters to pass to axios
 * @returns { Promise<void> }
 */
export async function uploadMediaFile(file: File, opts?: Opts) {
    const maxFileSize = opts?.maxFileSize ?? DEFAULT_MAX_FILE_SIZE;

    if (maxFileSize > 0 && file.size > maxFileSize) {
        throw new Error(`File too large (${fmtBytes(file.size)} > ${fmtBytes(maxFileSize)})`);
    }

    let callable: (file: File, opts?: Opts) => AxiosPromise = smallUpload;

    if (file.size > MAX_SIMPLE_UPLOAD) {
        callable = largeUpload;
    }

    return callable(file, opts);
}


/**
 * Uploads a file in a small file upload process.
 * 
 * This function handles the upload of a single file, and optionally accepts 
 * additional options through the `opts` parameter. It returns a promise that 
 * resolves with the result of the Axios HTTP request.
 *
 * @param { File } file - The file to be uploaded.
 * @param { Opts } [opts] - Optional configuration options for the upload process.
 * @returns { AxiosPromise }
 */
async function smallUpload(file: File, opts?: Opts): AxiosPromise {

    const fileType: string = file.type.split("/")[0];
    const method: ("get" | "delete" | "post" | "put") = "post";
    const uploadUrl: string = opts?.uploadUrl ?? SIMPLE_UPLOAD_URL;

    const formData = new FormData();

    formData.append("image", file, file.name);
    formData.append("type", fileType);

    if (opts?.extraFormFields) {
        for (const key in opts.extraFormFields) {
            /* eslint-disable-next-line no-prototype-builtins */
            if (opts.extraFormFields.hasOwnProperty(key)) {
                    formData.append(key, opts.extraFormFields[key]);
            }
        }
    }

    return request<FormData>(uploadUrl, method, formData, undefined, {
        signal: opts?.signal,
        onUploadProgress: (e) => {
            if (opts?.onProgress && e.total) {
                opts.onProgress(e.loaded / e.total);
            }
        }});
}


/**
 * Uploads a large file in chunks to the server and merges them upon completion.
 * 
 * This function handles the upload of large files by dividing them into chunks 
 * and sending them sequentially. It generates a unique upload ID, sends the 
 * chunks, checks the upload status, and eventually merges the uploaded chunks 
 * into a complete file on the server.
 * 
 * **Note**: The function currently does not implement retries with exponential 
 * backoff in case of failure, but this is planned for future improvements.
 *
 * @param { File } file - The large file to be uploaded.
 * @param { Opts } [opts] - Optional configuration options for the upload process, 
 * such as additional headers or parameters.
 * @returns { AxiosPromise } - A promise that resolves to the Axios response after 
 * the merge request has been made, any errors thrown by that are expected to be
 * handled by the caller.
 *
 * @throws { Error } - If an error occurs during the upload or status check, the 
 * function will throw an error with the message from the AxiosError response.
 */
async function largeUpload(file: File, opts?: Opts): AxiosPromise {
    // A stable ID so the server can associate chunks
    const uploadId: string = cryptoRandomId();
    const fileType: string = file.type.split("/")[0];

    // if this errors, the error will bubble up to the caller
    // TODO: This should do retries with exponential backoff!
    // there is a high chance it could get throttled by the rate limiter
    await sendChunks(file, uploadId, opts);

    // check status
    // TODO: if upload is not complete retry and throw error if persists!
    const [error,] = await handlePromise(
        request(`${CHUNK_UPLOAD_URL}/status/${uploadId}`, "get")) as RRT;
    if (error) { throw new Error(error.message); }

    // merge
    return request(`${CHUNK_UPLOAD_URL}/merge`, "post", {
        filename: file.name,
        uploadId: uploadId,
        contentType: fileType,
    });

}


/**
 * Determine whether a failed chunk upload can be safely retried.
 *
 * @param { unknown } error - The error returned by the upload request.
 * @returns { boolean } True if the request should be retried, otherwise false.
 */
function isRetryableChunkError(error: unknown): boolean {
    if (!axios.isAxiosError(error)) {
        return false;
    }

    // Request was cancelled by the caller.
    if (error.code === "ERR_CANCELED") {
        return false;
    }

    // No response means the request failed at the network/transport layer.
    if (!error.response) {
        return true;
    }

    return RETRYABLE_STATUS_CODES.has(error.response.status);
}


/**
 * Parse the Retry-After response header into a delay in milliseconds.
 *
 * Supports both delay-in-seconds and HTTP-date Retry-After values as it
 * can contain either:
 *
 *   Retry-After: 5
 *   Retry-After: Wed, 21 Oct 2015 07:28:00 GMT
 *
 * @param { AxiosError } error - The Axios error containing the response headers.
 * @returns { number | undefined } The retry delay in milliseconds, or undefined
 *     if no valid Retry-After header is present.
 */
function retryAfterMs(error: AxiosError): number | undefined {
    const retryAfter = error.response?.headers?.["retry-after"];

    if (retryAfter === undefined) {
        return undefined;
    }

    const seconds = Number(retryAfter);

    if (Number.isFinite(seconds)) {
        return Math.max(0, seconds * 1000);
    }

    const retryAt = Date.parse(String(retryAfter));

    if (!Number.isNaN(retryAt)) {
        return Math.max(0, retryAt - Date.now());
    }

    return undefined;
}


/**
 * Calculate the delay before retrying a failed chunk upload.
 *
 * Uses the server-provided Retry-After value for rate-limited requests when
 * available, otherwise calculates exponential backoff with jitter.
 *
 * @param { unknown } error - The error returned by the upload request.
 * @param { number } retryNumber - The zero-based retry number.
 * @returns { number } The delay before the next attempt in milliseconds.
 */
function retryDelayMs(error: unknown, retryNumber: number): number {
    if (
        axios.isAxiosError(error)
        && error.response?.status === 429
    ) {
        const serverDelay = retryAfterMs(error);

        if (serverDelay !== undefined) {
            return serverDelay;
        }
    }

    const exponentialDelay = CHUNK_RETRY_BASE_DELAY_MS * (2 ** retryNumber);

    // 75%-125% jitter.
    const jitter = 0.75 + (Math.random() * 0.5);

    return exponentialDelay * jitter;
}


/**
 * Sleep for a specified duration while supporting cancellation.
 *
 * @param { number } ms - The duration to wait in milliseconds.
 * @param { AbortSignal } [signal] - Optional signal used to cancel the wait.
 * @returns { Promise<void> } Resolves once the delay has elapsed.
 *
 * @throws { DOMException } Throws if the operation is aborted.
 */
function sleep(ms: number, signal?: AbortSignal): Promise<void> {
    return new Promise((resolve, reject) => {
        if (signal?.aborted) {
            reject(signal.reason ?? new DOMException(
                "Operation aborted",
                "AbortError",
            ));
            return;
        }

        const timeout = window.setTimeout(() => {
            signal?.removeEventListener("abort", onAbort);
            resolve();
        }, ms);

        const onAbort = (): void => {
            window.clearTimeout(timeout);
            signal?.removeEventListener("abort", onAbort);

            reject(signal?.reason ?? new DOMException(
                "Operation aborted",
                "AbortError",
            ));
        };

        signal?.addEventListener("abort", onAbort, { once: true });
    });
}


/**
 * Upload a single chunk, retrying transient failures with exponential backoff.
 *
 * Requests are retried when they fail due to a network error or return a
 * retryable HTTP status code. If the server returns a 429 response with a
 * Retry-After header, the requested delay is used instead of the calculated
 * backoff.
 *
 * @param { FormData } fd - Form data containing the chunk and its upload metadata.
 * @param { AbortSignal } [signal] - Optional signal used to cancel the upload.
 * @returns { Promise<void> } Resolves once the chunk has been uploaded successfully.
 *
 * @throws { AxiosError } Throws the final request error when retries are exhausted,
 *     the error is not retryable, or the request is cancelled.
 */
async function sendChunkWithRetry(
    fd: FormData,
    signal?: AbortSignal,
): Promise<void> {

    for (let attempt = 0; attempt < MAX_CHUNK_ATTEMPTS; attempt++) {

        const [error,] = await handlePromise(request<FormData>(
            `${CHUNK_UPLOAD_URL}/upload`, "post", fd, undefined, { signal })
        ) as RRT;

        if (!error) {
            return;
        }

        const finalAttempt = attempt === MAX_CHUNK_ATTEMPTS - 1;

        if (finalAttempt || !isRetryableChunkError(error)) {
            throw error;
        }

        const delay = retryDelayMs(error, attempt);

        const [sleepError,] = await handlePromise(sleep(delay, signal));

        if (sleepError) {
            throw sleepError;
        }
    }
}


/**
 * Uploads a file in chunks to the server.
 * 
 * This function splits a file into smaller chunks and uploads each chunk sequentially 
 * to the server. It tracks the number of bytes uploaded and supports optional progress 
 * reporting and additional form fields. The function returns the total number of bytes 
 * uploaded once the process is complete.
 * 
 * **Note**: The function currently does not include retry logic for failed chunk uploads, 
 * but this will be added in the future.
 *
 * @param { File } file - The file to be uploaded in chunks.
 * @param { string } uploadId - A unique ID for the upload session, used to group the chunks together.
 * @param { Opts } [opts] - Optional configuration options:
 *   - `opts.chunkSize`: The size of each chunk in bytes (defaults to `DEFAULT_CHUNK_SIZE`).
 *   - `opts.extraFormFields`: Additional form fields to include in the request for each chunk.
 *   - `opts.signal`: An AbortSignal to cancel the upload.
 *   - `opts.onProgress`: A callback function that receives the progress (between 0 and 1) as the file is uploaded.
 * @returns { Promise<number> } - A promise that resolves to the total number of bytes uploaded.
 * 
 * @throws { Error } - Throws an error if any chunk upload fails, with the message from the Axios response.
 */
async function sendChunks(
    file: File,
    uploadId: string,
    opts?: Opts,
): Promise<number> {
    const chunkSize = opts?.chunkSize ?? DEFAULT_CHUNK_SIZE;
    const totalChunks: number = Math.ceil(file.size / chunkSize);

    let uploadedBytes: number = 0;

    for (let chunkIndex = 0; chunkIndex < totalChunks; chunkIndex++) {
        const start: number = chunkIndex * chunkSize;  // offset
        const end: number = Math.min(start + chunkSize, file.size);
        const blob = file.slice(start, end);

        const fd = new FormData();

        fd.append("chunk", blob, `${file.name}.part${chunkIndex}`);
        fd.append("chunkIndex", String(chunkIndex));
        fd.append("totalChunks", String(totalChunks));
        fd.append("uploadId", uploadId);

        if (opts?.extraFormFields) {
            for (const key in opts.extraFormFields) {
                /* eslint-disable-next-line no-prototype-builtins */
                if (opts.extraFormFields.hasOwnProperty(key)) {
                    fd.append(key, opts.extraFormFields[key]);
                }
            }
        }

        await sendChunkWithRetry(fd, opts?.signal);

        uploadedBytes += blob.size;

        opts?.onProgress?.(uploadedBytes / file.size);
    }

    return uploadedBytes;
}

/* ---------- utilities ---------- */

function cryptoRandomId(): string {
    // RFC4122-ish UUID using Web Crypto if available
    if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
        return crypto.randomUUID();
    }
    // uuid only lives on the server for the duration of the upload, so we can
    // make a unique-ish number up here
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
        const r = (Math.random() * 16) | 0; // fallback
        const v = c === "x" ? r : (r & 0x3) | 0x8;
        return v.toString(16);
    });
}


/**
 * Converts a byte value to a human-readable file size string.
 * 
 * This function formats a given number of bytes into a more readable format with 
 * appropriate units such as "KB", "MB", or "GB". It uses powers of 1024 to convert 
 * bytes into higher units and returns the result as a string with one decimal place.
 * 
 * @param {number} n - The number of bytes to be converted to a human-readable format.
 * @returns {string} - A string representing the file size in the most appropriate unit 
 * (B, KB, MB, GB), with one decimal place.
 */
function fmtBytes(n: number): string {
    const units = ["B", "KB", "MB", "GB"];

    let i = 0; let v = n;
    while (v >= 1024 && i < units.length - 1) {
        v /= 1024; i++; 
    }
    return `${v.toFixed(1)} ${units[i]}`;
}
