// The API is served under /api. VITE_API_URL can point at another host (e.g. http://localhost:8000).
const BASE = `${import.meta.env.VITE_API_URL ?? ''}/api`

export class ApiError extends Error {
  constructor(message, { status, detail, body } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
    this.body = body
  }
}

// Errors come as {"detail": "..."}; validation errors (422 from FastAPI) as {"detail": [{msg, loc}, ...]}.
function errorDetail(body) {
  if (!body || typeof body !== 'object') return null
  if (typeof body.detail === 'string') return body.detail
  if (Array.isArray(body.detail)) {
    return body.detail.map((d) => `${(d.loc || []).slice(1).join('.')}: ${d.msg}`).join('; ')
  }
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

// Escapes a value used as one segment of a URL path.
const seg = (value) => encodeURIComponent(String(value))

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

  // 401 on a call with a token means the session expired; on login it means wrong credentials.
  if (res.status === 401 && auth) {
    setAuthToken(null)
    sessionStorage.removeItem(STORAGE_KEY)
    onUnauthorized?.()
    throw new ApiError(errorDetail(data) || 'Unauthorized', {
      status: 401,
      detail: errorDetail(data),
      body: data,
    })
  }

  if (!res.ok) {
    const detail = errorDetail(data)
    throw new ApiError(detail || res.statusText || 'Request failed', {
      status: res.status,
      detail,
      body: data,
    })
  }

  return data
}

export async function login(email, password) {
  return apiRequest('/login', {
    method: 'POST',
    body: { email, password },
    auth: false,
  })
}

export const catalogue = {
  teachers: (name) => apiRequest('/teachers', { query: { name } }),
  subjects: (name, code) => apiRequest('/subjects', { query: { name, code } }),
  curricula: (name) => apiRequest('/curricula', { query: { name } }),
  organizationalUnits: (name) => apiRequest('/faculties', { query: { name } }),
  teacherGroups: (idx) => apiRequest(`/teachers/${seg(idx)}/groups`),
  subjectDetail: (code) => apiRequest(`/subjects/${seg(code)}`),
  subjectGroups: (subject_code, cycle_id) =>
    apiRequest(`/subjects/${seg(subject_code)}/groups`, { query: { cycle_id } }),
  groupDetail: (group_id) => apiRequest(`/groups/${seg(group_id)}`),
  teacherDetail: (idx) => apiRequest(`/teachers/${seg(idx)}`),
  opinions: (query) => apiRequest('/opinions', { query }),
}

export const student = {
  registrations: () => apiRequest('/me/registrations'),
  registrationCourses: (registration_id) =>
    apiRequest(`/me/registrations/${seg(registration_id)}/subjects`),
  registrationGroups: (registration_id, subject_code) =>
    apiRequest(`/me/registrations/${seg(registration_id)}/groups`, { query: { subject_code } }),
  register: (group_id) => apiRequest(`/me/registered-groups/${seg(group_id)}`, { method: 'PUT' }),
  deregister: (group_id) => apiRequest(`/me/registered-groups/${seg(group_id)}`, { method: 'DELETE' }),
  enrolments: () => apiRequest('/me/enrolments'),
  academicCycles: () => apiRequest('/me/academic-cycles'),
  academicCycleDetail: (cycle_id) => apiRequest(`/me/academic-cycles/${seg(cycle_id)}`),
  registeredGroups: () => apiRequest('/me/registered-groups'),
  createOpinion: (body) => apiRequest('/opinions', { method: 'POST', body }),
}

export const teacher = {
  myGroups: () => apiRequest('/me/groups'),
  studentDetail: (student_idx) => apiRequest(`/students/${seg(student_idx)}`),
  groupStudents: (group_id) => apiRequest(`/groups/${seg(group_id)}/students`),
  setGrade: (group_id, student_idx, grade) =>
    apiRequest(`/groups/${seg(group_id)}/students/${seg(student_idx)}/grade`, {
      method: 'PUT',
      body: { grade },
    }),
}

export const admin = {
  createTeacher: (body) => apiRequest('/admin/teachers', { method: 'POST', body }),
  createStudent: (body) => apiRequest('/admin/students', { method: 'POST', body }),
  assignUser: (body) => apiRequest('/admin/users', { method: 'POST', body }),
  deactivateUser: (idx) =>
    apiRequest(`/admin/users/${seg(idx)}`, { method: 'PATCH', body: { active: false } }),
  activateUser: (idx) =>
    apiRequest(`/admin/users/${seg(idx)}`, { method: 'PATCH', body: { active: true } }),
  addRole: ({ idx, role, ...details }) =>
    apiRequest(`/admin/users/${seg(idx)}/roles/${seg(role)}`, { method: 'PUT', body: details }),
  removeRole: ({ idx, role }) =>
    apiRequest(`/admin/users/${seg(idx)}/roles/${seg(role)}`, { method: 'DELETE' }),
  createFaculty: (body) => apiRequest('/admin/faculties', { method: 'POST', body }),
  listFaculties: () => apiRequest('/faculties'),
  listProgrammes: () => apiRequest('/admin/programmes'),
  listRooms: () => apiRequest('/admin/rooms'),
  listAcademicCycles: () => apiRequest('/admin/academic-cycles'),
  listSubjects: () => apiRequest('/admin/subjects'),
  listCurricula: () => apiRequest('/admin/curricula'),
  listTeachers: () => apiRequest('/admin/teachers'),
  listGroups: () => apiRequest('/admin/groups'),
  createRoom: (body) => apiRequest('/admin/rooms', { method: 'POST', body }),
  createAcademicCycle: (body) => apiRequest('/admin/academic-cycles', { method: 'POST', body }),
  createSubject: ({ code, ...body }) =>
    apiRequest(`/admin/subjects/${seg(code)}`, { method: 'PUT', body }),
  createCurriculumTerm: (body) => apiRequest('/admin/curriculum-terms', { method: 'POST', body }),
  createCurriculum: (body) => apiRequest('/admin/curricula', { method: 'POST', body }),
  createGroupType: (body) => apiRequest('/admin/group-types', { method: 'POST', body }),
  createGroup: (body) => apiRequest('/admin/groups', { method: 'POST', body }),
  assignTeacherToGroup: (body) => apiRequest('/admin/groups/teachers', { method: 'POST', body }),
  startRegistrations: (body) => apiRequest('/admin/registrations', { method: 'POST', body }),
  createOpinion: (body) => apiRequest('/opinions', { method: 'POST', body }),
  createAdmin: (body) => apiRequest('/admin/admins', { method: 'POST', body }),
  // 204 No Content: return the idx so the view can say whose login was removed.
  removeUser: (idx) =>
    apiRequest(`/admin/users/${seg(idx)}`, { method: 'DELETE' }).then(() => ({ idx })),
  createProgramme: (body) => apiRequest('/admin/programmes', { method: 'POST', body }),
  addSubjectToTerm: (body) => apiRequest('/admin/curriculum-terms/subjects', { method: 'POST', body }),
  enrolStudent: ({ student_idx, term_id }) =>
    apiRequest(`/admin/students/${seg(student_idx)}/enrolments`, { method: 'POST', body: { term_id } }),
  assignStudentsToTurn: (body) =>
    apiRequest('/admin/registrations/turns/students', { method: 'POST', body }),
  deanRegister: (body) => apiRequest('/admin/groups/students', { method: 'POST', body }),
  nextIdx: () => apiRequest('/admin/people/next-idx'),
  listStudents: () => apiRequest('/admin/students'),
  listTerms: () => apiRequest('/admin/curriculum-terms'),
  listTurns: () => apiRequest('/admin/registration-turns'),
}
