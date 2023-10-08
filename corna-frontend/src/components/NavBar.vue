<template>
<nav>
  <ul class="right">
    <li>
      <router-link to="/"> Corna </router-link>
    </li>
    <li v-if="isAuthenticated">
      <button v-if="cornaDomain">
        <a v-bind:href="cornaURL"> {{ cornaDomain }} </a>
      </button>
      <button v-else-if="!cornaDomain">
        <router-link to="/create-corna"> Create a corna! </router-link>
      </button>
    </li>
    <li>
      <button v-if="!isAuthenticated">
        <router-link to="/login"> Login </router-link>
      </button>
      <button v-else v-on:click.prevent="handleLogout">
        logout
      </button>
    </li>
  </ul>
</nav>
</template>
<script>
import axios from "axios";

export default {
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
  methods: {
    handleLogout: function() {
      axios.delete(`${this.apiUrl}/auth/logout`, {withCredentials: true,})
      .then((response) => (this.$eventBus.$emit("userLoggedOut")))
      .catch((error) => (console.log(error)));
    },
  },
  computed: {
    cornaURL: function() {
      console.log("corna url maker called");
      if (this.isAuthenticated && this.cornaDomain) {
        return `https://${this.cornaDomain}.mycorna.com`;
      }
    },
  },
}
</script>
<style scoped>
nav {
  background-color: red;
}
ul {
  background-color: yellow;
}
li {
  display: inline-block;
  margin-inline: 0.5rem;
}
li a {
  text-decoration: none;
  color: blue;
}
.right {
  background-color: purple;
  list-style-type: none;
  text-align: right;
  margin: 0;
  padding: 0.5rem;
}
</style>
