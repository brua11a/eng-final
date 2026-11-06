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
  api.run(() => catalogue.teachers(queryName.value))
}

function searchAgain({ name }) {
  router.push({
    name: 'catalogue-teachers-results',
    query: name ? { name } : {},
  })
}
</script>

<template>
  <div class="catalogue-results-page">
    <h1 class="catalogue-page-title">People - results</h1>

    <CatalogueResultsQueryBar
      :initial-name="queryName"
      name-placeholder="Staff name"
      :loading="api.loading"
      @search="searchAgain"
    />

    <ApiMessages :error="api.error" :api-message="api.apiMessage" />

    <div v-if="api.result?.teachers?.length" class="catalogue-results-table-wrap">
      <table class="catalogue-results-table">
        <thead>
          <tr>
            <th>Surname</th>
            <th>First name</th>
            <th>Degree / unit</th>
            <th class="col-action" />
          </tr>
        </thead>
        <tbody>
          <tr v-for="t in api.result.teachers" :key="t.idx">
            <td>{{ t.surname }}</td>
            <td>{{ t.name }}</td>
            <td class="col-meta">{{ t.degree }}<br /><span>{{ t.faculty }}</span></td>
            <td class="col-action">
              <RouterLink
                :to="{ name: 'catalogue-teacher-detail', params: { idx: t.idx }, query: route.query }"
                class="catalogue-link-arrow"
              >
                Profile →
              </RouterLink>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <p v-else-if="api.result && !api.loading" class="catalogue-hint">No results.</p>
  </div>
</template>
