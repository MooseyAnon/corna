/* Core JS script that will be injected into each Corna. */

import { createDivElement, createIframeElement } from "./lib/utils.js";

let enlarged: boolean = false;
const allowedOrigin: string = "https://mycorna.com"; // adjust if needed

document.addEventListener("DOMContentLoaded", function() {
    /* Create iframe on page load. */
    const frameContainer = createDivElement(["frameContainer"]) as HTMLDivElement;
    const frameSrc: string = "https://mycorna.com/nav?mode=fragment";
    const frame = createIframeElement(frameSrc) as HTMLIFrameElement;
    frameContainer.appendChild(frame);
    document.body.appendChild(frameContainer);

    // Listen to messages from the iframe
    window.addEventListener("message", function(e) {
        // Only accept messages from the nav iframe origin
        if (e.origin !== allowedOrigin) { return; }

        const data = typeof e.data === "string" ? e.data : "";

        if (data === "open") {
            if (enlarged) { return; }
            frame.classList.add("enlargeIframe");
            enlarged = true;

        } else if (data === "close") {
            if (!enlarged) { return; }
            frame.classList.remove("enlargeIframe");
            enlarged = false;

        } else if (data.startsWith("domainName=")) {
            const domainName: string = data.split("=")[1]?.trim();
            if (!domainName) { return; }

            const currHref: string = window.location.href;

            if (!currHref.includes(domainName)) {
                const href: string = `https://${domainName}.mycorna.com`;
                window.location.href = href;
            }
        }
    });
});
