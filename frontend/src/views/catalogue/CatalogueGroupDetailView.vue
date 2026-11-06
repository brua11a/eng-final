<script setup>
import { onMounted, watch, computed } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { catalogue } from '../../api/client'
import { useApiCall } from '../../composables/useApiCall'
import { useAuthStore } from '../../stores/auth'
import ApiMessages from '../../components/ApiMessages.vue'
import GroupFacts from '../../components/GroupFacts.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const api = useApiCall()

const groupId = computed(() => route.params.groupId?.toString() ?? '')
const fromTeacher = computed(() => route.query.teacher?.toString() ?? '')

const canGrade = computed(
  () =>
    auth.roles.includes('Teacher') &&
    auth.idx &&
    (api.result?.teachers || []).some((t) => t.id === auth.idx),
)

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
      <RouterLink
        v-if="fromTeacher"
        :to="{ name: 'catalogue-teacher-detail', params: { idx: fromTeacher }, query: route.query }"
      >
        ← Staff profile
      </RouterLink>
      <a v-else href="#" @click.prevent="router.back()">← Back</a>
    </p>

    <h1 class="catalogue-page-title group-detail__title">
      <span v-if="api.result">{{ api.result.course_name }}</span>
      <span v-else>Group</span>
      <RouterLink
        v-if="api.result?.subject_code"
        :to="{ name: 'catalogue-subject-detail', params: { code: api.result.subject_code } }"
        class="group-detail__code"
      >
        [{{ api.result.subject_code }}]
      </RouterLink>
    </h1>

    <ApiMessages :error="api.error" :api-message="api.apiMessage" />

    <div v-if="api.result" class="group-detail__panel">
      <GroupFacts :group="api.result" />
      <p v-if="canGrade" class="group-detail__actions">
        <RouterLink
          :to="{ name: 'teacher-group-grades', params: { groupId: groupId } }"
          class="catalogue-link-arrow"
        >
          Edit grades →
        </RouterLink>
      </p>
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
  text-decoration: none;
}
.group-detail__code:hover {
  text-decoration: underline;
}
.group-detail__panel {
  background: #fff;
  border: 1px solid #c5cdd6;
  padding: 1rem 1.25rem;
  max-width: 36rem;
}
.group-detail__actions {
  margin: 1rem 0 0;
  padding-top: 0.75rem;
  border-top: 1px solid #e8ecf0;
}
</style>
