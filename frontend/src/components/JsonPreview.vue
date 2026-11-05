<script setup>
defineProps({
  data: { type: [Object, Array, String, Number, Boolean, null], default: null },
})
</script>

<template>
  <pre v-if="data != null" class="json">{{ JSON.stringify(data, null, 2) }}</pre>
</template>

<style scoped>
.json {
  background: #f3f4f6;
  padding: 0.75rem;
  border-radius: 4px;
  overflow: auto;
  max-height: 24rem;
  font-size: 0.85rem;
}
</style>
