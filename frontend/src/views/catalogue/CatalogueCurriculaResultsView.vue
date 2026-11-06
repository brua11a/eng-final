<script setup>
import { onMounted, watch, computed } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { catalogue } from '../../api/client'
import { useApiCall } from '../../composables/useApiCall'
import ApiMessages from '../../components/ApiMessages.vue'
import CatalogueResultsQueryBar from '../../components/catalogue/CatalogueResultsQueryBar.vue'

const route = useRoute()
const router = useRouter()
const api = useApiCall()

const queryName = computed(() => (route.query.name || '').toString())

onMounted(load)
watch(
  () => [route.name, route.query.name],
  () => load(),
)

function load() {
  api.run(() => catalogue.curricula(queryName.value))
}

function searchAgain({ name }) {
  router.push({
    name: 'catalogue-curricula-results',
    query: name ? { name } : {},
  })
}
</script>

<template>
  <div>
    <h1 class="catalogue-page-title">Programmes - results</h1>

    <CatalogueResultsQueryBar
      :initial-name="queryName"
      name-placeholder="Programme name"
      :loading="api.loading"
      @search="searchAgain"
    />

    <ApiMessages :error="api.error" :api-message="api.apiMessage" />

    <ul v-if="api.result?.curricula?.length" class="result-list">
      <li v-for="c in api.result.curricula" :key="c.id">
        <RouterLink :to="{ name: 'catalogue-curricula-results', query: { name: c.name } }">
          {{ c.name }}
        </RouterLink>
        <span class="meta">Intake {{ c.intake_year }}</span>
      </li>
    </ul>
    <p v-else-if="api.result && !api.loading" class="catalogue-hint">No results.</p>
  </div>
</template>

<style scoped>
.result-list {
  list-style: none;
  padding: 0;
  margin: 0;
  background: #fff;
  border: 1px solid #c5cdd6;
}
.result-list li {
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid #e8ecf0;
}
.result-list a {
  color: #e8641b;
  text-decoration: none;
}
.result-list a:hover {
  text-decoration: underline;
}
.meta {
  display: block;
  font-size: 0.8rem;
  color: #5c6570;
}
</style>
