<template>
  <div>
    <div v-if="createFailed">
      <p> Oh Sh*t! There was an error: {{ errMsg }} </p>
    </div>
    <form-base v-if="isAuthenticated">
      <div slot="form-header"> Post a photo! </div>
      <div slot="form-fields">
        <drag-drop v-on:fileUpload="handleFiles"></drag-drop>
        <text-area
          placeholder="Caption"
          v-on:textAreaInnerText="updateCaption"
        >
        </text-area>
      </div>
      <div slot="form-controls">
        <button v-on:click.prevent="handleSubmit"> Submit </button>
      </div>
    </form-base>
    <div v-else>
      <span> lets get you
        <button>
          <router-link
            :to="{path: '/login', query: {redirect: '/p/photo'}}"
          >
            logged in!
          </router-link>
        </button>
      </span>
    </div>
  </div>
</template>
<script>
import axios from "axios";

import DragDrop from "../components/DragDrop.vue"
import formBase from "../components/formBase.vue"
import TextArea from "../components/TextArea.vue"

export default {
  components: {
    "drag-drop": DragDrop,
    "form-base": formBase,
    "text-area": TextArea,
  },
  props: {
    apiUrl: {
      type: String,
      default: null,
    },
    isAuthenticated: {
      type: Boolean,
      default: false,
    },
    cornaDomain: {
      type: String,
      default: null,
    },
  },
  data() {
    return {
      postData:{
        type: "picture",
        caption: "",
        // we'll leave this as an array for now as it will make doing
        // albums easier in the future
        files: [],
      },
      errMsg: "",
      createFailed: true,
    }
  },
  methods: {
    handleSubmit: function() {
      console.log(this.postData.caption);
      console.log(this.postData.files[0]);
      const singleFile = this.postData.files[0]

      axios({
        method: "post",
        url: `${this.apiUrl}/posts/${this.cornaDomain}`,
        data: {
          type: this.postData.type,
          caption: this.postData.caption,
          pictures: singleFile,
        },
        withCredentials: true,
        // reason for content-type choice comes from here: https://stackoverflow.com/questions/4007969/application-x-www-form-urlencoded-or-multipart-form-data
        headers: {"Content-Type": "multipart/form-data"}
      })
      .then((response) => {
        if (response.status === 201) {
          console.log("photo post was successful");
          this.$router.push("/");
        }
      })
      .catch((error) => {
        console.log(error.message);
        this.errMsg = error.message;
        this.createFailed = true;
      });
    },
    handleFiles: function(data) {
      console.log("received emit data");
      this.postData.files = data;
    },
    updateCaption: function(data) {
      this.postData.caption = data;
    },
  },
}
</script>
