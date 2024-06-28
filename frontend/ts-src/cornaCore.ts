/* Core JS script that will be injected into each Corna. */

import { createDivElement, createIframeElement } from "./lib/utils.js";


document.addEventListener("DOMContentLoaded", function() {
    /* Create iframe on page load. */
    const frameContainer = createDivElement(["frameContainer"]) as HTMLDivElement;
    const frameSrc: string = "https://mycorna.com/nav";
    const frame = createIframeElement(frameSrc) as HTMLIFrameElement;
    frameContainer.appendChild(frame);
    document.body.appendChild(frameContainer);

    // Listen to messages from the iframe
    window.addEventListener("message", function(e) {
        if (e.data === "open") {
            frame.classList.add("enlargeIframe");
        } else if (e.data === "close") {
            frame.classList.remove("enlargeIframe");
        } else if (e.data.includes("domainName")) {

            const domainName: string = e.data.split("=")[1];
            const currHref: string = window.location.href;
            // we only want to follow the link if user is not already
            // on their own corna.
            if (!currHref.includes(domainName)) {
                const href: string = `https://${domainName}.mycorna.com`;
                window.location.href = href;
            }
        }
    })
});
