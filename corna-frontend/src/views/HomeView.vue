<template>
  <main>
    <ToolBar class="toolbar-outter"/>
  </main>
</template>
<script>
import ToolBar from "../components/ToolBar.vue";

export default {
    components: {
        ToolBar,
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
.toolbar-outter {
    grid-row-start: 2;
}
</style>
