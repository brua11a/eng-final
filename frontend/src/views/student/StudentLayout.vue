<script setup>
import SidebarLayout from '../../components/SidebarLayout.vue'

const links = [
  { to: '/student/schedule', label: 'Schedule' },
  { to: '/student/registrations', label: 'Registrations' },
  { to: '/student/enrolments', label: 'Enrolments' },
  { to: '/student/cycles', label: 'Cycles' },
  { to: '/student/opinion', label: 'Opinion' },
]
</script>

<template>
  <SidebarLayout label="Student" :links="links" />
</template>
