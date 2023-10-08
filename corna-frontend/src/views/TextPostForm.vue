<template>
  <div>
    <div v-if="createFailed">
      <p> Oh sh*t! There was an error: {{ errMsg }} </p>
    </div>
    <form-base v-if="isAuthenticated">
      <div slot="form-header"> Make a Text Post </div>
      <div slot="form-fields">
        <text-area
          placeholder="Add your title here!"
          v-model="postData.title"
          v-on:textAreaInnerText="updateTitle"
        >
        </text-area>
        <text-area
          v-model="postData.content"
          placeholder="Write your post here!"
          v-on:textAreaInnerText="updateContent"
          required
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
            :to="{path: '/login', query: {redirect: '/p/text'}}"
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

import formBase from "../components/formBase.vue"
import TextArea from "../components/TextArea.vue"

export default {
  components: {
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
      postData: {
        type: "text",
        content: "",
        title: ""
      },
      createFailed: false,
      errMsg: "",
    }
  },
  methods: {
    handleSubmit: function() {
      axios({
        method: "post",
        url:`${this.apiUrl}/posts/${this.cornaDomain}`,
        data: {
          type: this.postData.type,
          title: this.postData.title,
          content: this.postData.content,
        },
        withCredentials: true,
        // reason for content-type choice comes from here: https://stackoverflow.com/questions/4007969/application-x-www-form-urlencoded-or-multipart-form-data
        headers: {"Content-Type": "application/x-www-form-urlencoded",}
      })
      .then((response) => {
        if (response.status === 201) {
          console.log("text post was successful")
          this.$router.push("/")
        }
      })
      .catch((error) => {
        console.log(error.message);
        this.errMsg = error.message;
        this.createFailed = true;
      });
    },
    updateTitle(newTitle) {
      this.postData.title = newTitle;
    },
    updateContent(newContent) {
      this.postData.content = newContent;
    },
  },
}
</script>
