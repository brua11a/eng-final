<script setup>
import { computed, onMounted, ref } from 'vue'
import { catalogue, student } from '../../api/client'
import ApiMessages from '../../components/ApiMessages.vue'
import GroupFacts from '../../components/GroupFacts.vue'
import { errorMessage, scheduleLine, timeRange } from '../../utils/format'

const loadingList = ref(false)
const listError = ref('')
const registrations = ref([])

const selected = ref(null)
const loadingCourses = ref(false)
const coursesError = ref('')
const courses = ref([])

const expandedCourseId = ref('')
const groupsByCourse = ref({})
const groupsLoading = ref('')
const groupsError = ref({})
const registerStatus = ref({})

const detailGroupId = ref('')
const detailLoading = ref(false)
const detailError = ref('')
const detailData = ref(null)

const onListScreen = computed(() => !selected.value)

function registrationLabel(r) {
  return `${r.name} · turn ${r.turn_number} · ${r.date} ${timeRange(r.start, r.end)}`
}

function groupsForCourse(courseId) {
  return groupsByCourse.value[courseId] || []
}

function groupsGroupedByType(courseId) {
  const byType = new Map()
  for (const g of groupsForCourse(courseId)) {
    if (!byType.has(g.g_type)) byType.set(g.g_type, [])
    byType.get(g.g_type).push(g)
  }
  return [...byType.entries()].sort((a, b) => a[0].localeCompare(b[0]))
}

function registeredInType(courseId, gType) {
  return groupsForCourse(courseId).find((g) => g.registered && g.g_type === gType)
}

function canRegister(courseId, group) {
  if (group.registered) return false
  const taken = registeredInType(courseId, group.g_type)
  return !taken
}

async function loadRegistrations() {
  loadingList.value = true
  listError.value = ''
  try {
    const data = await student.registrations()
    registrations.value = data?.available_registrations || []
  } catch (e) {
    listError.value = errorMessage(e)
    registrations.value = []
  } finally {
    loadingList.value = false
  }
}

async function openRegistration(r) {
  selected.value = r
  expandedCourseId.value = ''
  groupsByCourse.value = {}
  groupsError.value = {}
  registerStatus.value = {}
  detailGroupId.value = ''
  detailData.value = null
  courses.value = []
  loadingCourses.value = true
  coursesError.value = ''
  try {
    const data = await student.registrationCourses(r.id)
    courses.value = data?.courses || []
  } catch (e) {
    coursesError.value = errorMessage(e)
  } finally {
    loadingCourses.value = false
  }
}

function backToList() {
  selected.value = null
  courses.value = []
  expandedCourseId.value = ''
  detailGroupId.value = ''
  detailData.value = null
}

function classSummary(course) {
  if (!course.classes?.length) return ''
  return course.classes.map((c) => `${c.g_type} (${c.count})`).join(', ')
}

async function refreshCourseGroups(courseId) {
  if (!selected.value) return
  const data = await student.registrationGroups(selected.value.id, courseId)
  groupsByCourse.value = { ...groupsByCourse.value, [courseId]: data?.groups || [] }
}

async function toggleCourse(course) {
  const id = course.id
  if (expandedCourseId.value === id) {
    expandedCourseId.value = ''
    detailGroupId.value = ''
    detailData.value = null
    return
  }
  expandedCourseId.value = id
  detailGroupId.value = ''
  detailData.value = null
  if (groupsByCourse.value[id]) return

  groupsLoading.value = id
  groupsError.value = { ...groupsError.value, [id]: '' }
  try {
    await refreshCourseGroups(id)
  } catch (e) {
    groupsError.value = { ...groupsError.value, [id]: errorMessage(e) }
  } finally {
    groupsLoading.value = ''
  }
}

async function pickGroup(group) {
  if (detailGroupId.value === group.id) {
    detailGroupId.value = ''
    detailData.value = null
    return
  }
  detailGroupId.value = group.id
  detailLoading.value = true
  detailError.value = ''
  detailData.value = null
  try {
    detailData.value = await catalogue.groupDetail(group.id)
  } catch (e) {
    detailError.value = errorMessage(e)
  } finally {
    detailLoading.value = false
  }
}

async function setRegistered(courseId, group, register) {
  const key = group.id
  registerStatus.value = { ...registerStatus.value, [key]: { saving: true, err: '' } }
  try {
    const call = register ? student.register : student.deregister
    const res = await call(courseId, group.id)
    if (res?.err || res?.ok === false) {
      registerStatus.value[key] = { saving: false, err: res?.err || 'Request failed' }
    } else {
      registerStatus.value[key] = { saving: false, err: '' }
      await refreshCourseGroups(courseId)
    }
  } catch (e) {
    registerStatus.value[key] = { saving: false, err: errorMessage(e) }
  }
}

onMounted(loadRegistrations)
</script>

<template>
  <div>
    <div class="page-toolbar">
      <h1 class="teacher-page-title">Registrations</h1>
      <button
        v-if="onListScreen"
        type="button"
        class="teacher-btn-secondary"
        :disabled="loadingList"
        @click="loadRegistrations"
      >
        Refresh
      </button>
    </div>

    <template v-if="onListScreen">
      <ApiMessages :error="listError" />
      <p v-if="!loadingList && !registrations.length" class="page-empty">No registration windows available.</p>
      <ul v-else class="reg-list">
        <li v-for="r in registrations" :key="r.id">
          <button type="button" class="reg-pick" @click="openRegistration(r)">
            <strong>{{ r.name }}</strong>
            <span>Turn {{ r.turn_number }} · {{ r.date }}</span>
            <span>{{ timeRange(r.start, r.end) }} · {{ r.reg_type }}</span>
          </button>
        </li>
      </ul>
    </template>

    <template v-else>
      <button type="button" class="teacher-btn-secondary reg-back" @click="backToList">← All registrations</button>
      <h2 class="reg-detail-title">{{ registrationLabel(selected) }}</h2>
      <p class="reg-meta">Curriculum {{ selected.curriculum_id }}</p>

      <ApiMessages :error="coursesError" />
      <p v-if="loadingCourses" class="page-empty">Loading subjects…</p>
      <p v-else-if="!courses.length" class="page-empty">No subjects in this registration.</p>

      <div v-for="course in courses" :key="course.id" class="teacher-panel reg-course">
        <button type="button" class="reg-course-head" @click="toggleCourse(course)">
          <span>
            <strong>{{ course.name }}</strong>
            <span v-if="classSummary(course)" class="reg-course-meta">{{ classSummary(course) }}</span>
          </span>
          <span class="reg-course-meta">{{ course.academic_cycle }}</span>
        </button>

        <div v-if="expandedCourseId === course.id" class="reg-groups">
          <p v-if="groupsLoading === course.id" class="page-empty">Loading groups…</p>
          <p v-else-if="groupsError[course.id]" class="reg-err">{{ groupsError[course.id] }}</p>
          <p v-else-if="!groupsForCourse(course.id).length" class="page-empty">No open groups.</p>

          <template v-else>
            <section
              v-for="[gType, typeGroups] in groupsGroupedByType(course.id)"
              :key="gType"
              class="reg-type-block"
            >
              <h3 class="reg-type-title">{{ gType }}</h3>

              <table class="teacher-groups-table reg-groups-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>When</th>
                    <th>Room</th>
                    <th>Teacher</th>
                    <th>Places</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="g in typeGroups"
                    :key="g.id"
                    class="reg-row"
                    :class="{ 'reg-row--selected': detailGroupId === g.id, 'reg-row--mine': g.registered }"
                    @click="pickGroup(g)"
                  >
                    <td>{{ g.number }}</td>
                    <td>{{ scheduleLine(g.weekday, g.start, g.end) }}</td>
                    <td>{{ g.room || '-' }}</td>
                    <td>{{ g.teacher || '-' }}</td>
                    <td>{{ g.filled }}/{{ g.capacity }}</td>
                    <td class="reg-action" @click.stop>
                      <button
                        v-if="g.registered"
                        type="button"
                        class="teacher-btn-secondary"
                        :disabled="registerStatus[g.id]?.saving"
                        @click="setRegistered(course.id, g, false)"
                      >
                        Deregister
                      </button>
                      <button
                        v-else-if="canRegister(course.id, g)"
                        type="button"
                        class="teacher-btn-save"
                        :disabled="registerStatus[g.id]?.saving"
                        @click="setRegistered(course.id, g, true)"
                      >
                        Register
                      </button>
                      <span v-else class="reg-muted">Other group chosen</span>
                      <span v-if="registerStatus[g.id]?.err" class="reg-err">{{ registerStatus[g.id].err }}</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </section>

            <aside v-if="detailGroupId" class="reg-detail-panel">
              <h3 class="reg-detail-panel-title">Group details</h3>
              <p v-if="detailLoading" class="page-empty">Loading…</p>
              <p v-else-if="detailError" class="reg-err">{{ detailError }}</p>
              <GroupFacts v-else-if="detailData" :group="detailData" />
            </aside>
          </template>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.reg-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-width: 36rem;
}

.reg-pick {
  width: 100%;
  text-align: left;
  padding: 0.75rem 1rem;
  border: 1px solid #c5cdd6;
  background: #fff;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  font: inherit;
}

.reg-pick:hover {
  border-color: #e8641b;
  background: #fffaf5;
}

.reg-back {
  margin-bottom: 0.75rem;
}

.reg-detail-title {
  margin: 0 0 0.25rem;
  font-size: 1.05rem;
  font-weight: 600;
}

.reg-meta {
  margin: 0 0 1rem;
  font-size: 0.82rem;
  color: #6b7280;
}

.reg-course {
  margin-bottom: 0.75rem;
  max-width: 56rem;
  padding: 0;
  overflow: hidden;
}

.reg-course-head {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  padding: 0.75rem 1rem;
  border: none;
  background: #f8fafc;
  cursor: pointer;
  font: inherit;
  text-align: left;
}

.reg-course-meta {
  display: block;
  font-size: 0.78rem;
  color: #6b7280;
  font-weight: normal;
  margin-top: 0.15rem;
}

.reg-groups {
  padding: 0.75rem 1rem 1rem;
  border-top: 1px solid #e8ecf0;
}

.reg-type-block {
  margin-bottom: 1.25rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid #e8ecf0;
}

.reg-type-block:last-of-type {
  border-bottom: none;
  margin-bottom: 0.5rem;
}

.reg-type-title {
  margin: 0 0 0.35rem;
  font-size: 0.9rem;
  font-weight: 600;
  color: #1a3352;
}

.reg-row {
  cursor: pointer;
}

.reg-row--selected {
  background: #eff6ff;
}

.reg-row--mine {
  background: #f0fdf4;
}

.reg-action {
  white-space: nowrap;
  min-width: 8rem;
}

.reg-muted {
  font-size: 0.75rem;
  color: #9ca3af;
}

.reg-err {
  display: block;
  color: #b91c1c;
  font-size: 0.75rem;
  margin-top: 0.25rem;
}

.reg-detail-panel {
  margin-top: 1rem;
  padding: 0.75rem 1rem;
  background: #f8fafc;
  border: 1px solid #c5cdd6;
  max-width: 28rem;
}

.reg-detail-panel-title {
  margin: 0 0 0.5rem;
  font-size: 0.9rem;
}
</style>
