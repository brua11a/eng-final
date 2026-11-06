<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { student } from '../../api/client'
import ApiMessages from '../../components/ApiMessages.vue'
import { useCycleDetails } from '../../composables/useCycleDetails'
import { errorMessage } from '../../utils/format'

const loading = ref(false)
const error = ref('')
const enrolments = ref([])

const openProgramme = ref('')
const openCurriculum = ref('')
const openTerm = ref('')
const {
  details: cycleDetails,
  loadingId: cycleLoading,
  errors: cycleErrors,
  ensure: ensureCycle,
} = useCycleDetails()

const tree = computed(() => {
  const programmes = new Map()
  for (const e of enrolments.value) {
    if (!programmes.has(e.programme_id)) {
      programmes.set(e.programme_id, { id: e.programme_id, name: e.programme, curricula: new Map() })
    }
    const curricula = programmes.get(e.programme_id).curricula
    if (!curricula.has(e.curriculum_id)) {
      curricula.set(e.curriculum_id, { id: e.curriculum_id, intake_year: e.intake_year, terms: [] })
    }
    curricula.get(e.curriculum_id).terms.push(e)
  }
  return [...programmes.values()]
    .sort((a, b) => a.name.localeCompare(b.name))
    .map((p) => ({
      ...p,
      curricula: [...p.curricula.values()]
        .sort((a, b) => String(b.intake_year).localeCompare(String(a.intake_year)))
        .map((c) => ({ ...c, terms: [...c.terms].sort((a, b) => a.sem - b.sem) })),
    }))
})

function termCycle(t) {
  return t.year && t.season ? `${t.year} ${t.season}` : 'No cycle linked'
}

function toggleProgramme(id) {
  openProgramme.value = openProgramme.value === id ? '' : id
  openCurriculum.value = ''
  openTerm.value = ''
}

function toggleCurriculum(id) {
  openCurriculum.value = openCurriculum.value === id ? '' : id
  openTerm.value = ''
}

function toggleTerm(term) {
  if (!term.cycle_id) return
  openTerm.value = openTerm.value === term.term_id ? '' : term.term_id
  if (openTerm.value) ensureCycle(term.cycle_id)
}

async function load() {
  loading.value = true
  error.value = ''
  openProgramme.value = ''
  try {
    const data = await student.enrolments()
    enrolments.value = data?.enrolments || []
  } catch (e) {
    error.value = errorMessage(e)
    enrolments.value = []
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div class="page-toolbar">
      <h1 class="teacher-page-title">Enrolments</h1>
      <button type="button" class="teacher-btn-secondary" :disabled="loading" @click="load">Refresh</button>
    </div>

    <ApiMessages :error="error" />
    <p v-if="!loading && !tree.length" class="page-empty">No enrolments.</p>

    <div v-for="prog in tree" :key="prog.id" class="teacher-panel st-tree">
      <button type="button" class="st-head" @click="toggleProgramme(prog.id)">
        <strong>{{ prog.name }}</strong>
        <span class="st-chevron">{{ openProgramme === prog.id ? '−' : '+' }}</span>
      </button>

      <template v-if="openProgramme === prog.id">
        <div v-for="curr in prog.curricula" :key="curr.id">
          <button type="button" class="st-head st-head--l2" @click="toggleCurriculum(curr.id)">
            <strong>Curriculum {{ curr.intake_year }}</strong>
            <span class="st-chevron">{{ openCurriculum === curr.id ? '−' : '+' }}</span>
          </button>

          <template v-if="openCurriculum === curr.id">
            <div v-for="term in curr.terms" :key="term.term_id">
              <button
                type="button"
                class="st-head st-head--l3"
                :class="{ 'st-head--open': openTerm === term.term_id }"
                :disabled="!term.cycle_id"
                @click="toggleTerm(term)"
              >
                <strong>Semester {{ term.sem }}</strong>
                <span class="st-meta">{{ termCycle(term) }}</span>
                <span class="st-chevron">
                  <template v-if="term.cycle_id">{{ openTerm === term.term_id ? '−' : '+' }}</template>
                </span>
              </button>

              <div v-if="openTerm === term.term_id" class="st-body">
                <p v-if="cycleLoading === term.cycle_id" class="page-empty">Loading…</p>
                <p v-else-if="cycleErrors[term.cycle_id]" class="page-err">{{ cycleErrors[term.cycle_id] }}</p>
                <p v-else-if="!cycleDetails[term.cycle_id]?.subjects?.length" class="page-empty">
                  No subjects.
                </p>
                <ul v-else class="st-subjects">
                  <li v-for="s in cycleDetails[term.cycle_id].subjects" :key="s.code">
                    <RouterLink :to="{ name: 'catalogue-subject-detail', params: { code: s.code } }">
                      {{ s.name }}
                    </RouterLink>
                    <span class="st-meta">
                      {{ s.code }}<template v-if="s.ects != null"> · {{ s.ects }} ECTS</template>
                    </span>
                  </li>
                </ul>
              </div>
            </div>
          </template>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.st-tree {
  margin-bottom: 0.65rem;
  overflow: hidden;
}

.st-head {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  border: none;
  border-top: 1px solid #eef1f4;
  background: #f8fafc;
  cursor: pointer;
  font: inherit;
  text-align: left;
}

.st-tree > .st-head {
  border-top: none;
}

.st-head strong {
  flex: 1;
}

.st-head:hover:not(:disabled) {
  background: #f1f5f9;
}

.st-head:disabled {
  cursor: default;
}

.st-head--l2 {
  padding-left: 1.5rem;
  background: #fff;
}

.st-head--l3 {
  padding: 0.55rem 1rem 0.55rem 2.25rem;
  background: #fff;
  font-size: 0.88rem;
}

.st-head--open {
  background: #fff7ed;
}

.st-meta {
  font-size: 0.75rem;
  color: #6b7280;
  white-space: nowrap;
}

.st-chevron {
  flex-shrink: 0;
  width: 1.25rem;
  text-align: center;
  font-weight: 600;
  color: #6b7280;
}

.st-body {
  padding: 0.6rem 1rem 0.85rem 2.25rem;
  background: #fafbfc;
  border-top: 1px solid #eef1f4;
}

.st-subjects {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 0.4rem;
  font-size: 0.85rem;
}

.st-subjects li {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}

.st-subjects a {
  color: #e8641b;
  text-decoration: none;
}

.st-subjects a:hover {
  text-decoration: underline;
}
</style>
