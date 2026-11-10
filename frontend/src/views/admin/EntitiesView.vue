<script setup>
import { ref } from 'vue'
import { admin } from '../../api/client'
import { useApiCall } from '../../composables/useApiCall'
import { useAdminReferenceData } from '../../composables/useAdminReferenceData'
import ApiMessages from '../../components/ApiMessages.vue'

const {
  faculties,
  programmes,
  terms,
  rooms,
  cycles,
  subjects,
  curricula,
  teachers,
  groups,
  facultyLabel,
  programmeLabel,
  roomLabel,
  cycleLabel,
  teacherLabel,
  error: refsError,
  load: reloadRefs,
} = useAdminReferenceData()

async function create(api, fn) {
  const data = await api.run(fn)
  if (data && !api.apiMessage) reloadRefs()
}

const facultyApi = useApiCall()
const roomApi = useApiCall()
const cycleApi = useApiCall()
const subjectApi = useApiCall()
const curriculumApi = useApiCall()
const termApi = useApiCall()
const groupTypeApi = useApiCall()
const groupApi = useApiCall()
const assignTeacherApi = useApiCall()
const programmeApi = useApiCall()
const termSubjectApi = useApiCall()

const faculty = ref({ name: '', full_name: '' })
const room = ref({ building: '', room_num: '' })
const cycle = ref({ year: '2026/27', season: 'Z', start_date: '2026-10-01', end_date: '2027-02-03' })
const subject = ref({ code: '', name: '', ects: '' })
const curriculum = ref({ programme_id: '', intake_year: '2024' })
const term = ref({ sem: 1, curriculum_id: '', cycle_id: '' })
const groupType = ref({ subject_code: '', cycle_id: '', g_type: 'wykład', weight: 1 })
const group = ref({
  weekday: 1,
  g_type: 'wykład',
  number: 1,
  pnp: 'P',
  capacity: 30,
  start_hr: '08:00:00',
  end_time: '09:30:00',
  subject_code: '',
  cycle_id: '',
  room_id: '',
})
const assign = ref({ teacher_idx: '', group_id: '' })
const programme = ref({ name: '', faculty_id: '' })
const termSubject = ref({ term_id: '', subject_code: '' })
</script>

<template>
  <div>
    <h1 class="teacher-page-title">Entities</h1>
    <ApiMessages v-if="refsError" :error="refsError" />

    <section class="teacher-panel admin-panel-spaced">
      <h2 class="admin-section-title">Faculty</h2>
      <form class="admin-form" @submit.prevent="create(facultyApi, () => admin.createFaculty(faculty))">
        <label>Short name (e.g. W4N) <input v-model="faculty.name" required /></label>
        <label>Full name <input v-model="faculty.full_name" required /></label>
        <button type="submit" class="teacher-btn-save" :disabled="facultyApi.loading">Create</button>
      </form>
      <ApiMessages :error="facultyApi.error" :api-message="facultyApi.apiMessage" />
      <p v-if="facultyApi.result?.id && !facultyApi.apiMessage" class="admin-ok">Id {{ facultyApi.result.id }}</p>
    </section>

    <section class="teacher-panel admin-panel-spaced">
      <h2 class="admin-section-title">Programme</h2>
      <form class="admin-form" @submit.prevent="create(programmeApi, () => admin.createProgramme(programme))">
        <label>Name <input v-model="programme.name" required /></label>
        <label>
          Faculty
          <select v-model="programme.faculty_id" required>
            <option value="" disabled>Select faculty</option>
            <option v-for="f in faculties" :key="f.id" :value="f.id">
              {{ facultyLabel(f) }}
            </option>
          </select>
        </label>
        <button type="submit" class="teacher-btn-save" :disabled="programmeApi.loading">Create</button>
      </form>
      <ApiMessages :error="programmeApi.error" :api-message="programmeApi.apiMessage" />
      <p v-if="programmeApi.result?.id && !programmeApi.apiMessage" class="admin-ok">Id {{ programmeApi.result.id }}</p>
    </section>

    <section class="teacher-panel admin-panel-spaced">
      <h2 class="admin-section-title">Room</h2>
      <form class="admin-form" @submit.prevent="create(roomApi, () => admin.createRoom(room))">
        <label>Building <input v-model="room.building" required /></label>
        <label>Room number <input v-model="room.room_num" required /></label>
        <button type="submit" class="teacher-btn-save" :disabled="roomApi.loading">Create</button>
      </form>
      <ApiMessages :error="roomApi.error" :api-message="roomApi.apiMessage" />
      <p v-if="roomApi.result?.id && !roomApi.apiMessage" class="admin-ok">Id {{ roomApi.result.id }}</p>
    </section>

    <section class="teacher-panel admin-panel-spaced">
      <h2 class="admin-section-title">Academic cycle</h2>
      <form class="admin-form" @submit.prevent="create(cycleApi, () => admin.createAcademicCycle(cycle))">
        <label>Year <input v-model="cycle.year" required /></label>
        <label>Season <input v-model="cycle.season" required /></label>
        <label>Classes start <input v-model="cycle.start_date" type="date" required /></label>
        <label>Classes end <input v-model="cycle.end_date" type="date" required /></label>
        <button type="submit" class="teacher-btn-save" :disabled="cycleApi.loading">Create</button>
      </form>
      <ApiMessages :error="cycleApi.error" :api-message="cycleApi.apiMessage" />
      <p v-if="cycleApi.result?.id && !cycleApi.apiMessage" class="admin-ok">Id {{ cycleApi.result.id }}</p>
    </section>

    <section class="teacher-panel admin-panel-spaced">
      <h2 class="admin-section-title">Subject</h2>
      <form
        class="admin-form"
        @submit.prevent="
          create(subjectApi, () =>
            admin.createSubject({
              code: subject.code,
              name: subject.name,
              ects: subject.ects ? Number(subject.ects) : null,
            }),
          )
        "
      >
        <label>Code <input v-model="subject.code" required /></label>
        <label>Name <input v-model="subject.name" required /></label>
        <label>ECTS <input v-model="subject.ects" type="number" /></label>
        <button type="submit" class="teacher-btn-save" :disabled="subjectApi.loading">Create</button>
      </form>
      <ApiMessages :error="subjectApi.error" :api-message="subjectApi.apiMessage" />
      <p v-if="subjectApi.result?.code && !subjectApi.apiMessage" class="admin-ok">Code {{ subjectApi.result.code }}</p>
    </section>

    <section class="teacher-panel admin-panel-spaced">
      <h2 class="admin-section-title">Curriculum</h2>
      <form class="admin-form" @submit.prevent="create(curriculumApi, () => admin.createCurriculum(curriculum))">
        <label>
          Programme
          <select v-model="curriculum.programme_id" required>
            <option value="" disabled>Select programme</option>
            <option v-for="p in programmes" :key="p.id" :value="p.id">
              {{ programmeLabel(p) }}
            </option>
          </select>
        </label>
        <label>Intake year <input v-model="curriculum.intake_year" required /></label>
        <button type="submit" class="teacher-btn-save" :disabled="curriculumApi.loading">Create</button>
      </form>
      <ApiMessages :error="curriculumApi.error" :api-message="curriculumApi.apiMessage" />
      <p v-if="curriculumApi.result?.id && !curriculumApi.apiMessage" class="admin-ok">Id {{ curriculumApi.result.id }}</p>
    </section>

    <section class="teacher-panel admin-panel-spaced">
      <h2 class="admin-section-title">Curriculum term</h2>
      <form
        class="admin-form"
        @submit.prevent="
          create(termApi, () =>
            admin.createCurriculumTerm({
              sem: Number(term.sem),
              curriculum_id: term.curriculum_id,
              cycle_id: term.cycle_id,
            }),
          )
        "
      >
        <label>Semester <input v-model="term.sem" type="number" required /></label>
        <label>
          Curriculum
          <select v-model="term.curriculum_id" required>
            <option value="" disabled>Select curriculum</option>
            <option v-for="c in curricula" :key="c.id" :value="c.id">
              {{ c.programme_name }} {{ c.intake_year }}
            </option>
          </select>
        </label>
        <label>
          Cycle
          <select v-model="term.cycle_id" required>
            <option value="" disabled>Select cycle</option>
            <option v-for="c in cycles" :key="c.id" :value="c.id">
              {{ cycleLabel(c) }}
            </option>
          </select>
        </label>
        <button type="submit" class="teacher-btn-save" :disabled="termApi.loading">Create</button>
      </form>
      <ApiMessages :error="termApi.error" :api-message="termApi.apiMessage" />
      <p v-if="termApi.result?.id && !termApi.apiMessage" class="admin-ok">Id {{ termApi.result.id }}</p>
    </section>

    <section class="teacher-panel admin-panel-spaced">
      <h2 class="admin-section-title">Subject in curriculum term</h2>
      <form class="admin-form" @submit.prevent="create(termSubjectApi, () => admin.addSubjectToTerm(termSubject))">
        <label>
          Curriculum term
          <select v-model="termSubject.term_id" required>
            <option value="" disabled>Select term</option>
            <option v-for="t in terms" :key="t.id" :value="t.id">{{ t.label }}</option>
          </select>
        </label>
        <label>
          Subject
          <select v-model="termSubject.subject_code" required>
            <option value="" disabled>Select subject</option>
            <option v-for="su in subjects" :key="su.code" :value="su.code">
              {{ su.code }} {{ su.name }}
            </option>
          </select>
        </label>
        <button type="submit" class="teacher-btn-save" :disabled="termSubjectApi.loading">Add</button>
      </form>
      <ApiMessages :error="termSubjectApi.error" :api-message="termSubjectApi.apiMessage" />
      <p v-if="termSubjectApi.result && !termSubjectApi.apiMessage" class="admin-ok">
        Added {{ termSubjectApi.result.subject_code }}
      </p>
    </section>

    <section class="teacher-panel admin-panel-spaced">
      <h2 class="admin-section-title">Group type</h2>
      <form
        class="admin-form"
        @submit.prevent="
          create(groupTypeApi, () =>
            admin.createGroupType({
              ...groupType,
              weight: Number(groupType.weight),
            }),
          )
        "
      >
        <label>
          Subject
          <select v-model="groupType.subject_code" required>
            <option value="" disabled>Select subject</option>
            <option v-for="su in subjects" :key="su.code" :value="su.code">
              {{ su.code }} {{ su.name }}
            </option>
          </select>
        </label>
        <label>
          Cycle
          <select v-model="groupType.cycle_id" required>
            <option value="" disabled>Select cycle</option>
            <option v-for="c in cycles" :key="c.id" :value="c.id">
              {{ cycleLabel(c) }}
            </option>
          </select>
        </label>
        <label>Type name <input v-model="groupType.g_type" required /></label>
        <label>Weight <input v-model="groupType.weight" type="number" step="0.1" required /></label>
        <button type="submit" class="teacher-btn-save" :disabled="groupTypeApi.loading">Create</button>
      </form>
      <ApiMessages :error="groupTypeApi.error" :api-message="groupTypeApi.apiMessage" />
      <p v-if="groupTypeApi.result?.id && !groupTypeApi.apiMessage" class="admin-ok">Id {{ groupTypeApi.result.id }}</p>
    </section>

    <section class="teacher-panel admin-panel-spaced">
      <h2 class="admin-section-title">Group</h2>
      <form
        class="admin-form"
        @submit.prevent="
          create(groupApi, () =>
            admin.createGroup({
              ...group,
              weekday: Number(group.weekday),
              number: Number(group.number),
              capacity: Number(group.capacity),
            }),
          )
        "
      >
        <label>Weekday <input v-model="group.weekday" type="number" required /></label>
        <label>Group type <input v-model="group.g_type" required /></label>
        <label>Number <input v-model="group.number" type="number" required /></label>
        <label>P/NP/ALL <input v-model="group.pnp" required /></label>
        <label>Capacity <input v-model="group.capacity" type="number" required /></label>
        <label>Start <input v-model="group.start_hr" required /></label>
        <label>End <input v-model="group.end_time" required /></label>
        <label>
          Subject
          <select v-model="group.subject_code" required>
            <option value="" disabled>Select subject</option>
            <option v-for="su in subjects" :key="su.code" :value="su.code">
              {{ su.code }} {{ su.name }}
            </option>
          </select>
        </label>
        <label>
          Cycle
          <select v-model="group.cycle_id" required>
            <option value="" disabled>Select cycle</option>
            <option v-for="c in cycles" :key="c.id" :value="c.id">
              {{ cycleLabel(c) }}
            </option>
          </select>
        </label>
        <label>
          Room
          <select v-model="group.room_id" required>
            <option value="" disabled>Select room</option>
            <option v-for="r in rooms" :key="r.id" :value="r.id">
              {{ roomLabel(r) }}
            </option>
          </select>
        </label>
        <button type="submit" class="teacher-btn-save" :disabled="groupApi.loading">Create</button>
      </form>
      <ApiMessages :error="groupApi.error" :api-message="groupApi.apiMessage" />
      <p v-if="groupApi.result?.id && !groupApi.apiMessage" class="admin-ok">Id {{ groupApi.result.id }}</p>
    </section>

    <section class="teacher-panel admin-panel-spaced">
      <h2 class="admin-section-title">Assign teacher to group</h2>
      <form class="admin-form" @submit.prevent="create(assignTeacherApi, () => admin.assignTeacherToGroup(assign))">
        <label>
          Teacher
          <select v-model="assign.teacher_idx" required>
            <option value="" disabled>Select teacher</option>
            <option v-for="t in teachers" :key="t.idx" :value="t.idx">
              {{ teacherLabel(t) }}
            </option>
          </select>
        </label>
        <label>
          Group
          <select v-model="assign.group_id" required>
            <option value="" disabled>Select group</option>
            <option v-for="g in groups" :key="g.id" :value="g.id">
              {{ g.label }}
            </option>
          </select>
        </label>
        <button type="submit" class="teacher-btn-save" :disabled="assignTeacherApi.loading">Assign</button>
      </form>
      <ApiMessages :error="assignTeacherApi.error" :api-message="assignTeacherApi.apiMessage" />
      <p v-if="assignTeacherApi.result && !assignTeacherApi.apiMessage && !assignTeacherApi.error" class="admin-ok">
        {{ assignTeacherApi.result.teacher_idx }} teaches {{ assignTeacherApi.result.group_id }}
      </p>
    </section>
  </div>
</template>
