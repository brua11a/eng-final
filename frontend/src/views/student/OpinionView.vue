<script setup>
import { onMounted, reactive, ref } from 'vue'
import { student } from '../../api/client'
import ApiMessages from '../../components/ApiMessages.vue'
import { errorMessage } from '../../utils/format'

const groups = ref([])
const loading = ref(false)
const loadError = ref('')
const drafts = reactive({})
const status = reactive({})

function groupLabel(g) {
  return [g.course_name || g.course_code, g.g_type, g.number != null ? `#${g.number}` : '']
    .filter(Boolean)
    .join(' · ')
}

async function loadGroups() {
  loading.value = true
  loadError.value = ''
  try {
    const data = await student.dashboard()
    groups.value = data?.groups || []
    for (const g of groups.value) {
      drafts[g.group_id] ??= { grade: 4.5, content: '' }
      status[g.group_id] ??= { saving: false, error: '', ok: '' }
    }
  } catch (e) {
    loadError.value = errorMessage(e)
    groups.value = []
  } finally {
    loading.value = false
  }
}

async function submitForGroup(g) {
  const st = status[g.group_id]
  const draft = drafts[g.group_id]
  Object.assign(st, { saving: true, error: '', ok: '' })
  try {
    const res = await student.createOpinion({
      grade: Number(draft.grade),
      content: draft.content.trim() || null,
      submit: new Date().toISOString(),
      group_id: g.group_id,
    })
    if (res?.err) st.error = res.err
    else st.ok = 'Saved'
  } catch (e) {
    st.error = errorMessage(e)
  } finally {
    st.saving = false
  }
}

onMounted(loadGroups)
</script>

<template>
  <div>
    <div class="page-toolbar">
      <h1 class="teacher-page-title">Submit opinion</h1>
      <button type="button" class="teacher-btn-secondary" :disabled="loading" @click="loadGroups">
        Refresh
      </button>
    </div>

    <ApiMessages :error="loadError" />

    <p v-if="!loading && !groups.length" class="page-empty">No registered groups.</p>

    <div class="opinion-grid">
      <div v-for="g in groups" :key="g.group_id" class="teacher-panel opinion-card">
        <h2 class="opinion-card-title" :title="groupLabel(g)">{{ groupLabel(g) }}</h2>
        <p class="opinion-meta">{{ g.course_code || '\u00a0' }}</p>

        <form class="opinion-form" @submit.prevent="submitForGroup(g)">
          <label>
            Grade
            <input
              v-model.number="drafts[g.group_id].grade"
              type="number"
              step="0.1"
              min="2"
              max="5"
              required
            />
          </label>
          <label>
            Content
            <textarea v-model="drafts[g.group_id].content" rows="3" placeholder="Optional comment" />
          </label>
          <div class="opinion-actions">
            <button type="submit" class="teacher-btn-save" :disabled="status[g.group_id].saving">
              {{ status[g.group_id].saving ? 'Submitting…' : 'Submit' }}
            </button>
          </div>
          <p v-if="status[g.group_id].error" class="opinion-err">{{ status[g.group_id].error }}</p>
          <p v-if="status[g.group_id].ok" class="opinion-ok">{{ status[g.group_id].ok }}</p>
        </form>
      </div>
    </div>
  </div>
</template>

<style scoped>
.opinion-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(18rem, 1fr));
  gap: 1rem;
  align-items: stretch;
}

.opinion-card {
  margin: 0;
  padding: 0.85rem 1rem;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.opinion-card-title {
  margin: 0 0 0.2rem;
  font-size: 0.95rem;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.opinion-meta {
  margin: 0 0 0.75rem;
  font-size: 0.8rem;
  color: #6b7280;
}

.opinion-form {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
  flex: 1;
}

.opinion-form textarea {
  resize: vertical;
  min-height: 4.5rem;
}

.opinion-form label {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.85rem;
}

.opinion-form input,
.opinion-form textarea {
  font: inherit;
  padding: 0.35rem 0.5rem;
  border: 1px solid #c5cdd6;
  border-radius: 2px;
}

.opinion-actions {
  margin-top: auto;
}

.opinion-err {
  margin: 0;
  color: #b91c1c;
  font-size: 0.82rem;
}

.opinion-ok {
  margin: 0;
  color: #15803d;
  font-size: 0.82rem;
}
</style>
