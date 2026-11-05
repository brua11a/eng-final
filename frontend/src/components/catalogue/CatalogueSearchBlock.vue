<script setup>
defineProps({
  title: { type: String, required: true },
  loading: { type: Boolean, default: false },
  horizontalFields: { type: Boolean, default: false },
  submitLabel: { type: String, default: 'Search' },
})

defineEmits(['search'])
</script>

<template>
  <section class="catalogue-search-block">
    <div class="catalogue-search-block__head">
      <span class="icon-search" aria-hidden="true">🔍</span>
      <span>{{ title }}</span>
    </div>
    <form class="catalogue-search-block__body" @submit.prevent="$emit('search')">
      <div
        class="catalogue-search-block__fields"
        :class="{ 'row-2': horizontalFields }"
      >
        <slot />
      </div>
      <button type="submit" class="catalogue-btn-search" :disabled="loading">
        {{ submitLabel }}
      </button>
    </form>
  </section>
</template>
