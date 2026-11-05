<script setup>
import { onMounted, watch, computed, ref } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { catalogue } from '../../api/client'
import { useApiCall } from '../../composables/useApiCall'
import ApiMessages from '../../components/ApiMessages.vue'
import CatalogueResultsQueryBar from '../../components/catalogue/CatalogueResultsQueryBar.vue'

const route = useRoute()
const router = useRouter()
const api = useApiCall()

const queryName = computed(() => (route.query.name || '').toString())
const queryCode = computed(() => (route.query.code || '').toString())

const pageSize = 30
const page = ref(1)

const cycleColumns = computed(() => api.result?.cycle_columns ?? [])
const rows = computed(() => api.result?.subjects ?? [])
const total = computed(() => rows.value.length)
const pageRows = computed(() => {
  const start = (page.value - 1) * pageSize
  return rows.value.slice(start, start + pageSize)
})

onMounted(load)
watch(
  () => [route.name, route.query.name, route.query.code],
  () => {
    page.value = 1
    load()
  },
)

function load() {
  api.run(() => catalogue.subjects(queryName.value, queryCode.value))
}

function searchAgain({ name, code }) {
  const query = {}
  if (name) query.name = name
  if (code) query.code = code
  router.push({ name: 'catalogue-subjects-results', query })
}

function cellLabel(cell) {
  if (!cell?.instance_id) return '—'
  if (cell.registration_open) return `${cell.group_count} groups`
  if (cell.group_count) return `${cell.group_count} groups (closed)`
  return '—'
}
</script>

<template>
  <div class="catalogue-results-page catalogue-results-page--wide">
    <h1 class="catalogue-page-title">Subjects — results</h1>

    <CatalogueResultsQueryBar
      :single="false"
      :initial-name="queryName"
      :initial-code="queryCode"
      name-placeholder="Subject name"
      code-placeholder="Subject code"
      :loading="api.loading"
      @search="searchAgain"
    />

    <ApiMessages :error="api.error" :api-message="api.apiMessage" />

    <div v-if="pageRows.length" class="catalogue-results-table-wrap">
      <table class="catalogue-results-table catalogue-results-table--subjects">
        <thead>
          <tr>
            <th>Code</th>
            <th>Unit</th>
            <th>Name</th>
            <th v-for="col in cycleColumns" :key="col">{{ col }}</th>
            <th class="col-action" />
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in pageRows" :key="s.code">
            <td>
              <RouterLink
                :to="{ name: 'catalogue-subject-detail', params: { code: s.code } }"
                class="catalogue-link-arrow"
              >
                {{ s.code }}
              </RouterLink>
            </td>
            <td>{{ s.faculty || '—' }}</td>
            <td>{{ s.name }}</td>
            <td v-for="(cell, idx) in s.cycles" :key="cycleColumns[idx] || idx">
              {{ cellLabel(cell) }}
            </td>
            <td class="col-action">
              <RouterLink
                :to="{ name: 'catalogue-subject-detail', params: { code: s.code } }"
                class="catalogue-link-arrow"
              >
                Detail →
              </RouterLink>
            </td>
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
