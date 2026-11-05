<template>
  <div>
    <nav class="subnav">
      <RouterLink to="/admin/lists">Lists</RouterLink>
      <RouterLink to="/admin/users">Users</RouterLink>
      <RouterLink to="/admin/people">Teachers & students</RouterLink>
      <RouterLink to="/admin/entities">Entities</RouterLink>
      <RouterLink to="/admin/registrations">Registrations</RouterLink>
      <RouterLink to="/admin/opinion">Opinion</RouterLink>
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
