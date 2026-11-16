<script setup>
defineProps({
  error: { type: String, default: '' },
})
</script>

<template>
  <p v-if="error" class="msg err">{{ error }}</p>
</template>

<style scoped>
.msg {
  padding: 0.5rem 0.75rem;
  border-radius: 4px;
  margin: 0.5rem 0;
}
.err {
  background: #fde8e8;
  color: #9b1c1c;
}
</style>
