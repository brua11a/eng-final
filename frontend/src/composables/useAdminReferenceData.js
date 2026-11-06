import { onMounted, ref } from 'vue'
import { admin } from '../api/client'
import { cycleLabel, errorMessage, teacherLabel } from '../utils/format'

export function useAdminReferenceData() {
  const faculties = ref([])
  const programmes = ref([])
  const rooms = ref([])
  const cycles = ref([])
  const subjects = ref([])
  const curricula = ref([])
  const teachers = ref([])
  const groups = ref([])
  const loading = ref(false)
  const error = ref('')

  async function load() {
    loading.value = true
    error.value = ''
    try {
      const [f, p, r, c, su, cur, t, g] = await Promise.all([
        admin.listFaculties(),
        admin.listProgrammes(),
        admin.listRooms(),
        admin.listAcademicCycles(),
        admin.listSubjects(),
        admin.listCurricula(),
        admin.listTeachers(),
        admin.listGroups(),
      ])
      faculties.value = f.faculties || []
      programmes.value = p.programmes || []
      rooms.value = r.rooms || []
      cycles.value = c.cycles || []
      subjects.value = su.subjects || []
      curricula.value = cur.curricula || []
      teachers.value = t.teachers || []
      groups.value = g.groups || []
    } catch (e) {
      error.value = errorMessage(e)
    } finally {
      loading.value = false
    }
  }

  onMounted(load)

  function facultyLabel(f) {
    return f.name
  }

  function programmeLabel(p) {
    const fac = faculties.value.find((x) => x.id === p.faculty_id)
    const tag = fac?.name ? ` (${fac.name})` : ''
    return `${p.name}${tag}`
  }

  function roomLabel(r) {
    return `${r.building} ${r.room_num}`
  }

  return {
    faculties,
    programmes,
    rooms,
    cycles,
    subjects,
    curricula,
    teachers,
    groups,
    loading,
    error,
    load,
    facultyLabel,
    programmeLabel,
    roomLabel,
    cycleLabel,
    teacherLabel,
  }
}
