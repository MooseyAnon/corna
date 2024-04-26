window.onload = function () {
  adjustImageSize();
  window.addEventListener("resize", adjustImageSize);
};

window.addEventListener("resize", adjustImageSize);

function adjustImageSize() {
  console.log("adjust window");
  var image = document.getElementById("image");
  var container = document.getElementById("image-container");
  var overlay = document.getElementById("overlay");

  var svgOverlay = document.getElementById("svg-overlay");
  console.log("the SVG widht");
  if (image && container && image.complete) {
    console.log(
      "This is the image width " +
        image.naturalWidth +
        "this is the clientWidth " +
        container.clientWidth
    );
    console.log(
      "This is the image heigh " +
        image.naturalHeight +
        "this is the height " +
        container.clientHeight
    );

    var imageAspectRatio = image.naturalWidth / image.naturalHeight;
    var containerAspectRatio = container.clientWidth / container.clientHeight;
    console.log(
      "This is the image ratios " +
        imageAspectRatio +
        "this is the client ratio " +
        containerAspectRatio
    );

    console.log(image.naturalWidth);
    console.log(image.naturalHeight);

    if (
      image.naturalWidth > image.naturalHeight &&
      imageAspectRatio > containerAspectRatio &&
      containerAspectRatio > 0.2
    ) {
      console.log("should be 100% width");
      image.style.width = "100vw";
      image.style.height = "auto";
    }
    if (
      image.naturalWidth > image.naturalHeight &&
      imageAspectRatio > containerAspectRatio
    ) {
      console.log("should be 100% height");
      image.style.width = "auto";
      image.style.height = "100vh";
    }
    if (
      image.naturalWidth > image.naturalHeight &&
      imageAspectRatio < containerAspectRatio
    ) {
      console.log("should be 100% width");
      image.style.width = "100vw";
      image.style.height = "auto";
    }
    console.log(image.width);
    // svgOverlay.setAttribute("width", image.width);
    // svgOverlay.setAttribute("height", image.height);
    overlay.style.width = image.width + "px";
    overlay.style.height = image.height + "px";
    // console.log(svgOverlay.width);
  }
}
