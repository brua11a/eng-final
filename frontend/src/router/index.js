import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('../views/LoginView.vue'),
    meta: { public: true },
  },
  {
    path: '/',
    component: () => import('../layouts/AppLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: { name: 'catalogue' } },
      {
        path: 'catalogue',
        component: () => import('../views/catalogue/CatalogueLayout.vue'),
        meta: { tab: 'catalogue', layout: 'wide' },
        children: [
          { path: '', name: 'catalogue', component: () => import('../views/catalogue/CatalogueHomeView.vue') },
          { path: 'osoby', name: 'catalogue-people', component: () => import('../views/catalogue/CataloguePeopleView.vue'), meta: { catalogueSection: 'people' } },
          { path: 'jednostki', name: 'catalogue-units', component: () => import('../views/catalogue/CatalogueUnitsView.vue'), meta: { catalogueSection: 'units' } },
          { path: 'osoby/wyniki', name: 'catalogue-teachers-results', component: () => import('../views/catalogue/CatalogueTeachersResultsView.vue'), meta: { catalogueSection: 'people' } },
          { path: 'osoby/pracownik/:idx', name: 'catalogue-teacher-detail', component: () => import('../views/catalogue/CatalogueTeacherDetailView.vue'), meta: { catalogueSection: 'people' } },
          { path: 'osoby/grupa/:groupId', name: 'catalogue-group-detail', component: () => import('../views/catalogue/CatalogueGroupDetailView.vue'), meta: { catalogueSection: 'people' } },
          { path: 'przedmioty/wyniki', name: 'catalogue-subjects-results', component: () => import('../views/catalogue/CatalogueSubjectsResultsView.vue'), meta: { catalogueSection: 'subjects' } },
          { path: 'przedmioty/szczegoly/:code', name: 'catalogue-subject-detail', component: () => import('../views/catalogue/CatalogueSubjectDetailView.vue'), meta: { catalogueSection: 'subjects' } },
          { path: 'przedmioty', name: 'catalogue-subjects', component: () => import('../views/catalogue/CatalogueSubjectsView.vue'), meta: { catalogueSection: 'subjects' } },
          { path: 'jednostki/wyniki', name: 'catalogue-units-results', component: () => import('../views/catalogue/CatalogueUnitsResultsView.vue'), meta: { catalogueSection: 'units' } },
          { path: 'studia/wyniki', name: 'catalogue-curricula-results', component: () => import('../views/catalogue/CatalogueCurriculaResultsView.vue'), meta: { catalogueSection: 'studies' } },
          { path: 'studia', name: 'catalogue-studies', component: () => import('../views/catalogue/CatalogueStudiesView.vue'), meta: { catalogueSection: 'studies' } },
          { path: 'studia/lista', redirect: { name: 'catalogue-curricula-results' } },
          { path: 'akademiki', redirect: { name: 'catalogue' } },
          { path: 'pomoc', redirect: { name: 'catalogue' } },
          { path: 'wyniki/osoby', redirect: { name: 'catalogue-teachers-results' } },
          { path: 'wyniki/jednostki', redirect: { name: 'catalogue-units-results' } },
          { path: 'wyniki/przedmioty', redirect: { name: 'catalogue-subjects-results' } },
          { path: 'wyniki/studia', redirect: { name: 'catalogue-curricula-results' } },
        ],
      },
      {
        path: 'student',
        component: () => import('../views/student/StudentLayout.vue'),
        meta: { tab: 'student', roles: ['Student'] },
        children: [
          { path: '', redirect: { name: 'student-schedule' } },
          {
            path: 'registrations',
            name: 'student-registrations',
            component: () => import('../views/student/RegistrationsView.vue'),
          },
          {
            path: 'enrolments',
            name: 'student-enrolments',
            component: () => import('../views/student/EnrolmentsView.vue'),
          },
          {
            path: 'cycles',
            name: 'student-cycles',
            component: () => import('../views/student/CyclesView.vue'),
          },
          {
            path: 'schedule',
            name: 'student-schedule',
            component: () => import('../views/shared/WeeklyScheduleView.vue'),
          },
          {
            path: 'opinion',
            name: 'student-opinion',
            component: () => import('../views/student/OpinionView.vue'),
          },
        ],
      },
      {
        path: 'teacher',
        component: () => import('../views/teacher/TeacherLayout.vue'),
        meta: { tab: 'teacher', roles: ['Teacher', 'Admin'] },
        children: [
          { path: '', redirect: { name: 'teacher-schedule' } },
          {
            path: 'schedule',
            name: 'teacher-schedule',
            component: () => import('../views/shared/WeeklyScheduleView.vue'),
          },
          {
            path: 'groups',
            name: 'teacher-groups',
            component: () => import('../views/teacher/TeacherGroupsView.vue'),
          },
          {
            path: 'groups/:groupId/grades',
            name: 'teacher-group-grades',
            component: () => import('../views/teacher/TeacherGroupGradesView.vue'),
          },
          {
            path: 'students/:studentIdx',
            name: 'teacher-student-detail',
            component: () => import('../views/teacher/TeacherStudentDetailView.vue'),
          },
        ],
      },
      {
        path: 'admin',
        component: () => import('../views/admin/AdminLayout.vue'),
        meta: { tab: 'admin', roles: ['Admin'] },
        children: [
          { path: '', redirect: { name: 'admin-lists' } },
          {
            path: 'lists',
            name: 'admin-lists',
            component: () => import('../views/admin/ListsView.vue'),
          },
          {
            path: 'users',
            name: 'admin-users',
            component: () => import('../views/admin/UsersView.vue'),
          },
          {
            path: 'people',
            name: 'admin-people',
            component: () => import('../views/admin/PeopleView.vue'),
          },
          {
            path: 'entities',
            name: 'admin-entities',
            component: () => import('../views/admin/EntitiesView.vue'),
          },
          {
            path: 'registrations',
            name: 'admin-registrations',
            component: () => import('../views/admin/RegistrationsView.vue'),
          },
          {
            path: 'opinion',
            name: 'admin-opinion',
            component: () => import('../views/admin/OpinionView.vue'),
          },
        ],
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.public) {
    if (auth.isLoggedIn && to.name === 'login') return auth.defaultRoute
    return true
  }
  if (!auth.isLoggedIn) return { name: 'login', query: { redirect: to.fullPath } }
  const roles = to.matched.flatMap((r) => r.meta.roles || [])
  if (roles.length) {
    const ok = roles.some((role) => {
      if (role === 'Teacher') return auth.hasTeacher
      if (role === 'Admin') return auth.hasAdmin
      if (role === 'Student') return auth.hasStudent
      return auth.roles.includes(role)
    })
    if (!ok) return auth.defaultRoute
  }
  return true
})

export default router
