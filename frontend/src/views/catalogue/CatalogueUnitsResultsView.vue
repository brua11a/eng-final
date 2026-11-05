<script setup>
import { onMounted, watch, computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { catalogue } from '../../api/client'
import { useApiCall } from '../../composables/useApiCall'
import ApiMessages from '../../components/ApiMessages.vue'
import CatalogueResultsQueryBar from '../../components/catalogue/CatalogueResultsQueryBar.vue'

const route = useRoute()
const router = useRouter()
const api = useApiCall()

const queryName = computed(() => (route.query.name || '').toString())
const pageSize = 30
const page = ref(1)

const rows = computed(() => api.result?.faculties ?? [])
const total = computed(() => rows.value.length)
const pageRows = computed(() => {
  const start = (page.value - 1) * pageSize
  return rows.value.slice(start, start + pageSize)
})

onMounted(load)
watch(
  () => [route.name, route.query.name],
  () => {
    page.value = 1
    load()
  },
)

function load() {
  api.run(() => catalogue.organizationalUnits(queryName.value))
}

function searchAgain({ name }) {
  router.push({
    name: 'catalogue-units-results',
    query: name ? { name } : {},
  })
}
</script>

<template>
  <div class="catalogue-results-page">
    <h1 class="catalogue-page-title">Units — results</h1>

    <CatalogueResultsQueryBar
      single
      :initial-name="queryName"
      name-placeholder="Unit name or code"
      :loading="api.loading"
      @search="searchAgain"
    />

    <ApiMessages :error="api.error" :api-message="api.apiMessage" />

    <div v-if="pageRows.length" class="catalogue-results-table-wrap">
      <table class="catalogue-results-table">
        <thead>
          <tr>
            <th>Code</th>
            <th>Name</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="fa in pageRows" :key="fa.id">
            <td>{{ fa.name }}</td>
            <td>{{ fa.full_name }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <p v-else-if="api.result && !api.loading" class="catalogue-hint">No results.</p>

    <div v-if="total > pageSize" class="catalogue-pager">
      <button
        type="button"
        class="catalogue-btn-search catalogue-btn-search--sm"
        :disabled="page <= 1"
        @click="page--"
      >
        Previous
      </button>
      <span>Page {{ page }}</span>
      <button
        type="button"
        class="catalogue-btn-search catalogue-btn-search--sm"
        :disabled="page * pageSize >= total"
        @click="page++"
      >
        Next
      </button>
    </div>
  </div>
</template>
