<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  title: { type: String, default: 'Refine search' },
  submitLabel: { type: String, default: 'Search' },
  loading: { type: Boolean, default: false },
  single: { type: Boolean, default: true },
  initialName: { type: String, default: '' },
  initialCode: { type: String, default: '' },
  namePlaceholder: { type: String, default: 'Search…' },
  codePlaceholder: { type: String, default: 'Subject code' },
})

const emit = defineEmits(['search'])

const name = ref(props.initialName)
const code = ref(props.initialCode)

watch(
  () => [props.initialName, props.initialCode],
  ([n, c]) => {
    name.value = n
    code.value = c
  },
)

function submit() {
  emit('search', { name: name.value.trim(), code: code.value.trim() })
}
</script>

<template>
  <section class="catalogue-search-block catalogue-results-query">
    <div class="catalogue-search-block__head">
      <span class="icon-search" aria-hidden="true">🔍</span>
      <span>{{ title }}</span>
    </div>
    <form class="catalogue-search-block__body" @submit.prevent="submit">
      <div class="catalogue-search-block__fields" :class="{ 'row-2': !single }">
        <input v-model="name" type="search" :placeholder="namePlaceholder" />
        <input v-if="!single" v-model="code" type="search" :placeholder="codePlaceholder" />
      </div>
      <button type="submit" class="catalogue-btn-search" :disabled="loading">
        {{ submitLabel }}
      </button>
    </form>
  </section>
</template>
