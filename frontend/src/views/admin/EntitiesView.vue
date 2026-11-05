<script setup>
import { ref } from 'vue'
import { admin } from '../../api/client'
import { useApiCall } from '../../composables/useApiCall'
import ApiMessages from '../../components/ApiMessages.vue'
import JsonPreview from '../../components/JsonPreview.vue'

const facultyApi = useApiCall()
const roomApi = useApiCall()
const cycleApi = useApiCall()
const subjectApi = useApiCall()
const curriculumApi = useApiCall()
const termApi = useApiCall()
const groupTypeApi = useApiCall()
const groupApi = useApiCall()
const assignTeacherApi = useApiCall()

const faculty = ref({ name: '', full_name: '' })
const room = ref({ building: '', room_num: '' })
const cycle = ref({ year: '2025', season: 'winter' })
const subject = ref({ code: '', name: '', ects: '' })
const curriculum = ref({ programme_id: '', intake_year: '2024' })
const term = ref({ sem: 1, curriculum_id: '', cycle_id: '' })
const groupType = ref({ subject_code: '', g_type: 'wykład', weight: 1 })
const group = ref({
  weekday: 1,
  g_type: 'wykład',
  number: 1,
  pnp: 'P',
  capacity: 30,
  start_hr: '08:00:00',
  end_time: '09:30:00',
  instance_id: '',
  room_id: '',
})
const assign = ref({ teacher_idx: '', group_id: '' })
</script>

<template>
  <div>
    <h1>Create entities</h1>

    <section class="block">
      <h2>POST /admin/faculties</h2>
      <form
        class="form"
        @submit.prevent="facultyApi.run(() => admin.createFaculty(faculty))"
      >
        <input v-model="faculty.name" placeholder="name" required />
        <input v-model="faculty.full_name" placeholder="full_name" required />
        <button type="submit" :disabled="facultyApi.loading">Create</button>
      </form>
      <ApiMessages :error="facultyApi.error" :api-message="facultyApi.apiMessage" />
      <JsonPreview :data="facultyApi.result" />
    </section>

    <section class="block">
      <h2>POST /admin/rooms</h2>
      <form class="form" @submit.prevent="roomApi.run(() => admin.createRoom(room))">
        <input v-model="room.building" placeholder="building" required />
        <input v-model="room.room_num" placeholder="room_num" required />
        <button type="submit" :disabled="roomApi.loading">Create</button>
      </form>
      <ApiMessages :error="roomApi.error" :api-message="roomApi.apiMessage" />
      <JsonPreview :data="roomApi.result" />
    </section>

    <section class="block">
      <h2>POST /admin/academic-cycles</h2>
      <form class="form" @submit.prevent="cycleApi.run(() => admin.createAcademicCycle(cycle))">
        <input v-model="cycle.year" placeholder="year" required />
        <input v-model="cycle.season" placeholder="season" required />
        <button type="submit" :disabled="cycleApi.loading">Create</button>
      </form>
      <ApiMessages :error="cycleApi.error" :api-message="cycleApi.apiMessage" />
      <JsonPreview :data="cycleApi.result" />
    </section>

    <section class="block">
      <h2>POST /admin/subjects</h2>
      <form
        class="form"
        @submit.prevent="
          subjectApi.run(() =>
            admin.createSubject({
              code: subject.code,
              name: subject.name,
              ects: subject.ects ? Number(subject.ects) : null,
            }),
          )
        "
      >
        <input v-model="subject.code" placeholder="code" required />
        <input v-model="subject.name" placeholder="name" required />
        <input v-model="subject.ects" placeholder="ects (optional)" type="number" />
        <button type="submit" :disabled="subjectApi.loading">Create</button>
      </form>
      <ApiMessages :error="subjectApi.error" :api-message="subjectApi.apiMessage" />
      <JsonPreview :data="subjectApi.result" />
    </section>

    <section class="block">
      <h2>POST /admin/curricula</h2>
      <form class="form" @submit.prevent="curriculumApi.run(() => admin.createCurriculum(curriculum))">
        <input v-model="curriculum.programme_id" placeholder="programme_id" required />
        <input v-model="curriculum.intake_year" placeholder="intake_year" required />
        <button type="submit" :disabled="curriculumApi.loading">Create</button>
      </form>
      <ApiMessages :error="curriculumApi.error" :api-message="curriculumApi.apiMessage" />
      <JsonPreview :data="curriculumApi.result" />
    </section>

    <section class="block">
      <h2>POST /admin/curriculum-terms</h2>
      <form
        class="form"
        @submit.prevent="
          termApi.run(() =>
            admin.createCurriculumTerm({
              sem: Number(term.sem),
              curriculum_id: term.curriculum_id,
              cycle_id: term.cycle_id,
            }),
          )
        "
      >
        <input v-model="term.sem" type="number" placeholder="sem" required />
        <input v-model="term.curriculum_id" placeholder="curriculum_id" required />
        <input v-model="term.cycle_id" placeholder="cycle_id" required />
        <button type="submit" :disabled="termApi.loading">Create</button>
      </form>
      <ApiMessages :error="termApi.error" :api-message="termApi.apiMessage" />
      <JsonPreview :data="termApi.result" />
    </section>

    <section class="block">
      <h2>POST /admin/group-types</h2>
      <form
        class="form"
        @submit.prevent="
          groupTypeApi.run(() =>
            admin.createGroupType({
              ...groupType,
              weight: Number(groupType.weight),
            }),
          )
        "
      >
        <input v-model="groupType.subject_code" placeholder="subject_code" required />
        <input v-model="groupType.g_type" placeholder="g_type" required />
        <input v-model="groupType.weight" type="number" step="0.1" placeholder="weight" required />
        <button type="submit" :disabled="groupTypeApi.loading">Create</button>
      </form>
      <ApiMessages :error="groupTypeApi.error" :api-message="groupTypeApi.apiMessage" />
      <JsonPreview :data="groupTypeApi.result" />
    </section>

    <section class="block">
      <h2>POST /admin/groups</h2>
      <form
        class="form"
        @submit.prevent="
          groupApi.run(() =>
            admin.createGroup({
              ...group,
              weekday: Number(group.weekday),
              number: Number(group.number),
              capacity: Number(group.capacity),
            }),
          )
        "
      >
        <input v-for="(_, key) in group" :key="key" v-model="group[key]" :placeholder="key" />
        <button type="submit" :disabled="groupApi.loading">Create</button>
      </form>
      <ApiMessages :error="groupApi.error" :api-message="groupApi.apiMessage" />
      <JsonPreview :data="groupApi.result" />
    </section>

    <section class="block">
      <h2>POST /admin/groups/teachers</h2>
      <form
        class="form"
        @submit.prevent="assignTeacherApi.run(() => admin.assignTeacherToGroup(assign))"
      >
        <input v-model="assign.teacher_idx" placeholder="teacher_idx" required />
        <input v-model="assign.group_id" placeholder="group_id" required />
        <button type="submit" :disabled="assignTeacherApi.loading">Assign</button>
      </form>
      <ApiMessages :error="assignTeacherApi.error" :api-message="assignTeacherApi.apiMessage" />
      <JsonPreview :data="assignTeacherApi.result" />
    </section>
  </div>
</template>

<style scoped>
.block {
  margin-bottom: 2rem;
}
.form {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-width: 24rem;
}
.block h2 {
  font-size: 1rem;
}
</style>
