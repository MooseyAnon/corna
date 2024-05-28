let subdomain = null;

document.addEventListener("DOMContentLoaded", () => {
  const domainList = window.location.hostname.split(".", 1);

  if (domainList.length > 0) {
    subdomain = domainList[0];
  }


  // clickListener(document, "clickable-text-element", textModal);
  clickListener(document, "post-container", pictureModal);
  // clickListener(document, "clickable-folder-element", folderModal);

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


function textModal(e) {
  e.preventDefault();
  const href = e.target.id;

  if (!subdomain) {
    console.error("SUBDOMAIN IS NULL!!");
    return;
  }

  const url = `https://${subdomain}.mycorna.com/fragment/${href}`

  axios({
    method: "get",
    url: url,
    withCredentials: true,
  })
  .then((response) => {
    json = response.data;
    let modal = createModal(json);

    const popupWidth = 630; // Width of the modal.
    const popupHeight = 400; // Height of the modal.

    const maxX = window.innerWidth - popupWidth;
    const maxY = window.innerHeight - popupHeight;

    const randomX = Math.random() * maxX;
    const randomY = Math.random() * maxY;

    modal.style.left = `${randomX}px`;
    modal.style.top = `${randomY}px`;

    if (modal.style.display !== "flex") { modal.style.display = "flex"; }

    const closeTextModalIcon = modal.getElementsByClassName("closeTextModalIcon")[0];
    closeTextModalIcon.addEventListener(
      "click", closeModal.bind(null, modal)
    );

    // make element draggable
    dragElement(modal);

    document.body.appendChild(modal);
  })
}


function createElement(type, classList = []) {
  const newEl = document.createElement(type);
  if (classList) {
    newEl.classList.add(...classList);
  }

  return newEl;
}


function createModal(data) {

  console.log(data)
  console.log("|||||||||")
  // create html element from our string so we can manipulate it
  let new_div = document.createElement("div")
  new_div.innerHTML = data.content

  // ----------- text container --------------
  let newImgContainer = document.createElement("div")
  newImgContainer.classList.add("text-image-container");

  let imgFromBackend = new_div.getElementsByTagName("img")
  if (imgFromBackend.length > 0) {
    imgFromBackend[0].classList.add("text-banner");
    newImgContainer.appendChild(imgFromBackend[0])
  } else {
    let img = document.createElement("img")
    img.src = "./static/windowcil-98/images/Dummyimage.jpg";
    img.classList.add("text-banner");

    newImgContainer.appendChild(img);
  }

  let article = document.createElement("div");
  article.classList.add("article");

  article.appendChild(newImgContainer);

  let backendH1 = new_div.getElementsByTagName("h1")
  if (backendH1.length > 0) {
    article.appendChild(backendH1[0])
  }
  article.appendChild(new_div);

  let textContainer = document.createElement("div");
  textContainer.classList.add("modal-text-content-container");
  textContainer.appendChild(article);

  // -------------- modal nav buttons ---------------------
  let closeBtn = document.createElement("p")
  closeBtn.classList.add("modal-nav-close-icon", "closeTextModalIcon");
  closeBtn.id = "closeTextModalIcon";
  closeBtn.innerHTML = "&times;";

  let modalNav = document.createElement("div");
  modalNav.classList.add("modal-navigation");
  modalNav.appendChild(closeBtn);

  // -------- modal display bar image -------------
  let cornerImg = document.createElement("img");
  cornerImg.classList.add("modal-icon")
  cornerImg.src = "./static/windowcil-98/images/Text.png"

  let modalTitle = document.createElement("div");
  modalTitle.classList.add("modal-title");
  modalTitle.appendChild(cornerImg);

  if (data.title) {
    let title = document.createElement("p");
    title.textContent = data.title;

    modalTitle.appendChild(title);
  }

  let headerContainer = document.createElement("div");
  headerContainer.classList.add("modal-header-container");
  headerContainer.appendChild(modalTitle);
  headerContainer.appendChild(modalNav)

  let modal = document.createElement("div");
  modal.classList.add("text-modal");
  modal.appendChild(headerContainer);
  modal.appendChild(textContainer);

  return modal
}


function pictureModal(el) {
  // _ = document.getElementsByClassName("picture-modal")[0];
  let uuidLong = null;
  console.log(el.classList)
  for (let i = 0; i < el.classList.length; i++) {
    className = el.classList[i];
    if (className.includes("uuid_")) {
      uuidLong = className;
    }
  }
  console.log(uuidLong);
  if (!uuidLong) {
    console.error("Unable to find modal to open");
    return;
  }
  
  uuid = uuidLong.split("_")[1];

  let modEl = document.getElementById(uuid);

  const popupWidth = 630; // Width of the modal.
  const popupHeight = 400; // Height of the modal.

  addDisplay(modEl, popupWidth, popupHeight);
}


function addDisplay(el, width, height, ret=false) {

  el = el.cloneNode(true);
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
    element.addEventListener("click", function() {
      console.log(this);
      method(this);
    });
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
