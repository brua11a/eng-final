<script setup>
import { onMounted } from 'vue'
import { admin } from '../../api/client'
import { useApiCall } from '../../composables/useApiCall'
import ApiMessages from '../../components/ApiMessages.vue'

const lists = [
  {
    title: 'Faculties',
    key: 'faculties',
    load: admin.listFaculties,
    columns: [
      ['Id', 'id'],
      ['Name', 'name'],
      ['Full name', 'full_name'],
    ],
  },
  {
    title: 'Programmes',
    key: 'programmes',
    load: admin.listProgrammes,
    columns: [
      ['Id', 'id'],
      ['Name', 'name'],
      ['Faculty', 'faculty_id'],
    ],
  },
  {
    title: 'Rooms',
    key: 'rooms',
    load: admin.listRooms,
    columns: [
      ['Id', 'id'],
      ['Building', 'building'],
      ['Room', 'room_num'],
    ],
  },
  {
    title: 'Academic cycles',
    key: 'cycles',
    load: admin.listAcademicCycles,
    columns: [
      ['Id', 'id'],
      ['Year', 'year'],
      ['Season', 'season'],
    ],
  },
].map((list) => ({ ...list, api: useApiCall() }))

function loadAll() {
  for (const list of lists) list.api.run(list.load)
}

onMounted(loadAll)
</script>

<template>
  <div>
    <div class="page-toolbar">
      <h1 class="teacher-page-title">Reference lists</h1>
      <button type="button" class="teacher-btn-secondary" @click="loadAll">Refresh</button>
    </div>

    <section v-for="list in lists" :key="list.key" class="teacher-panel admin-panel-spaced">
      <h2 class="admin-section-title">{{ list.title }}</h2>
      <ApiMessages :error="list.api.error" :api-message="list.api.apiMessage" />
      <table v-if="list.api.result?.[list.key]?.length" class="teacher-groups-table">
        <thead>
          <tr>
            <th v-for="[label] in list.columns" :key="label">{{ label }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in list.api.result[list.key]" :key="row.id">
            <td v-for="[label, field] in list.columns" :key="label">{{ row[field] }}</td>
          </tr>
        </tbody>
      </table>
      <p v-else-if="list.api.result && !list.api.loading" class="admin-ok">
        No {{ list.title.toLowerCase() }}.
      </p>
    </section>
  </div>
</template>
