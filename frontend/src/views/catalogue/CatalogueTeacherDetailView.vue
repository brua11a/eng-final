<script setup>
import { onMounted, watch } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { catalogue } from '../../api/client'
import { useApiCall } from '../../composables/useApiCall'
import ApiMessages from '../../components/ApiMessages.vue'

const route = useRoute()
const api = useApiCall()
const idx = () => route.params.idx

onMounted(load)
watch(() => route.params.idx, load)

function load() {
  api.run(() => catalogue.teacherDetail(idx()))
}

function groupLabel(g) {
  const title = g.course_name || g.course_code
  const code = g.course_name && g.course_code ? ` [${g.course_code}]` : g.course_code ? ` [${g.course_code}]` : ''
  return `${title}${code} · ${g.g_type} · group ${g.group_num}`
}
</script>

<template>
  <div>
    <h1 class="catalogue-page-title">Staff profile</h1>
    <p class="catalogue-hint">
      <RouterLink :to="{ name: 'catalogue-teachers-results', query: route.query }">
        ← Back to results
      </RouterLink>
    </p>
    <ApiMessages :error="api.error" :api-message="api.apiMessage" />
    <div v-if="api.result && !api.result.err" class="catalogue-detail-card">
      <p><strong>{{ api.result.name }}</strong></p>
      <p>{{ api.result.degree }}</p>
      <p v-if="api.result.phone">Phone: {{ api.result.phone }}</p>
      <p v-if="api.result.email">Email: {{ api.result.email }}</p>

      <h2 v-if="api.result.groups?.length" class="catalogue-subsection-title">Classes</h2>
      <ul v-if="api.result.groups?.length" class="group-list">
        <li v-for="g in api.result.groups" :key="g.group_id">
          <RouterLink
            :to="{
              name: 'catalogue-group-detail',
              params: { groupId: g.group_id },
              query: { teacher: idx() },
            }"
            class="catalogue-link-arrow"
          >
            {{ groupLabel(g) }}
          </RouterLink>
          <span v-if="g.academic_cycle" class="group-list__cycle">{{ g.academic_cycle }}</span>
        </li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.catalogue-detail-card {
  background: #fff;
  border: 1px solid #c5cdd6;
  padding: 1rem;
  font-size: 0.9rem;
}
.group-list {
  list-style: none;
  padding: 0;
  margin: 0.5rem 0 0;
}
.group-list li {
  padding: 0.35rem 0;
  border-bottom: 1px solid #e8ecf0;
}
.group-list__cycle {
  display: block;
  font-size: 0.8rem;
  color: #5c6570;
  margin-top: 0.15rem;
}
</style>
