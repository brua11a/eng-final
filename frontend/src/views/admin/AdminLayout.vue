<script setup>
import SidebarLayout from '../../components/SidebarLayout.vue'
import '../../styles/admin.css'

const links = [
  { to: '/admin/lists', label: 'Lists' },
  { to: '/admin/users', label: 'Users' },
  { to: '/admin/people', label: 'People' },
  { to: '/admin/entities', label: 'Entities' },
  { to: '/admin/registrations', label: 'Registrations' },
]
</script>

<template>
  <SidebarLayout label="Admin" :links="links" />
</template>
