<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { student } from '../../api/client'
import ApiMessages from '../../components/ApiMessages.vue'
import { useCycleDetails } from '../../composables/useCycleDetails'
import { errorMessage, scheduleLine } from '../../utils/format'

const loading = ref(false)
const error = ref('')
const cycles = ref([])

const expandedId = ref('')
const expandedSubject = ref('')
const {
  details,
  loadingId: detailLoading,
  errors: detailErrors,
  ensure: ensureDetail,
} = useCycleDetails()

const sortedCycles = computed(() =>
  [...cycles.value].sort((a, b) => {
    const ya = String(a.year)
    const yb = String(b.year)
    if (ya !== yb) return yb.localeCompare(ya)
    return String(a.season).localeCompare(String(b.season))
  }),
)

async function loadList() {
  loading.value = true
  error.value = ''
  expandedId.value = ''
  expandedSubject.value = ''
  try {
    const data = await student.academicCycles()
    cycles.value = data?.cycles || []
  } catch (e) {
    error.value = errorMessage(e)
    cycles.value = []
  } finally {
    loading.value = false
  }
}

function toggleCycle(c) {
  expandedSubject.value = ''
  expandedId.value = expandedId.value === c.id ? '' : c.id
  if (expandedId.value) ensureDetail(c.id)
}

function toggleSubject(code) {
  expandedSubject.value = expandedSubject.value === code ? '' : code
}

onMounted(loadList)
</script>

<template>
  <div>
    <div class="page-toolbar">
      <h1 class="teacher-page-title">Academic cycles</h1>
      <button type="button" class="teacher-btn-secondary" :disabled="loading" @click="loadList">
        Refresh
      </button>
    </div>

    <ApiMessages :error="error" />
    <p v-if="!loading && !sortedCycles.length" class="page-empty">No academic cycles.</p>

    <div v-for="c in sortedCycles" :key="c.id" class="teacher-panel st-tree">
      <button
        type="button"
        class="st-tree-head"
        :class="{ 'st-tree-head--open': expandedId === c.id }"
        @click="toggleCycle(c)"
      >
        <strong>{{ c.year }} {{ c.season }}</strong>
        <span class="st-chevron">{{ expandedId === c.id ? '−' : '+' }}</span>
      </button>

      <div v-if="expandedId === c.id">
        <p v-if="detailLoading === c.id" class="page-empty st-pad">Loading…</p>
        <p v-else-if="detailErrors[c.id]" class="page-err st-pad">{{ detailErrors[c.id] }}</p>
        <p v-else-if="!details[c.id]?.subjects?.length" class="page-empty st-pad">No subjects.</p>
        <ul v-else class="st-subjects">
          <li v-for="s in details[c.id].subjects" :key="s.code" class="st-subject">
            <button
              type="button"
              class="st-subject-head"
              :class="{ 'st-subject-head--open': expandedSubject === s.code }"
              @click="toggleSubject(s.code)"
            >
              <span class="st-subject-name">{{ s.name }}</span>
              <span class="st-subject-meta">
                {{ s.code }}<template v-if="s.ects != null"> · {{ s.ects }} ECTS</template>
                · {{ s.groups.length }} {{ s.groups.length === 1 ? 'group' : 'groups' }}
              </span>
              <span class="st-chevron">{{ expandedSubject === s.code ? '−' : '+' }}</span>
            </button>

            <div v-if="expandedSubject === s.code" class="st-subject-body">
              <RouterLink
                :to="{ name: 'catalogue-subject-detail', params: { code: s.code } }"
                class="st-link"
              >
                Subject in catalogue →
              </RouterLink>

              <p v-if="!s.groups.length" class="page-empty">Not registered in any group.</p>
              <table v-else class="teacher-groups-table">
                <thead>
                  <tr>
                    <th>Type</th>
                    <th>#</th>
                    <th>When</th>
                    <th>Room</th>
                    <th>Teacher</th>
                    <th>Grade</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="g in s.groups" :key="g.id">
                    <td>
                      <RouterLink :to="{ name: 'catalogue-group-detail', params: { groupId: g.id } }">
                        {{ g.g_type }}
                      </RouterLink>
                    </td>
                    <td>{{ g.number }}</td>
                    <td>{{ scheduleLine(g.weekday, g.start, g.end) || '-' }}</td>
                    <td>{{ g.room || '-' }}</td>
                    <td>{{ g.teacher || '-' }}</td>
                    <td>{{ g.grade ?? '-' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<style scoped>
.st-pad {
  padding: 0.75rem 1rem;
}

.st-tree {
  margin-bottom: 0.65rem;
  overflow: hidden;
}

.st-tree-head,
.st-subject-head {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  border: none;
  cursor: pointer;
  font: inherit;
  text-align: left;
}

.st-tree-head {
  justify-content: space-between;
  padding: 0.75rem 1rem;
  background: #f8fafc;
}

.st-tree-head:hover {
  background: #f1f5f9;
}

.st-tree-head--open {
  background: #eff6ff;
  border-bottom: 1px solid #e8ecf0;
}

.st-chevron {
  flex-shrink: 0;
  width: 1.25rem;
  text-align: center;
  font-weight: 600;
  color: #6b7280;
}

.st-subjects {
  list-style: none;
  margin: 0;
  padding: 0;
}

.st-subject + .st-subject {
  border-top: 1px solid #eef1f4;
}

.st-subject-head {
  padding: 0.6rem 1rem 0.6rem 1.5rem;
  background: #fff;
}

.st-subject-head:hover {
  background: #fffaf5;
}

.st-subject-head--open {
  background: #fff7ed;
}

.st-subject-name {
  flex: 1;
  font-weight: 600;
  font-size: 0.88rem;
}

.st-subject-meta {
  font-size: 0.75rem;
  color: #6b7280;
  white-space: nowrap;
}

.st-subject-body {
  padding: 0.6rem 1rem 0.85rem 1.5rem;
  background: #fafbfc;
  border-top: 1px solid #eef1f4;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.st-link {
  color: #e8641b;
  text-decoration: none;
  font-size: 0.82rem;
  align-self: flex-start;
}

.st-link:hover {
  text-decoration: underline;
}
</style>
