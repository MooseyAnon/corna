<template>
    <section class="toolbar-wrapper">
        <TextPostIcon class="text-post"/>
        <PhotoPostIcon class="photo-post"/>
        <HorizontalLineIcon class="splitter"/>
    </section>
</template>
<script>
import TextPostIcon from "./icons/TextPostIcon.vue";
import PhotoPostIcon from "./icons/PhotoPostIcon.vue";
import HorizontalLineIcon from "./icons/HorizontalLineIcon.vue";

export default {
    components: {
        TextPostIcon,
        PhotoPostIcon,
        HorizontalLineIcon,
    },
}
</script>
<style scoped>
.toolbar-wrapper {
    width: 100%;
    height: 100%;
    background-color: pink;
    border: 1px solid red;

    border-radius: 5rem;

    display: grid;
    grid-template-columns: repeat(4, 1fr);
    justify-items: center;
    align-items: center;
}

.text-post {
    grid-column-start: 1;

    height: 100px;
    width: 100px;

    border: 1px solid black;

    border-radius: 5rem;
}

.photo-post {
    grid-column-start: 2;

    height: 100px;
    width: 100px;

    border: 1px solid black;

    border-radius: 5rem;
}

.splitter {
    grid-column-start: 3;
    align-items: flex-end;

    height: 80%;
    width: 40%;

    padding: 0;
    margin: 0;
    transform: rotate(90deg);
    border: 1px solid black;
}
</style>
