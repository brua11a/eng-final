<script setup>
import { onMounted, watch } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { teacher } from '../../api/client'
import { useApiCall } from '../../composables/useApiCall'
import ApiMessages from '../../components/ApiMessages.vue'

const route = useRoute()
const api = useApiCall()

function load() {
  const idx = route.params.studentIdx?.toString()
  if (!idx) return
  api.run(() => teacher.studentDetail(idx))
}

onMounted(load)
watch(() => route.params.studentIdx, load)

const backTo = () => {
  const gid = route.query.groupId
  if (gid) return { name: 'teacher-group-grades', params: { groupId: gid } }
  return { name: 'teacher-groups' }
}
</script>

<template>
  <div>
    <p class="page-back">
      <RouterLink :to="backTo()">← Back</RouterLink>
    </p>

    <h1 class="teacher-page-title">Student</h1>
    <ApiMessages :error="api.error" :api-message="api.apiMessage" />

    <div v-if="api.result && !api.result.err" class="teacher-detail-card">
      <p>
        <strong>{{ api.result.surname }}, {{ api.result.name }}</strong>
      </p>
      <p>Idx: {{ api.result.idx }}</p>
      <p v-if="api.result.phone">Phone: {{ api.result.phone }}</p>
      <p v-if="api.result.avg_grade != null">Average grade: {{ api.result.avg_grade }}</p>
      <p v-if="api.result.joined">Joined: {{ api.result.joined }}</p>
      <p v-if="api.result.term_ids?.length">Terms: {{ api.result.term_ids.join(', ') }}</p>
    </div>
  </div>
</template>
