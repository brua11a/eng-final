<script setup>
defineProps({
  pageCount: { type: Number, required: true },
})

const page = defineModel({ type: Number, required: true })
</script>

<template>
  <div v-if="pageCount > 1" class="catalogue-pager">
    <button
      type="button"
      class="catalogue-btn-search catalogue-btn-search--sm"
      :disabled="page <= 1"
      @click="page--"
    >
      Previous
    </button>
    <span>Page {{ page }} / {{ pageCount }}</span>
    <button
      type="button"
      class="catalogue-btn-search catalogue-btn-search--sm"
      :disabled="page >= pageCount"
      @click="page++"
    >
      Next
    </button>
  </div>
</template>
