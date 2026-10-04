<template>
  <div class="wall">
    <h1 class="serif">我的认领</h1>
    <input v-model="name" @change="load" placeholder="认领人名" />
    <article v-for="w in rows" :key="w.id" class="card" @click="$router.push('/wishes/'+w.id)">
      <h3>{{ w.title }}</h3>
      <span class="tag">{{ w.status }} · 到期 {{ w.expires_at || '—' }}</span>
      <span v-if="w.countdown_seconds != null" class="tag"> · 倒计时 {{ fmtRemaining(w.countdown_seconds - tick) }}</span>
      <span v-if="w.undo_remaining_seconds != null && w.undo_remaining_seconds - tick > 0" class="tag"> · 可撤销 {{ fmtRemaining(w.undo_remaining_seconds - tick) }}</span>
    </article>
  </div>
</template>
<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { api } from '../api'
import { fmtRemaining } from '../countdown'
const name = ref('访客')
const rows = ref([])
const tick = ref(0)
let timer = null
async function load() { rows.value = await api('/mine?claimer=' + encodeURIComponent(name.value)); tick.value = 0 }
onMounted(() => { load(); timer = setInterval(() => tick.value++, 1000) })
onUnmounted(() => clearInterval(timer))
</script>
