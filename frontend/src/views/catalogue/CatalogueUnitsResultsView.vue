<script setup>
import { onMounted, watch, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { catalogue } from '../../api/client'
import { useApiCall } from '../../composables/useApiCall'
import { usePaged } from '../../composables/usePaged'
import ApiMessages from '../../components/ApiMessages.vue'
import CataloguePager from '../../components/catalogue/CataloguePager.vue'
import CatalogueResultsQueryBar from '../../components/catalogue/CatalogueResultsQueryBar.vue'

const route = useRoute()
const router = useRouter()
const api = useApiCall()

const queryName = computed(() => (route.query.name || '').toString())
const { page, pageCount, pageRows } = usePaged(computed(() => api.result?.faculties ?? []))

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
    <h1 class="catalogue-page-title">Units - results</h1>

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

    <CataloguePager v-model="page" :page-count="pageCount" />
  </div>
</template>
