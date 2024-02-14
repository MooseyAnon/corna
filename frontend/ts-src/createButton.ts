/* Button that will live on each Corna. */

document.addEventListener("DOMContentLoaded", function() {
    const createButton = document.getElementById("openPage") as HTMLDivElement;
    createButton.addEventListener("click", function(e) {
        e.preventDefault();
        window.open("/editor");
    });
});
