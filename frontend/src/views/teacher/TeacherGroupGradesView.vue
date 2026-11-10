<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { catalogue, teacher } from '../../api/client'
import { useApiCall } from '../../composables/useApiCall'
import ApiMessages from '../../components/ApiMessages.vue'

const GRADE_OPTIONS = [2, 2.5, 3, 3.5, 4, 4.5, 5]

const route = useRoute()
const groupId = computed(() => route.params.groupId?.toString() ?? '')

const metaApi = useApiCall()
const studentsApi = useApiCall()

const saving = ref(false)
const saveMessage = ref('')
const saveError = ref('')

const drafts = reactive({})
const original = reactive({})

async function loadStudents() {
  const data = await studentsApi.run(() => teacher.groupStudents(groupId.value))
  for (const key of Object.keys(drafts)) delete drafts[key]
  for (const key of Object.keys(original)) delete original[key]
  for (const st of data?.students || []) {
    const g = st.grade ?? ''
    drafts[st.idx] = g === '' ? '' : String(g)
    original[st.idx] = drafts[st.idx]
  }
}

function loadMeta() {
  return metaApi.run(() => catalogue.groupDetail(groupId.value))
}

async function loadAll() {
  await Promise.all([loadMeta(), loadStudents()])
}

onMounted(loadAll)
watch(groupId, loadAll)

const changedRows = computed(() =>
  (studentsApi.result?.students || []).filter((st) => drafts[st.idx] !== original[st.idx]),
)

function parseGrade(val) {
  if (val === '' || val == null) return null
  const n = Number(val)
  return Number.isFinite(n) ? n : null
}

async function saveGrades() {
  const pending = changedRows.value
  if (!pending.length) return
  saving.value = true
  saveError.value = ''
  saveMessage.value = ''
  const errors = []
  try {
    for (const st of pending) {
      const grade = parseGrade(drafts[st.idx])
      if (grade == null) continue
      try {
        const res = await teacher.setGrade(groupId.value, st.idx, grade)
        if (res?.err) errors.push(`${st.idx}: ${res.err}`)
        else original[st.idx] = drafts[st.idx]
      } catch (e) {
        errors.push(`${st.idx}: ${e.message}`)
      }
    }
    if (errors.length) saveError.value = errors.join('; ')
    else saveMessage.value = 'Grades saved.'
  } finally {
    saving.value = false
  }
}

function studentLink(st) {
  return {
    name: 'teacher-student-detail',
    params: { studentIdx: st.idx },
    query: { groupId: groupId.value },
  }
}

function resetDrafts() {
  for (const st of studentsApi.result?.students || []) {
    drafts[st.idx] = original[st.idx]
  }
}

const title = computed(() => {
  const m = metaApi.result
  if (!m) return 'Group grades'
  const code = m.subject_code ? ` [${m.subject_code}]` : ''
  return `${m.course_name}${code}`
})
</script>

<template>
  <div>
    <p class="page-back">
      <RouterLink :to="{ name: 'teacher-groups' }">← My groups</RouterLink>
    </p>

    <h1 class="teacher-page-title">Edit grades</h1>

    <div v-if="metaApi.result" class="teacher-panel">
      <div class="teacher-protocol-head">{{ title }}</div>
      <dl class="teacher-protocol-meta">
        <dt>Cycle:</dt>
        <dd>{{ metaApi.result.academic_cycle }}</dd>
        <dt>Group:</dt>
        <dd>{{ metaApi.result.g_type }} #{{ metaApi.result.group_num }}</dd>
      </dl>

      <ApiMessages
        :error="studentsApi.error || metaApi.error || saveError"
        :api-message="saveMessage"
      />

      <table v-if="studentsApi.result?.students?.length" class="teacher-grades-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Idx</th>
            <th>Surname</th>
            <th>First name</th>
            <th>Grade</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(st, i) in studentsApi.result.students" :key="st.idx">
            <td>{{ i + 1 }}</td>
            <td>{{ st.idx }}</td>
            <td><RouterLink :to="studentLink(st)">{{ st.surname }}</RouterLink></td>
            <td><RouterLink :to="studentLink(st)">{{ st.name }}</RouterLink></td>
            <td>
              <select v-model="drafts[st.idx]">
                <option value="">-</option>
                <option v-for="g in GRADE_OPTIONS" :key="g" :value="String(g)">{{ g }}</option>
              </select>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-else-if="studentsApi.result && !studentsApi.loading" class="page-empty grades-empty">
        No students in this group.
      </p>

      <div class="teacher-actions">
        <button
          type="button"
          class="teacher-btn-save"
          :disabled="saving || !changedRows.length"
          @click="saveGrades"
        >
          Save
        </button>
        <button type="button" class="teacher-btn-secondary" :disabled="!changedRows.length" @click="resetDrafts">
          Revert changes
        </button>
        <span v-if="changedRows.length" class="page-empty">{{ changedRows.length }} unsaved</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.grades-empty {
  padding: 0.75rem;
}
</style>
