<template>
    <div id="app">
        <!-- <NavBar 
            v-bind:is-authenticated="isAuthenticated"
            v-bind:corna-domain="userData.cornaDomain"
            v-bind:api-url="apiUrl"
        ></NavBar> -->
        <router-view
            v-bind:api-url="apiUrl"
            v-bind:login-check-settled="loginCheckSettled"
            v-bind:is-authenticated="isAuthenticated"
            v-bind:corna-domain="userData.cornaDomain"
        ></router-view>
    </div>
</template>
<script>
import axios from "axios";

import NavBar from "./components/NavBar.vue";

export default {
    components: {
        NavBar,
    },
    data() {
        return {
            apiUrl: null,
            loginCheckSettled: false,
            isAuthenticated: false,
            userData: {
                cornaDomain: null,
                username: null,
            },
            hasErrored: false,
            errMsg: "",
        }
    },
    methods: {
        setApiUrl: function() {
            const currHostname =  window.location.hostname;
            let apiUrl = "https://api.mycorna.com";

            if (currHostname == "localhost" || currHostname == "127.0.0.1") {
                // local backend address
                apiUrl = "http://127.0.0.1:8080/api/v1";
            }
            this.apiUrl = apiUrl;
        },

        checkLoggedIn: function() {
            const checkURL = `${this.apiUrl}/auth/check-login-status`;
            this.loginCheckSettled = false;

            return axios({
                method: "get",
                url: checkURL,
                withCredentials: true,
            })
            .then((response) => {
                this.isAuthenticated = response.data.status;
                console.log(response.data.status)
                console.log("------->")
            })
            .catch((error) => {
                this.hasErrored = true;
                console.log(error.messge);
            })
            .then(() => (this.loginCheckSettled = true));
        },

        getUserData: function() {
            const userDataURL = `${this.apiUrl}/corna/user-details`;

            axios({
                method: "get",
                url: userDataURL,
                withCredentials: true,
            })
            .then((response) => {
                console.log(response.data.username)
                console.log(response.data.domain_name)
                console.log(typeof(response.data.domain_name))
                console.log("*******")
                this.userData.username = response.data.username;
                this.userData.cornaDomain = response.data.domain_name
                    ? response.data.domain_name : null;
            })
            .catch((error) => {
                this.hasErrored = true;
                this.errMsg = error.data.message;
            })
        },

        initialized: function() {
            if (!this.apiUrl) this.setApiUrl();

            this.checkLoggedIn()
            .then(prev => {
                console.log("checked logging")
                console.log(this.loginCheckSettled)
                console.log(this.isAuthenticated)
                if (this.loginCheckSettled && this.isAuthenticated) {
                    console.log("getting data")
                    this.getUserData();
                    console.log("////");
                    // console.log(this.userData.co)
                }
            });
        },
    },
    created() {
        console.log(window.location)
        this.initialized();
        this.$eventBus.$on("userLoggedIn", () => { this.initialized(); })
        this.$eventBus.$on("userLoggedOut", () => { this.initialized(); })
        this.$eventBus.$on("CornaCreated", () => { this.initialized(); })
    },
}
</script>
<style scoped>
#app {
    width: 100%;
    min-height: 100vh;
    display: grid;
    grid-template-columns: 1fr 3fr 1fr;
    grid-template-rows: repeat(6, 1fr);
}
</style>
