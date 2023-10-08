<template>
  <div>
    <h1>Test Page</h1>
    <div>This is a test div</div>

    <h2> testProp: {{ testProp }} </h2>
  </div>
</template>

<script>
export default {
  props: ["testProp"],
  created() {
    console.log(this.testProp);
    console.log("------->");
  },
}
</script>
