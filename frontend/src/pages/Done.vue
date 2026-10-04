<template>
  <div class="wall">
    <h1 class="serif">已完成</h1>
    <article v-for="w in rows" :key="w.id" class="card">
      <h3>{{ w.title }}</h3>
      <p>{{ w.claimer }}</p>
      <span class="tag">核销于 {{ w.fulfilled_at || '—' }}</span>
      <p v-if="w.evidence" class="tag">举证：{{ w.evidence }}</p>
      <template v-if="remaining(w) > 0">
        <p class="tag">撤销窗剩余 {{ fmtRemaining(remaining(w)) }}</p>
        <button class="ghost" @click="undo(w)">撤销核销</button>
      </template>
    </article>
    <p v-if="err" class="err">{{ err }}</p>
  </div>
</template>
<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { api } from '../api'
import { fmtRemaining } from '../countdown'
const rows = ref([])
const err = ref('')
const tick = ref(0)
let timer = null
const remaining = (w) => (w.undo_remaining_seconds == null ? 0 : w.undo_remaining_seconds - tick.value)
async function load() { rows.value = await api('/done'); tick.value = 0 }
async function undo(w) {
  err.value = ''
  try {
    await api('/wishes/' + w.id + '/undo', { method: 'POST', body: '{}' })
    rows.value = rows.value.filter(x => x.id !== w.id)
  } catch (e) { err.value = e.message; await load() }
}
onMounted(() => { load(); timer = setInterval(() => tick.value++, 1000) })
onUnmounted(() => clearInterval(timer))
</script>
