<script setup>
import { admin } from '../../api/client'
import { useApiCall } from '../../composables/useApiCall'
import ApiMessages from '../../components/ApiMessages.vue'
import JsonPreview from '../../components/JsonPreview.vue'

const faculties = useApiCall()
const programmes = useApiCall()
const rooms = useApiCall()
const cycles = useApiCall()

function loadAll() {
  faculties.run(() => admin.listFaculties())
  programmes.run(() => admin.listProgrammes())
  rooms.run(() => admin.listRooms())
  cycles.run(() => admin.listAcademicCycles())
}
</script>

<template>
  <div>
    <h1>Admin lists</h1>
    <button type="button" @click="loadAll">Load all GET lists</button>

    <section class="block">
      <h2>GET /organizational-units</h2>
      <button type="button" :disabled="faculties.loading" @click="faculties.run(() => admin.listFaculties())">
        Load
      </button>
      <ApiMessages :error="faculties.error" :api-message="faculties.apiMessage" />
      <JsonPreview :data="faculties.result" />
    </section>

    <section class="block">
      <h2>GET /admin/programmes</h2>
      <button type="button" :disabled="programmes.loading" @click="programmes.run(() => admin.listProgrammes())">
        Load
      </button>
      <ApiMessages :error="programmes.error" :api-message="programmes.apiMessage" />
      <JsonPreview :data="programmes.result" />
    </section>

    <section class="block">
      <h2>GET /admin/rooms</h2>
      <button type="button" :disabled="rooms.loading" @click="rooms.run(() => admin.listRooms())">
        Load
      </button>
      <ApiMessages :error="rooms.error" :api-message="rooms.apiMessage" />
      <JsonPreview :data="rooms.result" />
    </section>

    <section class="block">
      <h2>GET /admin/academic-cycles</h2>
      <button
        type="button"
        :disabled="cycles.loading"
        @click="cycles.run(() => admin.listAcademicCycles())"
      >
        Load
      </button>
      <ApiMessages :error="cycles.error" :api-message="cycles.apiMessage" />
      <JsonPreview :data="cycles.result" />
    </section>
  </div>
</template>

<style scoped>
.block {
  margin-top: 1.5rem;
}
.block h2 {
  font-size: 1rem;
}
</style>
