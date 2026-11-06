<script setup>
import SidebarLayout from '../../components/SidebarLayout.vue'

const links = [
  { to: '/teacher/schedule', label: 'Schedule' },
  { to: '/teacher/groups', label: 'My groups' },
]
</script>

<template>
  <SidebarLayout label="Teacher" :links="links" />
</template>
