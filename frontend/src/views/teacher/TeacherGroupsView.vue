<script setup>
import { onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { teacher } from '../../api/client'
import { useApiCall } from '../../composables/useApiCall'
import { useAuthStore } from '../../stores/auth'
import ApiMessages from '../../components/ApiMessages.vue'
import TeacherSelect from '../../components/TeacherSelect.vue'

const api = useApiCall()
const auth = useAuthStore()
const teacherIdx = ref(auth.idx || '')

function load() {
  const query = auth.hasAdmin && teacherIdx.value ? { teacher_idx: teacherIdx.value } : {}
  return api.run(() => teacher.myGroups(query))
}

function onTeachersReady() {
  load()
  watch(teacherIdx, load)
}

onMounted(() => {
  if (!auth.hasAdmin) load()
})

function rowLabel(g) {
  const code = g.course_code ? ` [${g.course_code}]` : ''
  return `${g.course_name || g.course_code}${code}`
}
</script>

<template>
  <div>
    <div class="page-toolbar">
      <h1 class="teacher-page-title">My groups</h1>
      <button type="button" class="teacher-btn-secondary" :disabled="api.loading" @click="load">Refresh</button>
    </div>

    <TeacherSelect v-if="auth.hasAdmin" v-model="teacherIdx" @ready="onTeachersReady" />

    <ApiMessages :error="api.error" :api-message="api.apiMessage" />

    <div v-if="api.result?.groups?.length" class="teacher-panel">
      <table class="teacher-groups-table">
        <thead>
          <tr>
            <th>Course</th>
            <th>Group</th>
            <th>Cycle</th>
            <th>Room</th>
            <th />
          </tr>
        </thead>
        <tbody>
          <tr v-for="g in api.result.groups" :key="g.group_id">
            <td>{{ rowLabel(g) }}</td>
            <td>{{ g.g_type }} #{{ g.group_num }}</td>
            <td>{{ g.academic_cycle }}</td>
            <td>{{ g.room || '-' }}</td>
            <td>
              <RouterLink :to="{ name: 'teacher-group-grades', params: { groupId: g.group_id } }">
                Grades
              </RouterLink>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <p v-else-if="api.result && !api.loading" class="page-empty">No groups assigned.</p>
  </div>
</template>
