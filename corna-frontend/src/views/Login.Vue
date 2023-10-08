<template>
    <main>
        <div v-if="loginFailed" class="login-error">
            <p> Error logging in: {{ errMsg }} </p>
        </div>
        <form-base class="form">
            <div slot="form-header">Sign in to your account </div>
            <div slot="form-fields">
                <input
                    type="email"
                    placeholder="please enter email"
                    v-model="formData.email"
                    required
                >
                <input
                    type="password"
                    v-model="formData.password"
                    placeholder="please enter password"
                    required
                >
            </div>
            <div slot="form-controls" class="submit">
                <button v-on:click.prevent="handleSubmit"> Submit </button>
            </div>
        </form-base>
    </main>
</template>
<script>
import axios from "axios";

import formBase from "../components/formBase.vue";

export default {
    props: {
        apiUrl: {
            type: String
        },
    },
    components: {
        "form-base": formBase,
    },
    data() {
        return {
            formData: {
                email: "",
                password: "",
            },
            errMsg: "",
            loginFailed: false,
        }
    },
    methods: {
        makeRequest: function() {
            const loginURL = `${this.apiUrl}/auth/login`;
            this.loginFailed = false;

            axios({
                method: "post",
                url: loginURL,
                data: {
                    email_address: this.formData.email,
                    password: this.formData.password,
                },
                withCredentials: true,
            })
            .then((response) => {
                this.$eventBus.$emit("userLoggedIn")
                this.$router.push(this.$route.query.redirect || "/");
            })
            .catch((error) => {
                this.errMsg = error.message;
                this.loginFailed = true;
            })
        },

        isValid: function() {
            return (this.email && this.password) ? true : false;
        },

        handleSubmit: function() {
            if (this.isValid()) {
                this.makeRequest();
            } else {
                this.errMsg = "Both password and email address is required";
                this.loginFailed = true;
            }
        },
    },
}
</script>
<style scoped>
main {
    border: 1px solid black;
    grid-area: 2 / 2 / 6 / 3;

    display: grid;
    grid-template-columns: 1fr;
    grid-template-rows: repeat(4, 1fr);
}

.form {
    grid-area: 1 / 1 / 5 / 2;
    display: grid;

/*    background: pink;*/
    grid-template-columns: 1fr;
    grid-template-rows: repeat(4, 1fr);
}

.submit {
    grid-row: 3 / 4;

    min-width: 10%;
    max-width: 80%;

    display: flex;
    justify-content: center;
    align-items: center;

}

.submit button {
    width: 100%;
    height: 100%;

    background-color: purple;
    border-radius: 5rem;
}
</style>
