<script setup>
import { onMounted, watch, ref } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { catalogue } from '../../api/client'
import { useApiCall } from '../../composables/useApiCall'
import ApiMessages from '../../components/ApiMessages.vue'
import { scheduleLine } from '../../utils/format'

const route = useRoute()
const detailApi = useApiCall()
const groupsApi = useApiCall()
const selectedCycleId = ref('')

async function load() {
  const code = route.params.code
  const data = await detailApi.run(() => catalogue.subjectDetail(code))
  const first = data?.offerings?.[0]
  selectedCycleId.value = first?.cycle_id ?? ''
}

function loadGroups() {
  if (!selectedCycleId.value) return
  groupsApi.run(() => catalogue.subjectGroups(route.params.code, selectedCycleId.value))
}

onMounted(load)
watch(() => route.params.code, load)
watch(selectedCycleId, loadGroups)
</script>

<template>
  <div>
    <h1 class="catalogue-page-title">Subject {{ route.params.code }}</h1>
    <p class="catalogue-hint">
      <RouterLink to="/catalogue/przedmioty">← Subjects</RouterLink>
    </p>
    <ApiMessages :error="detailApi.error" :api-message="detailApi.apiMessage" />
    <div v-if="detailApi.result" class="catalogue-detail-card">
      <p><strong>{{ detailApi.result.name }}</strong></p>
      <p v-if="detailApi.result.ects != null">ECTS: {{ detailApi.result.ects }}</p>
      <p v-if="detailApi.result.taught_by?.length">
        Teachers:
        <span v-for="(t, i) in detailApi.result.taught_by" :key="t.id">
          {{ i ? ', ' : '' }}{{ t.name }}
        </span>
      </p>
    </div>

    <h2 class="catalogue-subsection-title">Offered in</h2>
    <div v-if="detailApi.result?.offerings?.length" class="catalogue-filter-panel">
      <label>
        Cycle
        <select v-model="selectedCycleId">
          <option v-for="o in detailApi.result.offerings" :key="o.cycle_id" :value="o.cycle_id">
            {{ o.cycle }} ({{ o.group_count }} groups)
          </option>
        </select>
      </label>
    </div>
    <p v-else class="catalogue-hint">Not offered in any cycle.</p>

    <h2 class="catalogue-subsection-title">Groups</h2>
    <ApiMessages :error="groupsApi.error" :api-message="groupsApi.apiMessage" />
    <div v-if="groupsApi.result?.groups?.length" class="catalogue-results-table-wrap">
      <table class="catalogue-results-table">
        <thead>
          <tr>
            <th>Type</th>
            <th>No.</th>
            <th>When</th>
            <th>Room / cycle</th>
            <th>Places</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="g in groupsApi.result.groups" :key="g.id">
            <td>
              <RouterLink
                :to="{ name: 'catalogue-group-detail', params: { groupId: g.id } }"
                class="catalogue-link-arrow"
              >
                {{ g.g_type }}
              </RouterLink>
            </td>
            <td>{{ g.number }}</td>
            <td>{{ scheduleLine(g.weekday, g.start_hr, g.end_time) }} {{ g.pnp }}</td>
            <td>{{ g.room }} · {{ g.cycle }}</td>
            <td>{{ g.filled }} / {{ g.capacity }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <p v-else-if="groupsApi.result && !groupsApi.loading" class="catalogue-hint">No groups.</p>
  </div>
</template>

<style scoped>
.catalogue-detail-card {
  background: #fff;
  border: 1px solid #c5cdd6;
  padding: 1rem;
  margin-bottom: 1rem;
}
</style>
