<template>
  <div>
    <nav class="subnav">
      <RouterLink to="/student/registrations">Registrations</RouterLink>
      <RouterLink to="/student/enrolments">Enrolments</RouterLink>
      <RouterLink to="/student/cycles">Academic cycles</RouterLink>
      <RouterLink to="/student/dashboard">Dashboard</RouterLink>
      <RouterLink to="/student/opinion">Opinion</RouterLink>
    </nav>
    <RouterView />
  </div>
</template>

<style scoped>
.subnav {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-bottom: 1rem;
}
.subnav a.router-link-active {
  font-weight: 600;
  color: #2563eb;
}
</style>
