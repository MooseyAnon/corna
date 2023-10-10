document.addEventListener("DOMContentLoaded", () => {
  const clickableTextElements = document.querySelectorAll(
    ".clickable-text-element"
  );

  clickableTextElements.forEach((element) => {
    element.addEventListener("click", openTextModal);
  });
  const clickablePictureElements = document.querySelectorAll(
    ".clickable-picture-element"
  );

  clickablePictureElements.forEach((element) => {
    element.addEventListener("click", openPictureModal);
  });

  const clickableFolderElements = document.querySelectorAll(
    ".clickable-folder-element"
  );

  clickableFolderElements.forEach((element) => {
    element.addEventListener("click", openFolderModal);
  });
});

function openTextModal() {
  console.log("I have been clicked");
  const textModal = document.createElement("div");
  textModal.classList.add("text-modal");
  textModal.style.display = "flex";
  textModal.innerHTML = `
    <div class="modal-header-container">
        <div class="modal-title">
            <img src = "./images/Text.png" alt="Minimize" class="modal-icon"/>
            <p>This is the modal title</p>
        </div>
        <div class="modal-navigation">
            <p class="modal-nav-minimise-icon">__</p>
            <p class="modal-nav-close-icon" id="closeTextModalIcon" alt="close">&times;</p>
        </div>
    </div>
    <div class="modal-text-content-container">
        <div class="article">
        <div class="text-image-container"><img src="./images/Dummyimage.jpg" class="text-banner"></div>
        <h1>Title of this article</h1>
        <p>It is a long established fact that a reader will be distracted by the readable content of a page when looking at its layout. The point of using Lorem Ipsum is that it has a more-or-less normal distribution of letters, as opposed to using 'Content here, content here', making it look like readable English. Many desktop publishing packages and web page editors now use Lorem Ipsum</p>
        </div>
    </div>`;

  const popupWidth = 630; // Width of the modal.
  const popupHeight = 400; // Height of the modal.

  const maxX = window.innerWidth - popupWidth;
  const maxY = window.innerHeight - popupHeight;

  const randomX = Math.random() * maxX;
  const randomY = Math.random() * maxY;

  textModal.style.left = `${randomX}px`;
  textModal.style.top = `${randomY}px`;

  document.body.appendChild(textModal);
  const closeTextModalIcon = textModal.querySelector("#closeTextModalIcon");
  closeTextModalIcon.addEventListener(
    "click",
    closeTextModal.bind(null, textModal)
  );
}

function closeTextModal(modal) {
  modal.remove();
}

function openPictureModal() {
  console.log("Picture modal");
  const pictureModal = document.createElement("div");
  pictureModal.className = "picture-modal";
  pictureModal.style.display = "flex";
  pictureModal.innerHTML = `
  <div class="modal-header-container">
  <div class="modal-title">
      <img src = "./images/Inverted-picture.png" alt="Minimize" class="modal-icon"/>
      <p>This is a picture modal</p>
  </div>
  <div class="modal-navigation">
      <p class="modal-nav-minimise-icon">__</p>
      <p class="modal-nav-close-icon" id="closePictureModalIcon" alt="close">&times;</p>
  </div>
</div>
<div class="modal-picture-content-container">
<img src = "./images/Imageplaceholder.avif" alt="main image" class="picture-container"/>
</div>
<div class="pallette">
  <div class="selectedColour">
      <div class="backgroundcolour"></div>
      <div class="pickedcolour"></div>
  </div>
  <div class="colourPallette">
      <div style="background-color: aqua; box-shadow: inset 3px 3px 0px 0px rgb(43 43 43); border-radius: 1px; border: 2px outset #929292; width: 32px;"></div>                                                                                                                        
      <div style="background-color: darkblue; box-shadow: inset 3px 3px 0px 0px rgb(43 43 43); border-radius: 1px; border: 2px outset #929292;"></div>                                                                                                                        
      <div style="background-color: darkcyan; box-shadow: inset 3px 3px 0px 0px rgb(43 43 43); border-radius: 1px; border: 2px outset #929292;"></div>                                                                                                                                            
      <div style="background-color: darkgoldenrod; box-shadow: inset 3px 3px 0px 0px rgb(43 43 43); border-radius: 1px; border: 2px outset #929292;"></div>                                                                                                                        
      <div style="background-color: orchid; box-shadow: inset 3px 3px 0px 0px rgb(43 43 43); border-radius: 1px; border: 2px outset #929292;"></div>                                                                                                                        
      <div style="background-color: blueviolet; box-shadow: inset 3px 3px 0px 0px rgb(43 43 43); border-radius: 1px; border: 2px outset #929292;"></div>                                                                                                                        
      <div style="background-color:brown; box-shadow: inset 3px 3px 0px 0px rgb(43 43 43); border-radius: 1px; border: 2px outset #929292;"></div>                                                                                                                        
      <div style="background-color: chartreuse; box-shadow: inset 3px 3px 0px 0px rgb(43 43 43); border-radius: 1px; border: 2px outset #929292;"></div>                                                                                                                        
      <div style="background-color: chocolate; box-shadow: inset 3px 3px 0px 0px rgb(43 43 43); border-radius: 1px; border: 2px outset #929292;"></div>                                                                                                                        
      <div style="background-color: black; box-shadow: inset 3px 3px 0px 0px rgb(43 43 43); border-radius: 1px; border: 2px outset #929292;"></div>                                                                                                                        
      <div style="background-color: deeppink; box-shadow: inset 3px 3px 0px 0px rgb(43 43 43); border-radius: 1px; border: 2px outset #929292;"></div>                                                                                                                        
      <div style="background-color: burlywood; box-shadow: inset 3px 3px 0px 0px rgb(43 43 43); border-radius: 1px; border: 2px outset #929292;"></div>                                                                                                                        
      <div style="background-color:gold; box-shadow: inset 3px 3px 0px 0px rgb(43 43 43); border-radius: 1px; border: 2px outset #929292;"></div>                                                                                                                        
      <div style="background-color: pink; box-shadow: inset 3px 3px 0px 0px rgb(43 43 43); border-radius: 1px; border: 2px outset #929292;"></div>                                                                                                                        
      <div style="background-color: darkslateblue; box-shadow: inset 3px 3px 0px 0px rgb(43 43 43); border-radius: 1px; border: 2px outset #929292;"></div>                                                                                                                        
      <div style="background-color: darkturquoise; box-shadow: inset 3px 3px 0px 0px rgb(43 43 43); border-radius: 1px; border: 2px outset #929292;"></div>                                                                                                                        
      <div style="background-color: darkgreen; box-shadow: inset 3px 3px 0px 0px rgb(43 43 43); border-radius: 1px; border: 2px outset #929292;"></div>                                                                                                                        
      <div style="background-color: rgb(173, 0, 46); box-shadow: inset 3px 3px 0px 0px rgb(43 43 43); border-radius: 1px; border: 2px outset #929292;"></div>                                                                                                                        

  </div>
</div>`;

  const popupWidth = 630; // Width of the modal.
  const popupHeight = 520; // Height of the modal.

  const maxX = window.innerWidth - popupWidth;
  const maxY = window.innerHeight - popupHeight;

  const randomX = Math.random() * maxX;
  const randomY = Math.random() * maxY;

  pictureModal.style.left = `${randomX}px`;
  pictureModal.style.top = `${randomY}px`;

  document.body.appendChild(pictureModal);
  const closePictureModalIcon = pictureModal.querySelector(
    "#closePictureModalIcon"
  );
  closePictureModalIcon.addEventListener(
    "click",
    closePictureModal.bind(null, pictureModal)
  );
}

function closePictureModal(modal) {
  modal.remove();
}

function openFolderModal() {
  console.log("Folder modal");
  const folderModal = document.createElement("div");
  folderModal.className = "folder-modal";
  folderModal.style.display = "flex";
  folderModal.innerHTML = `
  <div class="modal-header-container">
  <div class="modal-title">
      <img src = "./images/Folder.png" alt="Minimize" class="modal-icon"/>
      <p>Open</p>
  </div>
  <div class="modal-navigation">
      <p class="modal-nav-minimise-icon">__</p>
      <p class="modal-nav-close-icon" id="closeFolderModalIcon" alt="close">&times;</p>
  </div>
</div>
<div class="location-folder-container">
  <p>Look in</p>
  <div class="location-route">
      <img src = "./images/Folder.png" alt="Folder" class="location-icon"/>
      <p>Your brain</p>
  </div>
  <div class="folder-icon-container">
  <img src = "./images/bug-fill.svg" alt="Minimize" class="nav-icon"/>
  <img src = "./images/bug-outline.svg" alt="Close" class="nav-icon"/>
</div>
</div>
<div class="folder-body-container">
  <div class="folder-content">
  <div class="file-container" id="clickableSVG">
          <img src = "./images/Text.png" alt="File" class="file-icon clickable-text-element"/>
          <p class="clickable-text-element">name</p>
  </div>
  <div class="file-container">
          <img src = "./images/Text.png" alt="File" class="file-icon clickable-text-element"/>
          <p class="clickable-text-element">Document name</p>
  </div>
  <div class="file-container">
          <img src = "./images/Text.png" alt="File" class="file-icon clickable-text-element"/>
          <p class="clickable-text-element">Document name</p>
  </div>
  <div class="file-container">
          <img src = "./images/Text.png" alt="File" class="file-icon clickable-text-element"/>
          <p class="clickable-text-element">Document name</p>
  </div>
      
  <div class="file-container">
          <img src = "./images/Picture.png" alt="Picture" class="file-icon clickable-picture-element"/>
          <p class="clickable-picture-element">Picture name</p>
      </div>
      <div class="file-container">
          <img src = "./images/Folder.png" alt="File" class="file-icon clickable-folder-element" />
          <p class="clickable-folder-element">File name</p>
      </div>
</div>
</div>
<div class="route">
      <div class="route-container">
          <p >File name</p>
          <div class="location-route">
              <p>.txt</p>
          </div>
          <button class="route-icon">Save</button>
          </div>
      <div class="route-container">
          <p>File of type</p>
          <div class="location-route">
              <p>.txt</p>
          </div>
          <button class="route-icon">Cancel</button>
      </div>
  </div>`;

  const popupWidth = 630; // Width of the modal.
  const popupHeight = 400; // Height of the modal.

  const maxX = window.innerWidth - popupWidth;
  const maxY = window.innerHeight - popupHeight;

  const randomX = Math.random() * maxX;
  const randomY = Math.random() * maxY;

  folderModal.style.left = `${randomX}px`;
  folderModal.style.top = `${randomY}px`;

  document.body.appendChild(folderModal);
  const closeFolderModalIcon = folderModal.querySelector(
    "#closeFolderModalIcon"
  );
  closeFolderModalIcon.addEventListener(
    "click",
    closeFolderModal.bind(null, folderModal)
  );
  const clickableTextElements = document.querySelectorAll(
    ".clickable-text-element"
  );
  const clickablePictureElements = document.querySelectorAll(
    ".clickable-picture-element"
  );

  clickablePictureElements.forEach((element) => {
    element.addEventListener("click", openPictureModal);
  });

  clickableTextElements.forEach((element) => {
    console.log("file");
    element.addEventListener("click", openTextModal);
  });
}

function closeFolderModal(modal) {
  modal.remove();
}
