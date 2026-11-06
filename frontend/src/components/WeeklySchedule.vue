<script setup>
import { computed, ref } from 'vue'
import {
  WEEKDAY_LABELS,
  addDays,
  eventsForWeek,
  formatMinutes,
  startOfWeekMonday,
  weekRangeLabel,
  isoWeekNumber,
} from '../utils/weekSchedule'

const props = defineProps({
  entries: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['refresh'])

const GRID_START = 7 * 60
const GRID_END = 21 * 60
const GRID_MINUTES = GRID_END - GRID_START

const weekStart = ref(startOfWeekMonday(new Date()))

const hourMarks = computed(() => {
  const marks = []
  for (let m = GRID_START; m <= GRID_END; m += 60) marks.push(m)
  return marks
})

const weekLabel = computed(() => weekRangeLabel(weekStart.value))
const isoWeek = computed(() => isoWeekNumber(weekStart.value))
const weekParity = computed(() => (isoWeek.value % 2 === 1 ? 'odd' : 'even'))

const dayColumns = computed(() => eventsForWeek(props.entries, weekStart.value, GRID_START, GRID_END))

function prevWeek() {
  weekStart.value = addDays(weekStart.value, -7)
}

function nextWeek() {
  weekStart.value = addDays(weekStart.value, 7)
}

function todayWeek() {
  weekStart.value = startOfWeekMonday(new Date())
}

function blockStyle(ev) {
  return {
    top: `${ev.topPct}%`,
    height: `${Math.max(ev.heightPct, 2.5)}%`,
    left: `calc(${ev.leftPct}% + 1px)`,
    width: `calc(${ev.widthPct}% - 2px)`,
  }
}

function timeRange(ev) {
  return `${formatMinutes(ev.startMin)}-${formatMinutes(ev.endMin)}`
}
</script>

<template>
  <div class="schedule-wrap">
    <div class="schedule-toolbar">
      <button type="button" class="teacher-btn-secondary" @click="prevWeek">Prev</button>
      <span class="schedule-week-label">{{ weekLabel }}</span>
      <button type="button" class="teacher-btn-secondary" @click="nextWeek">Next</button>
      <button type="button" class="teacher-btn-secondary" @click="todayWeek">This week</button>
      <button type="button" class="teacher-btn-secondary" :disabled="loading" @click="emit('refresh')">
        Refresh
      </button>
    </div>
    <p class="schedule-meta">
      ISO week {{ isoWeek }} ({{ weekParity }}). P weeks: even, NP weeks: odd, ALL every week.
    </p>
    <div class="schedule-legend">
      <span class="schedule-legend-item schedule-block--teaching">Teaching</span>
      <span class="schedule-legend-item schedule-block--student">My classes</span>
    </div>

    <div class="teacher-panel schedule-grid-panel">
      <div class="schedule-grid">
        <div class="schedule-time-col">
          <div class="schedule-day-head" />
          <div class="schedule-time-body" :style="{ minHeight: `${GRID_MINUTES}px` }">
            <div
              v-for="m in hourMarks"
              :key="m"
              class="schedule-hour"
              :style="{ top: `${((m - GRID_START) / GRID_MINUTES) * 100}%` }"
            >
              {{ formatMinutes(m) }}
            </div>
          </div>
        </div>
        <div v-for="(day, di) in dayColumns" :key="di" class="schedule-day-col">
          <div class="schedule-day-head">{{ WEEKDAY_LABELS[di] }}</div>
          <div class="schedule-day-body" :style="{ minHeight: `${GRID_MINUTES}px` }">
            <div
              v-for="m in hourMarks"
              :key="'line-' + m"
              class="schedule-hour-line"
              :style="{ top: `${((m - GRID_START) / GRID_MINUTES) * 100}%` }"
            />
            <div
              v-for="(ev, ei) in day"
              :key="`${ev.role}-${ev.weekday}-${ev.startMin}-${ei}`"
              class="schedule-block"
              :class="'schedule-block--' + ev.role"
              :style="blockStyle(ev)"
              :title="ev.label"
            >
              <strong>{{ ev.title }}</strong>
              <span v-if="ev.sub">{{ ev.sub }}</span>
              <span>{{ timeRange(ev) }}</span>
              <span v-if="ev.room">{{ ev.room }}</span>
              <span v-if="ev.pnp && ev.pnp !== 'ALL'">{{ ev.pnp }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.schedule-wrap {
  font-size: 0.82rem;
}

.schedule-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
  margin-bottom: 0.5rem;
}

.schedule-week-label {
  font-weight: 600;
  min-width: 11rem;
}

.schedule-meta {
  margin: 0 0 0.5rem;
  color: #4b5563;
  font-size: 0.78rem;
}

.schedule-legend {
  display: flex;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.schedule-legend-item {
  padding: 0.2rem 0.5rem;
  border: 1px solid #c5cdd6;
}

.schedule-grid-panel {
  overflow-x: auto;
}

.schedule-grid {
  display: flex;
  min-width: 640px;
}

.schedule-time-col {
  width: 3.25rem;
  flex-shrink: 0;
}

.schedule-day-col {
  flex: 1;
  min-width: 0;
  border-left: 1px solid #e8ecf0;
}

.schedule-day-head {
  height: 2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f0f3f7;
  border-bottom: 1px solid #e8ecf0;
  font-weight: 600;
  font-size: 0.75rem;
}

.schedule-time-body,
.schedule-day-body {
  position: relative;
}

.schedule-hour {
  position: absolute;
  left: 0;
  right: 0;
  transform: translateY(-50%);
  font-size: 0.68rem;
  color: #6b7280;
  padding-right: 0.25rem;
  text-align: right;
}

.schedule-hour-line {
  position: absolute;
  left: 0;
  right: 0;
  border-top: 1px solid #eef1f4;
  pointer-events: none;
}

.schedule-block {
  position: absolute;
  box-sizing: border-box;
  padding: 0.2rem 0.25rem;
  overflow: hidden;
  font-size: 0.65rem;
  line-height: 1.25;
  border: 1px solid rgba(0, 0, 0, 0.12);
  display: flex;
  flex-direction: column;
  gap: 0.05rem;
}

.schedule-block strong {
  font-weight: 600;
  font-size: 0.68rem;
}

.schedule-block--teaching {
  background: #bfdbfe;
}

.schedule-block--student {
  background: #fef08a;
}

.schedule-legend-item.schedule-block--teaching {
  background: #bfdbfe;
}

.schedule-legend-item.schedule-block--student {
  background: #fef08a;
}
</style>
