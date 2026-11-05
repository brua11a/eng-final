<script setup>
import { onMounted, watch, ref } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { catalogue } from '../../api/client'
import { useApiCall } from '../../composables/useApiCall'
import ApiMessages from '../../components/ApiMessages.vue'

const route = useRoute()
const detailApi = useApiCall()
const groupsApi = useApiCall()
const selectedInstanceId = ref('')

async function load() {
  const code = route.params.code
  const data = await detailApi.run(() => catalogue.subjectDetail(code))
  const first = data?.instances?.[0]
  selectedInstanceId.value = first?.id ?? ''
}

function loadGroups() {
  if (!selectedInstanceId.value) return
  groupsApi.run(() => catalogue.subjectGroups(selectedInstanceId.value))
}

onMounted(load)
watch(() => route.params.code, load)
watch(selectedInstanceId, loadGroups)
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

    <h2 class="catalogue-subsection-title">Instances</h2>
    <div v-if="detailApi.result?.instances?.length" class="catalogue-filter-panel">
      <label>
        Cycle
        <select v-model="selectedInstanceId">
          <option v-for="inst in detailApi.result.instances" :key="inst.id" :value="inst.id">
            {{ inst.cycle }}
            <template v-if="inst.catalogue_code"> · {{ inst.catalogue_code }}</template>
            ({{ inst.group_count }} groups)
          </option>
        </select>
      </label>
    </div>
    <p v-else class="catalogue-hint">No instances.</p>

    <h2 class="catalogue-subsection-title">Groups</h2>
    <ApiMessages :error="groupsApi.error" :api-message="groupsApi.apiMessage" />
    <div v-if="groupsApi.result?.groups?.length" class="catalogue-results-table-wrap">
      <table class="catalogue-results-table">
        <thead>
          <tr>
            <th>Type</th>
            <th>No.</th>
            <th>Day</th>
            <th>Room / cycle</th>
            <th>Places</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="g in groupsApi.result.groups" :key="g.id">
            <td>{{ g.g_type }}</td>
            <td>{{ g.number }}</td>
            <td>{{ g.weekday }}</td>
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
