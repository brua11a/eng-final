<script setup>
import { onMounted, ref } from 'vue'
import { student } from '../../api/client'
import { useApiCall } from '../../composables/useApiCall'
import ApiMessages from '../../components/ApiMessages.vue'
import JsonPreview from '../../components/JsonPreview.vue'

const listApi = useApiCall()
const detailApi = useApiCall()
const cycleId = ref('')

onMounted(() => listApi.run(() => student.academicCycles()))

function loadDetail() {
  detailApi.run(() => student.academicCycleDetail(cycleId.value))
}
</script>

<template>
  <div>
    <h1>Academic cycles</h1>
    <section class="block">
      <button
        type="button"
        :disabled="listApi.loading"
        @click="listApi.run(() => student.academicCycles())"
      >
        GET /me/academic-cycles
      </button>
      <ApiMessages :error="listApi.error" :api-message="listApi.apiMessage" />
      <JsonPreview :data="listApi.result" />
    </section>
    <section class="block">
      <form class="row" @submit.prevent="loadDetail">
        <input v-model="cycleId" placeholder="cycle_id" required />
        <button type="submit" :disabled="detailApi.loading">POST /me/academic-cycles/detail</button>
      </form>
      <ApiMessages :error="detailApi.error" :api-message="detailApi.apiMessage" />
      <JsonPreview :data="detailApi.result" />
    </section>
  </div>
</template>

<style scoped>
.row {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.block {
  margin-bottom: 1rem;
}
</style>
