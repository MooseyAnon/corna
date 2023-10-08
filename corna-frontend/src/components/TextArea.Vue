<template>
  <textarea
    v-bind:value="innerContent"
    v-on:change="event => innerContent = event.target.value">
  </textarea>
</template>
<script>
export default {
  name: "TextArea",
  data() {
    return {
      innerContent: "",
    }
  },
  watch: {
    innerContent: function() {
      this.$emit("textAreaInnerText", this.innerContent)
    }
  },
}
</script>
