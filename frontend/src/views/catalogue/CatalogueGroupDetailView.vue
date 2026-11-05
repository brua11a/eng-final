<script setup>
import { onMounted, watch, computed } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { catalogue } from '../../api/client'
import { useApiCall } from '../../composables/useApiCall'
import ApiMessages from '../../components/ApiMessages.vue'

const route = useRoute()
const api = useApiCall()

const groupId = computed(() => route.params.groupId?.toString() ?? '')

const WEEKDAYS = ['', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

const scheduleLine = computed(() => {
  const d = api.result
  if (!d) return ''
  const day = WEEKDAYS[d.weekday] || d.weekday
  const start = d.start_hr ? String(d.start_hr).slice(0, 5) : ''
  const end = d.end_time ? String(d.end_time).slice(0, 5) : ''
  const time = start && end ? `${start} – ${end}` : start || end
  const parts = [day, d.pnp, time, d.room].filter(Boolean)
  return parts.join(', ')
})

onMounted(load)
watch(groupId, load)

function load() {
  if (!groupId.value) return
  api.run(() => catalogue.groupDetail(groupId.value))
}
</script>

<template>
  <div class="group-detail">
    <p class="catalogue-hint">
      <RouterLink :to="{ name: 'catalogue-teacher-detail', params: { idx: route.query.teacher }, query: route.query }">
        ← Staff profile
      </RouterLink>
    </p>

    <h1 class="catalogue-page-title group-detail__title">
      <span v-if="api.result">{{ api.result.course_name }}</span>
      <span v-else>Group</span>
      <span v-if="api.result?.subject_code" class="group-detail__code">[{{ api.result.subject_code }}]</span>
    </h1>

    <ApiMessages :error="api.error" :api-message="api.apiMessage" />

    <div v-if="api.result" class="group-detail__panel">
      <dl class="group-detail__facts">
        <div v-if="api.result.academic_cycle">
          <dt>Academic cycle</dt>
          <dd>{{ api.result.academic_cycle }}</dd>
        </div>
        <div>
          <dt>Group</dt>
          <dd>{{ api.result.g_type }}, group {{ api.result.group_num }}</dd>
        </div>
        <div v-if="scheduleLine">
          <dt>Schedule</dt>
          <dd>{{ scheduleLine }}</dd>
        </div>
        <div v-if="api.result.room">
          <dt>Room</dt>
          <dd>{{ api.result.room }}</dd>
        </div>
        <div>
          <dt>Enrollment</dt>
          <dd>{{ api.result.filled }} / {{ api.result.capacity }}</dd>
        </div>
        <div v-if="api.result.teacher?.name">
          <dt>Instructor</dt>
          <dd>
            <RouterLink
              v-if="api.result.teacher.id"
              :to="{ name: 'catalogue-teacher-detail', params: { idx: api.result.teacher.id } }"
              class="catalogue-link-arrow"
            >
              {{ api.result.teacher.name }}
            </RouterLink>
            <span v-else>{{ api.result.teacher.name }}</span>
          </dd>
        </div>
      </dl>
    </div>
  </div>
</template>

<style scoped>
.group-detail__title {
  flex-wrap: wrap;
}
.group-detail__code {
  font-weight: 500;
  color: var(--cat-muted, #5c6570);
  font-size: 1rem;
}
.group-detail__panel {
  background: #fff;
  border: 1px solid #c5cdd6;
  padding: 1rem 1.25rem;
  max-width: 36rem;
}
.group-detail__facts {
  margin: 0;
  display: grid;
  gap: 0.75rem;
}
.group-detail__facts div {
  display: grid;
  grid-template-columns: 8.5rem 1fr;
  gap: 0.5rem;
  font-size: 0.9rem;
}
.group-detail__facts dt {
  margin: 0;
  font-weight: 600;
  color: #1a3352;
}
.group-detail__facts dd {
  margin: 0;
}
</style>
