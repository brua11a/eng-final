<script setup>
import { onMounted, ref, shallowRef, watch } from 'vue'
import { useRoute } from 'vue-router'
import { student, teacher } from '../../api/client'
import { useAuthStore } from '../../stores/auth'
import ApiMessages from '../../components/ApiMessages.vue'
import TeacherSelect from '../../components/TeacherSelect.vue'
import WeeklySchedule from '../../components/WeeklySchedule.vue'
import { errorMessage } from '../../utils/format'
import { normalizeEntry } from '../../utils/weekSchedule'

const auth = useAuthStore()
const route = useRoute()

const isTeacherView = route.path.startsWith('/teacher')
const pickTeacher = isTeacherView && auth.hasAdmin
const showStudent = auth.hasStudent
const showTeaching = auth.roles.includes('Teacher') || pickTeacher

const scheduleEntries = shallowRef([])
const loading = ref(false)
const error = ref('')
const teacherIdx = ref(auth.idx || '')

function toEntries(groups, role) {
  return (groups || []).map((g) => normalizeEntry(g, role)).filter(Boolean)
}

let loadToken = 0

async function loadAll() {
  const token = ++loadToken
  loading.value = true
  error.value = ''
  const merged = []
  try {
    if (showStudent) {
      const data = await student.dashboard()
      merged.push(...toEntries(data?.groups, 'student'))
    }
    if (showTeaching) {
      const query = pickTeacher && teacherIdx.value ? { teacher_idx: teacherIdx.value } : {}
      const data = await teacher.myGroups(query)
      merged.push(...toEntries(data?.groups, 'teaching'))
    }
    if (token === loadToken) scheduleEntries.value = merged
  } catch (e) {
    if (token === loadToken) error.value = errorMessage(e)
  } finally {
    if (token === loadToken) loading.value = false
  }
}

function onTeachersReady() {
  loadAll()
  watch(teacherIdx, loadAll)
}

onMounted(() => {
  if (!pickTeacher) loadAll()
})
</script>

<template>
  <div>
    <h1 class="teacher-page-title">Weekly schedule</h1>
    <TeacherSelect v-if="pickTeacher" v-model="teacherIdx" @ready="onTeachersReady" />
    <ApiMessages :error="error" />
    <p v-if="!loading && !error && !scheduleEntries.length" class="page-empty schedule-empty">
      No scheduled classes.
    </p>
    <WeeklySchedule :entries="scheduleEntries" :loading="loading" @refresh="loadAll" />
  </div>
</template>

<style scoped>
.schedule-empty {
  margin-bottom: 0.5rem;
}
</style>
