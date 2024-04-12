document.addEventListener("DOMContentLoaded", function () {
  let loggedIn = localStorage.getItem("loggedIn") === "true" || false;
  console.log(loggedIn);
  console.log("Initial loggedIn state:", loggedIn); // Add this line to log the initial state
  let currentUser = null;
  let hoverEnabled = true;

  updateNavigation(loggedIn);
  addHoverEventListeners();

  //----------------- NAV HOVER ------------------
  function handleNavItemHoverIn(event) {
    if (!hoverEnabled) return;
    console.log("hovering over navitem");
    const dot = event.target.querySelector(".dot");
    const navLabel = event.target.querySelector(".navLabel");

    dot.style.animation = "dotBounceIn 0.5s ease forwards";
    navLabel.style.animation = "labelBounceIn 0.5s ease forwards";
    dot.style.display = "block";
    navLabel.style.display = "block";
  }

  // Function to handle navItem hover out animation
  function handleNavItemHoverOut(event) {
    if (!hoverEnabled) return;
    console.log("NOT HOVERING");
    if (event.target.classList.contains("navItem")) {
      const dot = event.target.querySelector(".dot");
      const navLabel = event.target.querySelector(".navLabel");
      // Reset animations and hide dot and navLabel
      dot.style.animation = "none";
      navLabel.style.animation = "none";
      dot.style.display = "none";
      navLabel.style.display = "none";
    }
  }

  function addHoverEventListeners() {
    hoverEnabled = true;
    const navItems = document.querySelectorAll(".navItem");
    navItems.forEach((item) => {
      console.log(item);
      item.addEventListener("mouseenter", handleNavItemHoverIn);
      item.addEventListener("mouseleave", handleNavItemHoverOut);
    });
  }

  function removeHoverEventListeners() {
    hoverEnabled = false;
  }

  document.getElementById("create").addEventListener("click", function (event) {
    const createOptions = document.getElementById("createOptions");
    console.log("hovering");
    event.preventDefault(); // Prevent default link behavior
    createOptions.classList.toggle("active"); // Toggle the 'active' class on createOptions

    if (createOptions.classList.contains("active")) {
      const dot = this.querySelector(".dot");
      const navLabel = this.querySelector(".navLabel");
      // Reset animations and hide dot and navLabel
      dot.style.animation = "none";
      navLabel.style.animation = "none";
      dot.style.display = "none";
      navLabel.style.display = "none";
      removeHoverEventListeners(); // Remove hover event listeners on navItems
      createOptions.classList.remove("notActive");
    } else {
      createOptions.classList.add("notActive");
      addHoverEventListeners(); // Add hover event listeners back on navItems
    }
    event.stopPropagation();
    document.addEventListener("click", handleClickOutside);
    // document.getElementById("video").addEventListener("click", openVideoPost);
    // document.getElementById("text").addEventListener("click", openTextPost);
    // document
    //   .getElementById("picture")
    //   .addEventListener("click", openPicturePost);
  });

  function handleClickOutside(event) {
    if (
      createOptions.classList.contains("active") &&
      !createOptions.contains(event.target)
    ) {
      createOptions.classList.add("notActive");
      createOptions.classList.remove("active"); // Remove the 'active' class from createOptions
      console.log("dismiss createOptions");
      addHoverEventListeners();
    }
  }
  //-----------------POST TYPES ------------------

  function modalFunction() {
    const createButton = document.getElementById("createPost");
    const closeButton = document.getElementById("closePost");
    const dropArea = document.getElementById("drop-area");
    const inputFile = document.getElementById("input-file");

    closeButton.addEventListener("click", closeModal);
    createButton.addEventListener("click", post);

    dropArea.addEventListener("dragover", function (e) {
      e.preventDefault();
    });

    dropArea.addEventListener("drop", function (e) {
      e.preventDefault();
      if (e.dataTransfer.files.length > 0) {
        handleFileInput(e.dataTransfer.files);
      }
    });

    function handleFileInput(files) {
      if (files.length > 0) {
        createButton.classList.add("enabled");
        updateMediaPreview(files);
      } else {
        createButton.classList.remove("enabled");
      }
    }
    inputFile.addEventListener("change", function () {
      handleFileInput(inputFile.files);
    });
    function closeModal() {
      closeOverlay();
    }
    function post() {
      const bodyLargeContainer = document.querySelector(".bodyLargeContainer");
      const cardContainer = document.getElementById("cardContainer");
      displayStatusMessage("Please wait whilst the magic happens...");
      bodyLargeContainer.classList.add("clicked");
      setTimeout(() => {
        cardContainer.classList.add("dropped");
      }, "700");
      setTimeout(() => {
        clearStatusMessaging();
        bodyLargeContainer.classList.remove("clicked");
        cardContainer.classList.remove("dropped");
        closeOverlay();
      }, "1200");
    }

    function updateMediaPreview(files) {
      dropArea.innerHTML = ""; // Clear the drop area
      const sliderContainer = document.createElement("div");
      sliderContainer.id = "slider-container";
      sliderContainer.className = "slider-container";
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const fileType = file.type.split("/")[0];

        if (fileType === "image") {
          // Handle image file
          const reader = new FileReader();
          reader.onload = function (e) {
            const imgElement = document.createElement("img");
            imgElement.src = e.target.result;
            imgElement.className = "slider-image";
            sliderContainer.appendChild(imgElement);
          };
          reader.readAsDataURL(file);
        } else if (fileType === "video") {
          // Handle video file
          const videoElement = document.createElement("video");
          videoElement.src = URL.createObjectURL(file);
          videoElement.controls = true;
          videoElement.className = "slider-video";
          sliderContainer.appendChild(videoElement);
        }
      }
      dropArea.appendChild(sliderContainer);
    }
  }

  ///------------------OPEN OVERLAY------------------
  const overlay = document.getElementById("overlay");

  document.addEventListener("htmx:beforeSwap", function (event) {
    showOverlay(event);
  });

  overlay.addEventListener("click", function (event) {
    closeOverlay();
  });

  function showOverlay(event) {
    overlay.style.display = "flex";
  }

  //-----------CLOSE OVERLAY ------------
  function closeOverlay() {
    const signInContainer = document.getElementById("signInContainer");
    const imageModal = document.getElementById("imageModal");
    const textModal = document.getElementById("textModal");
    const videoModal = document.getElementById("videoModal");
    const registerContainer = document.getElementById("registerContainer");
    const cornaCardContainer = document.getElementById("cornaCardContainer");
    const permission = document.getElementById("permissionsContainer");
    const characterCard = document.getElementById("characterCard");
    const characterCreator = document.getElementById("characterCreator");

    if (signInContainer) {
      signInContainer.remove();
    }
    if (registerContainer) {
      registerContainer.remove();
    }
    if (imageModal) {
      imageModal.remove();
    }
    if (videoModal) {
      videoModal.remove();
    }
    if (textModal) {
      textModal.remove();
    }
    if (cornaCardContainer) {
      cornaCardContainer.remove();
    }
    if (permission) {
      permission.remove();
    }
    if (characterCard) {
      characterCard.remove();
    }
    if (characterCreator) {
      characterCreator.remove();
    }
    overlay.style.display = "none";
    var originalDiv = document.createElement("div");
    originalDiv.id = "content";
    document.getElementById("cardContainer").append(originalDiv);
  }

  //---------- STOP CLOSING WHEN INTERACTING WITHIN THE CONTAINER
  cardContainer.addEventListener("click", function (event) {
    event.stopPropagation(); // Stop the click event from bubbling up
  });
  //----------CHANGE THE NAVIGATION BASED ON IF LOGGED IN OR NOT ----------

  function isUserLoggedIn(logged) {
    // ----------Put logic to check if user is logged in or not
    return false; // Placeholder value, replace with actual logic
  }

  function updateNavigation(loggedIn) {
    const loggedInNavigation = document.getElementById("loggedInNavigation");
    const loggedOutNavigation = document.getElementById("loggedOutNavigation");

    if (loggedIn === true) {
      loggedInNavigation.style.display = "flex";
      loggedOutNavigation.style.display = "none";
    } else {
      loggedInNavigation.style.display = "none";
      loggedOutNavigation.style.display = "flex";
    }
  }

  function handleLogin() {
    const emailRaw = document.getElementById("emailInput");
    const passwordRaw = document.getElementById("passwordInput");
    email = emailRaw.value.trim();
    password = passwordRaw.value.trim();

    if (email === "" || password === "") {
      displayErrorMessage("Please enter both username and password.");
      return;
    }

    const isAuthenticated = authenticateUser(email, password);
    if (isAuthenticated) {
      loggedIn = true;
      currentUser = email;
      updateNavigation(loggedIn);
      localStorage.setItem("loggedIn", "true"); // Remember the login status      loadingMessage("Please wait whilst the magic happens...");
      //   container.innerHTML = "";
      cardContainer.classList.add("clicked");
      fetchUserDetails(email);
      setTimeout(() => {
        clearStatusMessaging();
        closeOverlay();
        cardContainer.classList.remove("clicked");
      }, "1000");
    } else {
      loggedIn = false;
      displayErrorMessage("Incorrect username and password");
    }
  }

  function authenticateUser(email, password) {
    const validEmail = "cil";
    const validPassword = "password";
    return email === validEmail && password === validPassword;
  }

  //-------- GLOBAL IN LINE ERROR HANDLING ------------
  function displayErrorMessage(message) {
    const errorMessageElement = document.getElementById("validation");
    errorMessageElement.textContent = message;
  }
  //-------- GLOBAL STATUS---------------------
  function displayStatusMessage(message) {
    const statusMessage = document.getElementById("statusUpdateMessage");
    statusMessage.textContent = message;
  }
  function clearErrorMessaging() {
    console.log("clear messaging");
    const errorMessageElement = document.getElementById("validation");

    errorMessageElement.textContent = "";
  }
  function clearStatusMessaging() {
    console.log("clear messaging");

    const statusMessage = document.getElementById("statusUpdateMessage");

    statusMessage.textContent = "";
  }

  //--------------REGISTRATION---------------

  const registrationModule = function () {
    let selectedTheme;

    function handleUserCreation() {
      console.log("user registeration");
      const nextToThemeButton = document.getElementById("nextToTheme");
      const registerButton = document.getElementById("Register");
      const rawUsername = document.getElementById("usernameInput");
      const rawEmail = document.getElementById("emailInput");
      const rawPassword = document.getElementById("passwordInput");
      const themeDetailsSection = document.getElementById("themeDetails");

      const username = rawUsername.value.trim();
      const email = rawEmail.value.trim();
      const password = rawPassword.value.trim();

      if (username === "" || email === "" || password === "") {
        displayErrorMessage("Please fill in all the details");
        return;
      } else {
        themeDetailsSection.style.display = "flex";
        themeDetailsSection.style.opacity = "1";
        scrollTo(themeDetailsSection);
        clearErrorMessaging();
        clearStatusMessaging();
      }
      registerButton.addEventListener("click", handleRegistration);
      function scrollTo(section) {
        nextToThemeButton.style.display = "none";
        registerButton.style.display = "block";
        console.log(section);
        section.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    }
    function handleRegistration() {
      const rawUsername = document.getElementById("usernameInput");
      const rawEmail = document.getElementById("emailInput");
      const rawPassword = document.getElementById("passwordInput");
      const rawUrl = document.getElementById("urlInput");
      const rawTabTitle = document.getElementById("tabtitleInput");

      const username = rawUsername.value.trim();
      const email = rawEmail.value.trim();
      const password = rawPassword.value.trim();
      const url = rawUrl.value.trim();
      const tabtitle = rawTabTitle.value.trim();

      if (
        username === "" ||
        email === "" ||
        password === "" ||
        url === "" ||
        tabtitle === "" ||
        selectedTheme === undefined
      ) {
        displayErrorMessage("Please fill in all the details");
        return;
      } else {
        creatingUser();

        displayStatusMessage("Please wait whilst the magic happens...");
        clearErrorMessaging();
        cardContainer.classList.add("clicked");
      }
    }
    function creatingUser() {
      //this is where you can add your code to send to the back end
      loggedIn = true;
      updateNavigation(loggedIn);
      setTimeout(() => {
        clearStatusMessaging();
        closeOverlay();
        cardContainer.classList.remove("clicked");
      }, "1000");
    }
    // fethcing JSON themes
    function themeSelection() {
      fetch("theme.JSON")
        .then((response) => response.json())
        .then((data) => {
          const themeGallery = document.getElementById("themeGallery");

          data.forEach((themeData) => {
            console.log("Theme:", themeData);
            const themeContainer = document.createElement("div");
            themeContainer.classList.add("themeContainer");

            const theme = document.createElement("img");
            theme.classList.add("theme");
            theme.src = themeData.url;
            theme.alt = themeData.description;

            let themeSelector = document.createElement("div");
            themeSelector.classList.add("themeSelector");
            themeContainer.addEventListener("click", function (event) {
              selectTheme(themeData.id, themeSelector);
            });

            themeGallery.appendChild(themeContainer);
            themeContainer.appendChild(themeSelector);
            themeContainer.appendChild(theme);
          });
        })
        .catch((error) => {
          console.error("Error fetching images:", error);
        });

      function selectTheme(themeId, themeSelector) {
        selectedTheme = themeId;

        const themeSelectors = document.querySelectorAll(".themeSelector");
        themeSelectors.forEach((selector) => {
          selector.style.background = "";
        });
        console.log(themeSelector);
        themeSelector.style.background = "white"; // Set the background of the clicked themeSelector

        console.log("Selected theme:", selectedTheme);
      }
    }
    return {
      handleUserCreation,
      handleRegistration,
      themeSelection, // Expose themeSelection function
    };
  };
  // -------- ADDING EVENT LISTENERS TO AFTER THE SWAP---------
  document.addEventListener("htmx:afterSwap", function (event) {
    if (
      event.detail.target.matches("#content") &&
      event.target.matches("#signInContainer")
    ) {
      document.getElementById("signIn").addEventListener("click", handleLogin);
      clearErrorMessaging();
      clearStatusMessaging();
    } else if (
      event.detail.target.matches("#content") &&
      event.target.matches("#createTextBody")
    ) {
      clearErrorMessaging();
      clearStatusMessaging();
    } else if (event.target.matches("#registerContainer")) {
      const registration = registrationModule();
      const nextToThemeButton = document.getElementById("nextToTheme");
      nextToThemeButton.addEventListener(
        "click",
        registration.handleUserCreation
      );
      registration.themeSelection();
      //create post add event listeners
    } else if (event.target.matches("#imageModal")) {
      clearErrorMessaging();
      clearStatusMessaging();
      modalFunction();
    } else if (event.target.matches("#textModal")) {
      clearErrorMessaging();
      clearStatusMessaging();
      modalFunction();
    } else if (event.target.matches("#videoModal")) {
      clearErrorMessaging();
      clearStatusMessaging();
      modalFunction();
    } else if (event.target.matches("#cornaCardContainer")) {
      clearErrorMessaging();
      clearStatusMessaging();
      cornaCard();
      const email = "cil@exampl.com";
      fetchUserDetails(email); // Fetch user details
      document
        .getElementById("signOut")
        .addEventListener("click", handleLogOut);
    } else if (event.target.matches("#permissionsContainer")) {
      clearErrorMessaging();
      clearStatusMessaging();
      getCharacters(currentUser);
    } else if (event.target.matches("#characterCreator")) {
      clearErrorMessaging();
      clearStatusMessaging();
      //need a condition to check whether they came from an existing character or creating a new character
      createCharacter();
    } else {
    }
  });

  //----------------------------------CORNA CARD------------------------------------

  function fetchUserDetails(email) {
    return fetch("globalUser.json")
      .then((response) => {
        if (!response.ok) {
          throw new Error("Failed to fetch user data");
        }
        return response.json();
      })
      .then((data) => {
        const user = data.users.find((user) => user.email === email);
        if (user) {
          console.log("fetched user details", user);
          currentUser = user;
          cornaCard();
          return user;
        } else {
          throw new Error("User not found");
        }
      })
      .catch((error) => {
        console.log("error");
      });
  }

  function cornaCard() {
    console.log("we are in CornaCard function");
    const username = document.getElementById("username");
    const cred = document.getElementById("cred");
    const role = document.getElementById("role");
    const avatar = document.getElementById("avatarImage");

    if (currentUser) {
      username.textContent = currentUser.username;
      cred.textContent = currentUser.hp;
      role.textContent = currentUser.role;
      avatar.src = currentUser.avatar;
    } else {
      console.error("User details not available");
    }
  }
  function handleLogOut() {
    localStorage.removeItem("loggedIn");
    loggedIn = false;
    updateNavigation(loggedIn);
    currentUser = null;
    closeOverlay();
  }
  function getCharacters(currentUser) {
    document.getElementById("return").addEventListener("click", closeOverlay);

    for (const permissionKey in currentUser.permissions) {
      if (currentUser.permissions.hasOwnProperty(permissionKey)) {
        const permission = currentUser.permissions[permissionKey];
        const charactersContainer = document.getElementById(
          "charactersContainer"
        );
        console.log(permission);

        const character = document.createElement("div");
        const identifier = document.createElement("div");
        const characterName = document.createElement("div");
        const pill = document.createElement("div");

        character.classList.add("character");
        characterName.classList.add("characterName");
        identifier.classList.add("characterIdentifer");
        pill.classList.add("pill");
        console.log(permissionKey);

        character.setAttribute("hx-get", "characterCard.html"); // Example URL, replace with your actual endpoint
        character.setAttribute("hx-trigger", "click");
        character.setAttribute("hx-target", "#permissionsContainer");
        character.setAttribute("hx-swap", "outerHTML");

        character.addEventListener("click", function () {
          // Modify the htmx:afterSwap event listener to ensure correct permission is passed
          document.addEventListener(
            "htmx:afterSwap",
            function () {
              console.log("this is converting");
              getCharacterCardInfo(permission); // Pass the specific permission object
            },
            { once: true }
          ); // Use { once: true } to ensure it only runs once
        });

        characterName.textContent = permission.name;
        pill.textContent = permission.default;
        identifier.textContent = permission.identifier;

        if (permission.default === "" || null) {
          pill.style.opacity = 0;
        }

        console.log(pill);
        console.log("This is the pill of the permission" + permission.pill);
        console.log("This is the name of the permission" + permission.name);
        console.log(
          "This is the identifier of the permission" + permission.identifier
        );

        character.appendChild(characterName);
        character.appendChild(identifier);
        character.appendChild(pill);
        charactersContainer.appendChild(character);

        function getCharacterCardInfo(permission) {
          const characterCardContainer = document.getElementById(
            "characterCardContainer"
          );

          const headerCopy = document.getElementById("modalHeaderCopy");
          headerCopy.textContent = "YOUR CHARACTER";
          console.log(characterCardContainer);

          console.log("CORNACARD OF: " + permission.name);

          const membersDetails = document.getElementById("membersDetails");
          const identifierDetails =
            document.getElementById("identifierDetails");

          const characterCardName =
            document.getElementById("characterCardName");
          characterCardName.textContent = permission.name;

          const characterIdentiferContainer =
            document.getElementById("characterIdentifer");
          characterIdentifer.textContent = permission.identifier;
          // characterIdentiferContainer.appendChild(characterIdentifer);

          const skills = document.getElementById("skills");
          for (const skillKey in permission.skill) {
            if (permission.skill.hasOwnProperty(skillKey)) {
              console.log(permission.skill);
              const skillElement = document.createElement("div");

              skillElement.classList.add("value");
              skillElement.textContent = permission.skill[skillKey];

              skills.appendChild(skillElement);
            }
          }
          for (const memberKey in permission.member) {
            if (permission.member.hasOwnProperty(memberKey)) {
              console.log(permission.member);
              const memberElement = document.createElement("div");
              memberElement.classList.add("member");

              const fullname = permission.member[memberKey];
              const initials = fullname
                .split(" ")
                .map((part) => part.charAt(0))
                .join("");
              memberElement.textContent = initials;

              membersDetails.appendChild(memberElement);
            }
          }
          // for loop for members to create a div and then applying a class name member & append it to members
          // for loop to go through skills and then apply class name
        }

        // // Modify your existing code to directly call getCharacterCardInfo instead of using htmx events
        // character.addEventListener("click", function () {
        //   getCharacterCardInfo(permission);
        // });
      }
    }
  }
  //----------------------------------CREATE CHARACTER CARD------------------------------------
  function createCharacter(editing) {
    console.log(
      " =-----------you are trying to edit or create a character again =-----------"
    );
    const chosenIdentifer = document.getElementById("selectedIdentifer");
    const skills = document.querySelectorAll(".skills .skillOption");
    const characterNameInput = document.getElementById("characterNameInput");
    const identifierOptions = document.querySelectorAll(
      ".identifierOptionContainer .identiferIcon"
    );
    const createCharacterButton = document.getElementById("createCharacter");

    const selectedSkills = [];

    characterNameInput.value = "";
    chosenIdentifer.textContent = "";
    selectedSkills.forEach((skill) => {
      skill.classList.remove("activeSelection");
    });

    // Listen to the characterName
    characterNameInput.addEventListener("input", function () {
      this.value;
    });

    //Allow for selection of identifier and highlight the selected one
    identifierOptions.forEach((option) => {
      option.addEventListener("click", function () {
        chosenIdentifer.textContent = option.textContent;
        option.classList.add("activeSelection");

        identifierOptions.forEach((otherOption) => {
          if (otherOption !== option) {
            otherOption.classList.remove("activeSelection");
          }
        });
      });
    });

    //Allow for selection of skills and highlight the selection
    function attachSkillListeners() {
      console.log("hello");
      skills.forEach((skill) => {
        console.log("each skills in the editing character");
        skill.addEventListener("click", function () {
          if (this.classList.contains("activeSelection")) {
            this.classList.remove("activeSelection");
            const index = selectedSkills.indexOf(this.textContent);
            if (index !== -1) {
              selectedSkills.splice(index, 1);
            }
          } else {
            selectedSkills.push(skill.textContent);
            this.classList.add("activeSelection");
          }

          console.log("Selected Skills:", selectedSkills);
        });
      });
    }
    attachSkillListeners();

    createCharacterButton.addEventListener("click", submitCharacter);

    function submitCharacter() {
      // Display status message and clear after a delay
      console.log("Character Data:", {
        characterName: characterNameInput.value,
        selectedSkills: Array.from(skills)
          .filter((s) => s.classList.contains("activeSelection"))
          .map((s) => s.textContent),
        selectedIdentifier: chosenIdentifer.textContent,
      });

      const newCharacterData = {
        characterName: characterNameInput.value,
        selectedSkills: Array.from(skills)
          .filter((s) => s.classList.contains("activeSelection"))
          .map((s) => s.textContent),
        selectedIdentifier: chosenIdentifer.textContent,
      };

      characterCreator.style.display = "none";
      setTimeout(() => {
        displayStatusMessage(
          "Please wait whilst your character gets created.."
        );
      }, "300");
      setTimeout(() => {
        clearStatusMessaging();
        document.addEventListener(
          "htmx:afterSwap",
          function afterSwapHandler(event) {
            const headerCopy = document.getElementById("modalHeaderCopy");

            headerCopy.textContent = "YOU’VE CREATED A CHARACTER!";
            document.getElementById("characterCardName").textContent =
              characterNameInput.value;
            document.getElementById("characterIdentifer").textContent =
              chosenIdentifer.textContent;

            const skillsContainer = document.getElementById("skills");
            skillsContainer.innerHTML = ""; // Clear previous skills

            // Populate skills
            selectedSkills.forEach((skill) => {
              const skillElement = document.createElement("div");
              skillElement.classList.add("value");
              skillElement.textContent = skill;
              skillsContainer.appendChild(skillElement);
            });

            // Swap to characterCard.html
            // const characterCardContent =
            //   document.getElementById("characterCard").outerHTML;
            // document.getElementById("characterCreator").innerHTML =
            //   characterCreatorContainer;
            // characterCreator.style.display = "flex";
            // characterCard.style.display = "flex";
            document.removeEventListener("htmx:afterSwap", afterSwapHandler);
          }
        );
      }, "1200");
    }
  }
});
