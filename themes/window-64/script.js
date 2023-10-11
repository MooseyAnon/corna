document.addEventListener("DOMContentLoaded", () => {

  clickListener(document, "clickable-text-element", textModal);
  clickListener(document, "clickable-picture-element", pictureModal);
  clickListener(document, "clickable-folder-element", folderModal);

});


function closeModal(e) {
  e.remove()
}


function folderModal() {
  _ = document.getElementsByClassName("folder-modal")[0];

  const popupWidth = 630; // Width of the modal.
  const popupHeight = 400; // Height of the modal.

  const el = addDisplay(_, popupWidth, popupHeight, ret=true);

  clickListener(el, "clickable-text-element", textModal);
  clickListener(el, "clickable-picture-element", pictureModal);

  document.body.appendChild(el);
}


function textModal() {
  _ = document.getElementsByClassName("text-modal")[0];

  const popupWidth = 630; // Width of the modal.
  const popupHeight = 400; // Height of the modal.
  
  addDisplay(_, popupWidth, popupHeight);
}


function pictureModal() {
  _ = document.getElementsByClassName("picture-modal")[0];

  const popupWidth = 630; // Width of the modal.
  const popupHeight = 400; // Height of the modal.

  addDisplay(_, popupWidth, popupHeight);
}


function addDisplay(el, width, height, ret=false) {

  el = _.cloneNode(true);
  var className = el.className.split(" ")[0];

  el.className = "";
  el.classList.add(className);

  const closeTextModalIcon = el.getElementsByClassName("closeTextModalIcon")[0];
  closeTextModalIcon.addEventListener(
    "click", closeModal.bind(null, el)
  );

  const popupWidth = width; // Width of the modal.
  const popupHeight = height; // Height of the modal.

  const maxX = window.innerWidth - popupWidth;
  const maxY = window.innerHeight - popupHeight;

  const randomX = Math.random() * maxX;
  const randomY = Math.random() * maxY;

  el.style.left = `${randomX}px`;
  el.style.top = `${randomY}px`;

  if (el.style.display !== "flex") { el.style.display = "flex"; }

  // make element draggable
  dragElement(el);

  if (ret) { return el; }

  document.body.appendChild(el);
}


function clickListener(el, className, method) {
  const clickableElement = el.getElementsByClassName(className);

  for (let i = 0; i < clickableElement.length; i++) {
    const element = clickableElement[i];
    element.addEventListener("click", method);
  }
}


function dragElement(elmnt) {
  var pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;

  elmnt.addEventListener("mousedown", dragMouseDown);
  elmnt.addEventListener("touchstart", dragMouseDown);

  function dragMouseDown(e) {
    e = e || window.event;
    e.preventDefault();
    // get the mouse cursor position at startup:
    pos3 = e.clientX;
    pos4 = e.clientY;
    document.onmouseup = closeDragElement;
    // call a function whenever the cursor moves:
    document.onmousemove = elementDrag;
  }

  function elementDrag(e) {
    e = e || window.event;
    e.preventDefault();
    // calculate the new cursor position:
    pos1 = pos3 - e.clientX;
    pos2 = pos4 - e.clientY;
    pos3 = e.clientX;
    pos4 = e.clientY;
    // set the element's new position:
    elmnt.style.top = (elmnt.offsetTop - pos2) + "px";
    elmnt.style.left = (elmnt.offsetLeft - pos1) + "px";
  }

  function closeDragElement() {
    /* stop moving when mouse button is released:*/
    document.onmouseup = null;
    document.onmousemove = null;
  }
}
