<template>
  <div>
    <nav class="subnav">
      <RouterLink to="/teacher/student">Student detail</RouterLink>
      <RouterLink to="/teacher/group-students">Group students</RouterLink>
      <RouterLink to="/teacher/grade">Set grade</RouterLink>
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
