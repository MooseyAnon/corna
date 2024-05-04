window.onload = function () {
  adjustImageSize();
  window.addEventListener("resize", adjustImageSize);
};


window.addEventListener("resize", adjustImageSize);

const frame1 = document.getElementById("frame1");
const frame2 = document.getElementById("frame2");
const frame3 = document.getElementById("frame3");
const frame4 = document.getElementById("frame4");
const frame5 = document.getElementById("frame5");
const frame6 = document.getElementById("frame6");
const frame7 = document.getElementById("frame7");
const frame8 = document.getElementById("frame8");
const frame9 = document.getElementById("frame9");
const frame10 = document.getElementById("frame10");

frame1.addEventListener("click", openArt);
frame2.addEventListener("click", openArt);
frame3.addEventListener("click", openArt);
frame4.addEventListener("click", openArt);
frame5.addEventListener("click", openArt);
frame6.addEventListener("click", openArt);
frame7.addEventListener("click", openArt);
frame8.addEventListener("click", openArt);
frame9.addEventListener("click", openArt);
frame10.addEventListener("click", openArt);

function openArt() {
  location.href = "artDetails.html";
}

function adjustImageSize() {
  console.log("adjust window");
  var image = document.getElementById("image");
  var container = document.getElementById("image-container");
  var overlay = document.getElementById("overlay");

  var svgOverlay = document.getElementById("svg-overlay");
  console.log("the SVG widht");
  if (image && container && image.complete) {
    var imageAspectRatio = image.naturalWidth / image.naturalHeight;
    var containerAspectRatio = container.clientWidth / container.clientHeight;
    if (
      image.naturalWidth > image.naturalHeight &&
      imageAspectRatio > containerAspectRatio &&
      containerAspectRatio > 0.2
    ) {
      image.style.width = "100vw";
      image.style.height = "auto";
    }
    if (
      image.naturalWidth > image.naturalHeight &&
      imageAspectRatio > containerAspectRatio
    ) {
      image.style.width = "auto";
      image.style.height = "100vh";
    }
    if (
      image.naturalWidth > image.naturalHeight &&
      imageAspectRatio < containerAspectRatio
    ) {
      image.style.width = "100vw";
      image.style.height = "auto";
    }
    overlay.style.width = image.width + "px";
    overlay.style.height = image.height + "px";
  }
}
