<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { WEEKDAYS, timeRange } from '../utils/format'

const props = defineProps({
  group: { type: Object, required: true },
  linkTeacher: { type: Boolean, default: true },
})

const schedule = computed(() => {
  const g = props.group
  return [WEEKDAYS[g.weekday] || '', g.pnp, timeRange(g.start_time, g.end_time)]
    .filter(Boolean)
    .join(', ')
})
</script>

<template>
  <dl class="group-facts">
    <div v-if="group.academic_cycle">
      <dt>Academic cycle</dt>
      <dd>{{ group.academic_cycle }}</dd>
    </div>
    <div>
      <dt>Group</dt>
      <dd>{{ group.g_type }} #{{ group.group_num }}</dd>
    </div>
    <div v-if="schedule">
      <dt>Schedule</dt>
      <dd>{{ schedule }}</dd>
    </div>
    <div v-if="group.room">
      <dt>Room</dt>
      <dd>{{ group.room }}</dd>
    </div>
    <div>
      <dt>Enrollment</dt>
      <dd>{{ group.filled }} / {{ group.capacity }}</dd>
    </div>
    <div v-if="group.teachers?.length">
      <dt>{{ group.teachers.length > 1 ? 'Instructors' : 'Instructor' }}</dt>
      <dd>
        <template v-for="(t, i) in group.teachers" :key="t.id">
          {{ i ? ', ' : '' }}
          <RouterLink
            v-if="linkTeacher && t.id"
            :to="{ name: 'catalogue-teacher-detail', params: { idx: t.id } }"
            class="group-facts__link"
          >
            {{ t.name }}
          </RouterLink>
          <span v-else>{{ t.name }}</span>
        </template>
      </dd>
    </div>
  </dl>
</template>

<style scoped>
.group-facts {
  margin: 0;
  display: grid;
  gap: 0.6rem;
}

.group-facts div {
  display: grid;
  grid-template-columns: 8.5rem 1fr;
  gap: 0.5rem;
  font-size: 0.88rem;
}

.group-facts dt {
  margin: 0;
  font-weight: 600;
  color: #1a3352;
}

.group-facts dd {
  margin: 0;
}

.group-facts__link {
  color: #e8641b;
  text-decoration: none;
}

.group-facts__link:hover {
  text-decoration: underline;
}
</style>
