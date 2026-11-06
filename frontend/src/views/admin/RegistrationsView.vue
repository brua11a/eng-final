<script setup>
import { ref } from 'vue'
import { admin } from '../../api/client'
import { useApiCall } from '../../composables/useApiCall'
import { useAdminReferenceData } from '../../composables/useAdminReferenceData'
import ApiMessages from '../../components/ApiMessages.vue'

const { faculties, cycles, groups, facultyLabel, cycleLabel, error: refsError } = useAdminReferenceData()

const api = useApiCall()
const formError = ref('')

const name = ref('')
const cycleId = ref('')
const facultyId = ref('')
const regType = ref('zapisowa')
const turns = ref([
  { turn_number: 1, date: '2025-10-01', start: '08:00', end: '20:00' },
])
const selectedGroupIds = ref([])

function addTurn() {
  const n = turns.value.length + 1
  turns.value.push({
    turn_number: n,
    date: turns.value[turns.value.length - 1]?.date || '2025-10-01',
    start: '08:00',
    end: '20:00',
  })
}

function removeTurn(index) {
  if (turns.value.length <= 1) return
  turns.value.splice(index, 1)
  turns.value.forEach((t, i) => {
    t.turn_number = i + 1
  })
}

function toggleGroup(id) {
  const i = selectedGroupIds.value.indexOf(id)
  if (i >= 0) selectedGroupIds.value.splice(i, 1)
  else selectedGroupIds.value.push(id)
}

function toTimeString(v) {
  if (!v) return ''
  return v.length === 5 ? `${v}:00` : v
}

function submit() {
  formError.value = ''
  if (!turns.value.length) {
    formError.value = 'Add at least one turn'
    return
  }
  for (const t of turns.value) {
    if (!t.date || !t.start || !t.end) {
      formError.value = 'Each turn needs date, start, and end'
      return
    }
  }
  const payloadTurns = turns.value.map((t) => ({
    turn_number: Number(t.turn_number),
    date: t.date,
    start: toTimeString(t.start),
    end: toTimeString(t.end),
  }))
  api.run(() =>
    admin.startRegistrations({
      name: name.value,
      cycle_id: cycleId.value,
      faculty_id: facultyId.value,
      reg_type: regType.value,
      turns: payloadTurns,
      group_ids: selectedGroupIds.value,
    }),
  )
}
</script>

<template>
  <div>
    <h1 class="teacher-page-title">Registrations</h1>
    <ApiMessages v-if="refsError" :error="refsError" />

    <section class="teacher-panel admin-panel-spaced">
      <h2 class="admin-section-title">Start registration window</h2>
      <form class="admin-form admin-form-wide" @submit.prevent="submit">
        <label>Name <input v-model="name" required /></label>
        <label>
          Cycle
          <select v-model="cycleId" required>
            <option value="" disabled>Select cycle</option>
            <option v-for="c in cycles" :key="c.id" :value="c.id">
              {{ cycleLabel(c) }}
            </option>
          </select>
        </label>
        <label>
          Faculty
          <select v-model="facultyId" required>
            <option value="" disabled>Select faculty</option>
            <option v-for="f in faculties" :key="f.id" :value="f.id">
              {{ facultyLabel(f) }}
            </option>
          </select>
        </label>
        <label>Type <input v-model="regType" required /></label>

        <details open class="admin-turns">
          <summary>Registration turns ({{ turns.length }})</summary>
          <div v-for="(turn, index) in turns" :key="index" class="admin-turn-block">
            <div class="admin-turn-head">Turn {{ turn.turn_number }}</div>
            <label>
              Turn number
              <input v-model.number="turn.turn_number" type="number" min="1" required />
            </label>
            <label>
              Date
              <input v-model="turn.date" type="date" required />
            </label>
            <label>
              Start
              <input v-model="turn.start" type="time" required />
            </label>
            <label>
              End
              <input v-model="turn.end" type="time" required />
            </label>
            <button
              v-if="turns.length > 1"
              type="button"
              class="teacher-btn-secondary admin-turn-remove"
              @click="removeTurn(index)"
            >
              Remove
            </button>
          </div>
          <button type="button" class="teacher-btn-secondary" @click="addTurn">Add turn</button>
        </details>

        <fieldset class="admin-group-pick">
          <legend>Groups to open</legend>
          <label v-for="g in groups" :key="g.id" class="admin-check">
            <input type="checkbox" :checked="selectedGroupIds.includes(g.id)" @change="toggleGroup(g.id)" />
            {{ g.label }}
          </label>
        </fieldset>
        <button type="submit" class="teacher-btn-save" :disabled="api.loading">Start</button>
      </form>
      <ApiMessages :error="formError || api.error" :api-message="api.apiMessage" />
      <p v-if="api.result?.id && !api.apiMessage" class="admin-ok">Registration {{ api.result.id }}</p>
    </section>
  </div>
</template>

<style scoped>
.admin-form-wide {
  max-width: 28rem;
}

.admin-turns {
  border: 1px solid #c5cdd6;
  padding: 0.5rem 0.65rem;
}

.admin-turns summary {
  cursor: pointer;
  font-weight: 600;
  font-size: 0.85rem;
  margin-bottom: 0.5rem;
}

.admin-turn-block {
  border-top: 1px solid #e8ecf0;
  padding: 0.65rem 0 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.admin-turn-head {
  font-size: 0.8rem;
  font-weight: 600;
  color: #1a3352;
}

.admin-turn-remove {
  align-self: flex-start;
}

.admin-group-pick {
  border: 1px solid #c5cdd6;
  padding: 0.5rem;
  max-height: 12rem;
  overflow-y: auto;
}

.admin-check {
  display: block;
  font-size: 0.78rem;
  margin-bottom: 0.25rem;
}
</style>
