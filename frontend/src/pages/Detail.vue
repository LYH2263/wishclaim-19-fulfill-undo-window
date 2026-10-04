<template>
  <div class="wall">
    <h1 class="serif">{{ w.title }}</h1>
    <p>{{ w.note }}</p>
    <p class="tag">状态 {{ w.status }} · 认领人 {{ w.claimer || '—' }}</p>
    <p v-if="w.status==='claimed'" class="tag">锁定倒计时 {{ fmtRemaining(cd) }}</p>
    <template v-if="w.status==='fulfilled'">
      <p class="tag">核销于 {{ w.fulfilled_at || '—' }}</p>
      <p v-if="w.evidence" class="tag">举证快照：{{ w.evidence }}</p>
      <p v-if="undoable" class="tag">撤销窗剩余 {{ fmtRemaining(ur) }}</p>
      <p v-else class="tag">撤销窗已关闭</p>
    </template>
    <p v-if="err" class="err">{{ err }}</p>
    <input v-model="claimer" placeholder="你的名字" />
    <input v-if="w.status==='claimed'" v-model="evidence" placeholder="举证（可选，核销时留档）" />
    <div style="display:flex;gap:8px;flex-wrap:wrap">
      <button @click="claim">认领锁定</button>
      <button class="ghost" @click="release">释放</button>
      <button class="ghost" @click="fulfill">核销完成</button>
      <button v-if="w.status==='fulfilled' && undoable" class="ghost" @click="undo">撤销核销</button>
    </div>
  </div>
</template>
<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { api } from '../api'
import { fmtRemaining } from '../countdown'
const props = defineProps({ id: String })
const w = ref({})
const claimer = ref('访客')
const evidence = ref('')
const err = ref('')
const cd = ref(null)
const ur = ref(null)
const undoable = ref(false)
let timer = null
async function load() {
  w.value = await api('/wishes/' + props.id)
  cd.value = w.value.countdown_seconds
  ur.value = w.value.undo_remaining_seconds
  undoable.value = w.value.undoable
}
async function claim() {
  err.value=''; try { await api('/wishes/'+props.id+'/claim',{method:'POST',body:JSON.stringify({claimer:claimer.value})}); await load() } catch(e){ err.value=e.message }
}
async function release() {
  err.value=''; try { await api('/wishes/'+props.id+'/release',{method:'POST',body:'{}'}); await load() } catch(e){ err.value=e.message }
}
async function fulfill() {
  err.value=''; try { await api('/wishes/'+props.id+'/fulfill',{method:'POST',body:JSON.stringify({evidence:evidence.value})}); evidence.value=''; await load() } catch(e){ err.value=e.message }
}
async function undo() {
  err.value=''
  try { await api('/wishes/'+props.id+'/undo',{method:'POST',body:'{}'}); await load() }
  catch(e){ err.value=e.message; await load() }
}
onMounted(() => {
  load()
  timer = setInterval(() => {
    if (cd.value != null && cd.value > 0) { cd.value--; if (cd.value === 0) load() }
    if (ur.value != null && ur.value > 0) { ur.value--; if (ur.value === 0) undoable.value = false }
  }, 1000)
})
onUnmounted(() => clearInterval(timer))
</script>
