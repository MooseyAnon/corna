<template>
  <div
    class="dropzone"
    v-on:dragover="dragOver"
    v-on:dragleave="dragLeave"
    v-on:drop="drop"
    v-bind:class="isDragging && 'border-color: green'"
  >
    <input
      type="file"
      name="file"
      id="fileInput"
      class="hidden-input"
      v-on:change="onChange"
      ref="file"
      accept=".pdf,.jpg,.jpeg,.png"
    />
    <label for="fileInput" class="file-input">
      <div v-if="isDragging"> Release to drop files here </div>
      <div v-else> Drop file here <u> click here </u> to upload. </div>
    </label>
    <div class="preview-container mt-4" v-if="files.length">
      <div
        v-for="file in files"
        v-bind:key="file.name"
        class="preview-card"
      >
        <img class="preview-img" v-bind:src="imgPreview(file)">
        <p>
          {{ file.name }} - 
          {{ Math.round(file.size / 1000) + "kb" }}
        </p>
      </div>
      <div>
        <button
          class="ml-2"
          type="button"
          v-on:click="remove(files.indexOf(file))"
          title="Remove File"
        >
          <b> X </b>
        </button>
      </div>
    </div>
  </div>
</template>
<script>

export default {
  data() {
    return {
      isDragging: false,
      files: [],
    }
  },
  methods: {
    onChange: function() {
      if (this.$refs.file.files.length > 1) {
        console.log("WARNING: Multiple pictures uploaded!")
      }
      this.files.push(...this.$refs.file.files);
    },
    dragOver: function(e) {
      e.preventDefault();
      this.isDragging = true;
    },
    dragLeave: function() {
      this.isDragging = false;
    },
    drop: function(e) {
      e.preventDefault();
      this.$refs.file.files = e.target.files || e.dataTransfer.files;
      this.onChange();
      this.isDragging = false;
    },
    remove: function(index) {
      this.files.splice(index, 1);
    },
    imgPreview: function(file) {
      const fileSrc = URL.createObjectURL(file);
      setTimeout(() => {
        URL.revokeObjectURL(fileSrc);
      }, 1000);
      return fileSrc;
    },
  },
  watch: {
    files: function() {
      this.$emit("fileUpload", this.files)
    },
  },
}
</script>
<style scoped>
.dropzone {
  padding: 4rem;
  background: #f7fafc;
  border: 2px dashed;
  border-color: #9e9e9e;
}

.hidden-input {
  opacity: 0;
  overflow: hidden;
  position: absolute;
  width: 1px;
  height: 1px;
}

.file-label {
  font-size: 20px;
  display: block;
  cursor: pointer;
}

.preview-container {
  display: flex;
  margin-top: 2rem;
}

.preview-card {
  display: flex;
  border: 1px solid #a2a2a2;
  padding: 5px;
  margin-left: 5px;
}

.preview-img {
  width: 50px;
  height: 50px;
  border-radius: 5px;
  border: 1px solid #a2a2a2;
  background-color: #a2a2a2;
}
</style>
