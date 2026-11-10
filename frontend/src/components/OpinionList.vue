<script setup>
import { onMounted, watch } from 'vue'
import { catalogue } from '../api/client'
import { useApiCall } from '../composables/useApiCall'
import ApiMessages from './ApiMessages.vue'

const props = defineProps({
  teacherIdx: { type: String, default: '' },
  groupId: { type: String, default: '' },
})

const api = useApiCall()

function load() {
  if (!props.teacherIdx && !props.groupId) return
  api.run(() =>
    catalogue.opinions({
      teacher_idx: props.teacherIdx || null,
      group_id: props.groupId || null,
    }),
  )
}

function formatDate(value) {
  return value ? String(value).slice(0, 10) : ''
}

onMounted(load)
watch(() => [props.teacherIdx, props.groupId], load)
</script>

<template>
  <section class="opinions">
    <h2 class="catalogue-subsection-title">
      Opinions
      <span v-if="api.result?.avg_grade != null" class="opinions__avg">
        average {{ api.result.avg_grade.toFixed(2) }} ({{ api.result.opinions.length }})
      </span>
    </h2>
    <ApiMessages :error="api.error" />
    <p v-if="api.result && !api.result.opinions?.length" class="page-empty">No opinions yet.</p>
    <ul v-if="api.result?.opinions?.length" class="opinions__list">
      <li v-for="o in api.result.opinions" :key="o.id" class="opinions__item">
        <div class="opinions__head">
          <strong>{{ o.grade }}</strong>
          <span>{{ o.course_code }} {{ o.course_name }}, {{ o.g_type }}, {{ o.cycle }}</span>
          <span v-if="!teacherIdx">· {{ o.teacher }}</span>
          <span class="opinions__date">{{ formatDate(o.submit) }}</span>
        </div>
        <p v-if="o.content" class="opinions__content">{{ o.content }}</p>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.opinions {
  margin-top: 1rem;
}
.opinions__avg {
  font-weight: 400;
  font-size: 0.82rem;
  color: #5c6570;
  margin-left: 0.5rem;
}
.opinions__list {
  list-style: none;
  padding: 0;
  margin: 0;
}
.opinions__item {
  border-top: 1px solid #e8ecf0;
  padding: 0.5rem 0;
}
.opinions__head {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  font-size: 0.85rem;
}
.opinions__date {
  margin-left: auto;
  color: #5c6570;
}
.opinions__content {
  margin: 0.25rem 0 0;
  font-size: 0.88rem;
  white-space: pre-wrap;
}
</style>
