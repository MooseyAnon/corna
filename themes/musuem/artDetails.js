function addSocialLinks() {
  const socialLinks = [
    "https://www.TikTok.co.uk",
    "https://www.instagram.com/",
    "https://www.facebook.com/",
    "https://twitter.com/?lang=en",
    "https://www.pinterest.com/",
  ];

  const socialMediaContainer = document.getElementById("artSocialContainer");

  socialLinks.forEach((socialUrl) => {
    if (socialUrl.includes("twitter")) {
      const socialMediaItem = document.createElement("div");
      socialMediaItem.classList.add("sociallink");
      const sociallink = document.createElement("a");
      sociallink.href = socialUrl;
      sociallink.setAttribute("target", "_blank");
      const socialIcon = document.createElement("img");
      socialIcon.src = "images/Twitter-icon.png";
      sociallink.append(socialIcon);
      socialMediaItem.append(sociallink);
      socialMediaContainer.append(socialMediaItem);
    }
    if (socialUrl.includes("instagram")) {
      const socialMediaItem = document.createElement("div");
      socialMediaItem.classList.add("sociallink");
      const sociallink = document.createElement("a");
      sociallink.href = socialUrl;
      sociallink.setAttribute("target", "_blank");
      const socialIcon = document.createElement("img");
      socialIcon.src = "images/Instagram-icon.png";
      sociallink.append(socialIcon);
      socialMediaItem.append(sociallink);
      socialMediaContainer.append(socialMediaItem);
    }
    if (socialUrl.includes("facebook")) {
      const socialMediaItem = document.createElement("div");
      socialMediaItem.classList.add("sociallink");
      const sociallink = document.createElement("a");
      sociallink.href = socialUrl;
      sociallink.setAttribute("target", "_blank");
      const socialIcon = document.createElement("img");
      socialIcon.src = "images/Facebook-icon.png";
      sociallink.append(socialIcon);
      socialMediaItem.append(sociallink);
      socialMediaContainer.append(socialMediaItem);
    }
    if (socialUrl.includes("pinterest")) {
      const socialMediaItem = document.createElement("div");
      socialMediaItem.classList.add("sociallink");
      const sociallink = document.createElement("a");
      sociallink.href = socialUrl;
      sociallink.setAttribute("target", "_blank");
      const socialIcon = document.createElement("img");
      socialIcon.src = "images/Pinterest-icon.png";
      sociallink.append(socialIcon);
      socialMediaItem.append(sociallink);
      socialMediaContainer.append(socialMediaItem);
    }
    if (socialUrl.includes("tiktok")) {
      const socialMediaItem = document.createElement("div");
      socialMediaItem.classList.add("sociallink");
      const sociallink = document.createElement("a");
      sociallink.href = socialUrl;
      sociallink.setAttribute("target", "_blank");
      const socialIcon = document.createElement("img");
      socialIcon.src = "images/Tiktok-icon.png";
      sociallink.append(socialIcon);
      socialMediaItem.append(sociallink);
      socialMediaContainer.append(socialMediaItem);
    }
  });

  //add statement to say if you get X social media, so it will do this
}

function getArt() {
  //Replace this with your fetch
  const images = [
    "https://cdn20.pamono.com/p/g/1/4/1405409_g16h81vku8/after-adolphe-monticelli-garden-with-figures-1800s-oil-image-2.jpg",
    "https://douwesfineart.com/wp-content/uploads/2023/06/Adolphe-Monticelli-Quatre-figure-dans-un-parc-photo-1.jpg",
    "https://www.nationalgallery.org.uk/media/pqefhbn5/n-5015-00-000038-hd.jpg?width=350&height=350&rnd=132751395245630000&bgcolor=fff",
    "https://cdn.britannica.com/15/95815-050-1041723F/Fisherman-panel-oil-Nets-Before-the-Storm.jpg",
  ];
  const carousel = document.getElementById("carousel");

  images.forEach((url) => {
    const item = document.createElement("div");
    const itemImage = document.createElement("img");

    itemImage.src = url;

    itemImage.classList.add("itemArt");
    item.classList.add("carouselItem");

    item.append(itemImage);
    carousel.append(item);
  });
}

function displayArtInformation() {
  const fetchedTitle = "A vase of Wild Flowers";
  const fetchedArtist = "Adolphe Monticelli";
  const fetchDescription =
    " (b Marseilles, 14 Oct. 1824; d Marseilles, 29 June 1886). French painter, active in his native Marseilles and in Paris. He was a pupil of Paul Delaroche, but he learned more from his studies of Old Masters in the Louvre; he was also influenced by his friends Delacroix and Diaz de la Peña. His subjects included landscapes, portraits, still lifes, fêtes galantes in the spirit of Watteau, and scenes from the circus, painted in brilliant colours and thick impasto that influenced van Gogh. He enjoyed great success in Paris in the 1860s, but after the outbreak ofthe Franco-Prussian War in 1870 he returned to Marseilles and led a retiring life. His work is represented in many French museums, and he has been much forged.";
  const title = document.getElementById("title");
  const artist = document.getElementById("artist");
  const description = document.getElementById("description");

  title.textContent = fetchedTitle;
  artist.textContent = fetchedArtist;
  description.textContent = fetchDescription;
}

document.addEventListener("DOMContentLoaded", function () {
  addSocialLinks();
  getArt();
  displayArtInformation();
});
