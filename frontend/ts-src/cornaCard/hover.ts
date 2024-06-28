/* Handle interactions with the actual nav bar. */


interface NavState {

    createOptions: HTMLUListElement;
    hoverEnabled: boolean;

}


function hoverOver(parentNode: HTMLOListElement): void {
    
    if (!state.hoverEnabled) { return; }

    const dot = parentNode.getElementsByClassName("dot") as HTMLCollectionOf<HTMLDivElement>;
    const navLabel = parentNode.getElementsByClassName("navLabel") as HTMLCollectionOf<HTMLDivElement>;

    // there will be at most 1 of each of these
    if (dot.length > 0) {
        dot[0].style.animation = "dotBounceIn 0.5s ease forwards";
        dot[0].style.display = "block";
    }

    if (navLabel.length > 0) {
        navLabel[0].style.animation = "labelBounceIn 0.5s ease forwards";
        navLabel[0].style.display = "block";
    }
}


function hoverOut(parentNode: HTMLOListElement | HTMLUListElement): void {

    if (!state.hoverEnabled) { return; }

    const dot = parentNode.getElementsByClassName("dot") as HTMLCollectionOf<HTMLDivElement>;
    const navLabel = parentNode.getElementsByClassName("navLabel") as HTMLCollectionOf<HTMLDivElement>;

    // there will be at most 1 of each of these
    if (dot.length > 0) {
        dot[0].style.animation = "none";
        dot[0].style.display = "none";
    }
    
    if (navLabel.length > 0) {
        navLabel[0].style.animation = "none";
        navLabel[0].style.display = "none";
    }
}


export function hoverEventListeners(): void {
    const navItems = document.getElementsByClassName("navItem") as HTMLCollectionOf<HTMLOListElement>;
    for (let i = 0; i < navItems.length; i++) {
        const item: HTMLOListElement = navItems[i]
        // for more information on `this` usage here:
        // - https://developer.mozilla.org/en-US/docs/Web/API/EventTarget/addEventListener#the_value_of_this_within_the_handler
        item.addEventListener("mouseenter", function() { hoverOver(this); });
        item.addEventListener("mouseleave", function() { hoverOut(this); });
    }

    state.hoverEnabled = true;
}


export function createOptionsHover(event: MouseEvent, parentNode: HTMLOListElement): void {
    /* handles hovering for "create post" options */

    event.preventDefault();

    // toggle adds or removes the class. More info:
    // - https://developer.mozilla.org/en-US/docs/Web/API/Element/classList
    state.createOptions.classList.toggle("active");

    if (state.createOptions.classList.contains("active")) {
        // remove decoration from nav bar create icon, the prevents
        // overlapping because the nav bar is a tight space
        hoverOut(parentNode);
        state.createOptions.classList.remove("notActive");

        // remove hover event listeners
        state.hoverEnabled = false;
    } else {
        state.createOptions.classList.add("notActive");
        hoverEventListeners();
    }

    event.stopPropagation();
}


/*
* Handle cleaning up create post options on the nav bar if user
* clicks outside of the nav.
*/
export function clickOut(event: MouseEvent): void {
    const clickedOut: boolean = (
        state.createOptions.classList.contains("active")
        && !state.createOptions.contains(event.target as Node)
    )

    if (clickedOut) {
        state.createOptions.classList.remove("active");
        state.createOptions.classList.add("notActive");

        hoverEventListeners();
    }
}


function initState(): NavState {
    const createOptions = document.getElementById("createOptions") as HTMLUListElement;
    const hoverEnabled: boolean = false;

    return {
        createOptions,
        hoverEnabled,
    }
}


const state: NavState = initState();
