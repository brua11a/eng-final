const BASE = import.meta.env.VITE_API_URL ?? ''

export class ApiError extends Error {
  constructor(message, { status, detail, body } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
    this.body = body
  }
}

function normalizeDetail(body) {
  if (!body || typeof body !== 'object') return null
  if (typeof body.detail === 'string') return body.detail
  if (typeof body.err === 'string') return body.err
  if (body.ok === false && typeof body.err === 'string') return body.err
  return null
}

const STORAGE_KEY = 'eng_final_auth'

let onUnauthorized = null
export function setUnauthorizedHandler(fn) {
  onUnauthorized = fn
}

function readPersistedAuth() {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function getAuthToken() {
  const direct = sessionStorage.getItem('auth_token')
  if (direct) return direct
  const saved = readPersistedAuth()
  if (saved?.token) {
    sessionStorage.setItem('auth_token', saved.token)
    return saved.token
  }
  return null
}

export function setAuthToken(token) {
  if (token) sessionStorage.setItem('auth_token', token)
  else sessionStorage.removeItem('auth_token')
}

async function parseJsonResponse(res) {
  const text = await res.text()
  if (!text) return {}
  try {
    return JSON.parse(text)
  } catch {
    throw new ApiError('Invalid JSON response', { status: res.status, body: text })
  }
}

export async function apiRequest(path, opts = {}) {
  const { method = 'GET', body, auth = true, query } = opts
  let url = `${BASE}${path}`
  if (query) {
    const params = new URLSearchParams()
    for (const [k, v] of Object.entries(query)) {
      if (v != null && v !== '') params.set(k, v)
    }
    const qs = params.toString()
    if (qs) url += `?${qs}`
  }

  const headers = { Accept: 'application/json' }
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (auth) {
    const token = getAuthToken()
    if (token) headers.Authorization = `Bearer ${token}`
  }

  const res = await fetch(url, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })

  const data = await parseJsonResponse(res)

  if (res.status === 401) {
    setAuthToken(null)
    sessionStorage.removeItem(STORAGE_KEY)
    onUnauthorized?.()
    throw new ApiError(data.detail || 'Unauthorized', {
      status: 401,
      detail: data.detail,
      body: data,
    })
  }

  if (!res.ok) {
    throw new ApiError(data.detail || res.statusText || 'Request failed', {
      status: res.status,
      detail: data.detail,
      body: data,
    })
  }

  const inlineErr = normalizeDetail(data)
  if (inlineErr && data.ok === false) {
    return { ...data, _apiMessage: inlineErr }
  }
  if (typeof data.err === 'string' && data.err) {
    return { ...data, _apiMessage: data.err }
  }

  return data
}

export async function login(email, password) {
  const data = await apiRequest('/login', {
    method: 'POST',
    body: { email, password },
    auth: false,
  })
  if (!data.ok) {
    return { ok: false, err: data.err || 'Login failed' }
  }
  return data
}

export const catalogue = {
  teachers: (name) => apiRequest('/teachers', { query: { name } }),
  subjects: (name, code) => apiRequest('/subjects', { query: { name, code } }),
  curricula: (name) => apiRequest('/curricula', { query: { name } }),
  organizationalUnits: (name) => apiRequest('/organizational-units', { query: { name } }),
  subjectDetail: (code) => apiRequest('/subjects/detail', { method: 'POST', body: { code } }),
  subjectGroups: (subject_code, cycle_id) =>
    apiRequest('/subjects/groups', { method: 'POST', body: { subject_code, cycle_id } }),
  groupDetail: (group_id) => apiRequest('/groups/detail', { method: 'POST', body: { group_id } }),
  teacherDetail: (idx) => apiRequest('/teachers/detail', { method: 'POST', body: { idx } }),
  opinions: (query) => apiRequest('/opinions/list', { method: 'POST', body: query }),
}

export const student = {
  registrations: () => apiRequest('/me/registrations'),
  registrationCourses: (registration_id) =>
    apiRequest('/me/registrations/courses', { method: 'POST', body: { registration_id } }),
  registrationGroups: (registration_id, subject_code) =>
    apiRequest('/me/registrations/groups', {
      method: 'POST',
      body: { registration_id, subject_code },
    }),
  register: (subject_code, group_id) =>
    apiRequest('/me/registrations/register', { method: 'POST', body: { subject_code, group_id } }),
  deregister: (subject_code, group_id) =>
    apiRequest('/me/registrations/deregister', { method: 'POST', body: { subject_code, group_id } }),
  enrolments: () => apiRequest('/me/enrolments'),
  academicCycles: () => apiRequest('/me/academic-cycles'),
  academicCycleDetail: (cycle_id) =>
    apiRequest('/me/academic-cycles/detail', { method: 'POST', body: { cycle_id } }),
  dashboard: () => apiRequest('/me/dashboard'),
  createOpinion: (body) => apiRequest('/opinions', { method: 'POST', body }),
}

export const teacher = {
  myGroups: (query) => apiRequest('/me/groups', { query }),
  studentDetail: (student_idx) =>
    apiRequest('/students/detail', { method: 'POST', body: { student_idx } }),
  groupStudents: (group_id) =>
    apiRequest('/groups/students', { method: 'POST', body: { group_id } }),
  setGrade: (group_id, student_idx, grade) =>
    apiRequest('/groups/students/grade', {
      method: 'POST',
      body: { group_id, student_idx, grade },
    }),
}

export const admin = {
  createTeacher: (body) => apiRequest('/admin/teachers', { method: 'POST', body }),
  createStudent: (body) => apiRequest('/admin/students', { method: 'POST', body }),
  assignUser: (body) => apiRequest('/admin/users', { method: 'POST', body }),
  deactivateUser: (idx) =>
    apiRequest('/admin/users/deactivate', { method: 'POST', body: { idx } }),
  activateUser: (idx) =>
    apiRequest('/admin/users/activate', { method: 'POST', body: { idx } }),
  addRole: (body) => apiRequest('/admin/users/roles', { method: 'POST', body }),
  removeRole: (body) => apiRequest('/admin/users/roles/remove', { method: 'POST', body }),
  createFaculty: (body) => apiRequest('/admin/faculties', { method: 'POST', body }),
  listFaculties: () => apiRequest('/organizational-units'),
  listProgrammes: () => apiRequest('/admin/programmes'),
  listRooms: () => apiRequest('/admin/rooms'),
  listAcademicCycles: () => apiRequest('/admin/academic-cycles'),
  listSubjects: () => apiRequest('/admin/subjects'),
  listCurricula: () => apiRequest('/admin/curricula'),
  listTeachers: () => apiRequest('/admin/teachers'),
  listGroups: () => apiRequest('/admin/groups'),
  createRoom: (body) => apiRequest('/admin/rooms', { method: 'POST', body }),
  createAcademicCycle: (body) => apiRequest('/admin/academic-cycles', { method: 'POST', body }),
  createSubject: (body) => apiRequest('/admin/subjects', { method: 'POST', body }),
  createCurriculumTerm: (body) => apiRequest('/admin/curriculum-terms', { method: 'POST', body }),
  createCurriculum: (body) => apiRequest('/admin/curricula', { method: 'POST', body }),
  createGroupType: (body) => apiRequest('/admin/group-types', { method: 'POST', body }),
  createGroup: (body) => apiRequest('/admin/groups', { method: 'POST', body }),
  assignTeacherToGroup: (body) => apiRequest('/admin/groups/teachers', { method: 'POST', body }),
  startRegistrations: (body) => apiRequest('/admin/registrations', { method: 'POST', body }),
  createOpinion: (body) => apiRequest('/opinions', { method: 'POST', body }),
  createAdmin: (body) => apiRequest('/admin/admins', { method: 'POST', body }),
  removeUser: (idx) => apiRequest('/admin/users/remove', { method: 'POST', body: { idx } }),
  createProgramme: (body) => apiRequest('/admin/programmes', { method: 'POST', body }),
  addSubjectToTerm: (body) => apiRequest('/admin/curriculum-terms/subjects', { method: 'POST', body }),
  enrolStudent: (body) => apiRequest('/admin/students/enrol', { method: 'POST', body }),
  assignStudentsToTurn: (body) =>
    apiRequest('/admin/registrations/turns/students', { method: 'POST', body }),
  deanRegister: (body) => apiRequest('/admin/groups/students', { method: 'POST', body }),
  listStudents: () => apiRequest('/admin/students'),
  listTerms: () => apiRequest('/admin/curriculum-terms'),
  listTurns: () => apiRequest('/admin/registration-turns'),
}
