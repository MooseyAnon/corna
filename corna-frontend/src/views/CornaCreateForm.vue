<template>
  <div>
    <div v-if="createFailed">
      <p> Oh Sh*t! There was an error: {{ errMsg }} </p>
    </div>
    <form-base v-if="isAuthenticated">
      <div slot="form-header"> Create you Corna! </div>
      <div slot="form-fields">
        <input
          type="text"
          placeholder="What you calling your Corna?"
          v-model="formData.domainName"
          required
        >
        <input
          type="text"
          placeholder="Give it a title!"
          v-model="formData.title"
          required
        >
      </div>
      <div slot="form-controls">
        <button v-on:click.prevent=""> less gooo! </button>
      </div>
    </form-base>
    <div v-else>
      <span> lets get you
        <button>
          <router-link
            :to="{path: '/login', query: {redirect: '/create-corna'}}"
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

import formBase from "../components/formBase.vue";

export default {
  props: {
    apiUrl: String,
    isAuthenticated: {
      type: Boolean,
      default: false,
    },
  },
  components: {
    "form-base": formBase,
  },
  data() {
    return {
      formData: {
        domainName: null,
        title: null,
      },
      errMsg: "",
      createFailed: false,
    }
  },
  methods: {
    handleSubmit: function() {
      axios
      .post(`${this.apiUrl}/corna/${this.formData.domainName}`, {
        title: this.formData.title,
      }, {withCredentials: true,})
      .then((response) => {
        if (response.status == 201) {
          console.log("successfully created corna");
          this.$eventBus.$emit("CornaCreated");
          this.$router.push("/");
        } else {
          console.log(`UNKNOWN ERROR: RESPONSE CODE: ${response.status}`);
        }
      })
      .catch((error) => {
        console.log(error);
        this.errMsg = error.message;
        this.createFailed = true;
      })
    },
  },
}
</script>
