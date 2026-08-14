<script setup lang="ts">
// 声优管理页：新增表单（名称必填 + 描述）+ 列表（ID/名称/图片数/状态/启用）
// 行为对齐原面板 backend/bot/admin/static/admin.js 的 loadActors / bindActorActions：
//   - 一次性拉全量列表，顶部搜索框客户端过滤
//   - 新增成功：提示 + 清空表单 + 刷新列表；空名称客户端拦截
//   - 启用开关：失败回滚开关并 el-message 报错
//   - ID 点击复制（navigator.clipboard，非 secure context 下降级 textarea + execCommand，成功/失败均有提示）
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import 'element-plus/es/components/message/style/css'
import api from '../api'
import type { VoiceActor } from '../api'

// 显式组件名：AdminLayout 的 keep-alive 靠 name 匹配缓存实例
defineOptions({ name: 'ActorsView' })

const loading = ref(false)
const actors = ref<VoiceActor[]>([])

/** 搜索关键字：客户端过滤（数据量小，一次性拉全量，对齐原实现） */
const keyword = ref('')
const filteredActors = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return actors.value
  return actors.value.filter(
    (a) => String(a.id).includes(kw) || a.name.toLowerCase().includes(kw),
  )
})

// ---------- 新增 ----------

const formRef = ref<FormInstance>()
const form = reactive({ name: '', description: '' })
const submitting = ref(false)

/** 名称必填：trim 后为空同样拦截（对齐原面板的客户端校验） */
const rules: FormRules<typeof form> = {
  name: [
    {
      validator: (_rule, value, callback) => {
        if (typeof value === 'string' && value.trim()) return callback()
        callback(new Error('请输入声优名称'))
      },
      trigger: 'blur',
    },
  ],
}

async function submitActor() {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    return // 校验未通过：表单内联错误提示
  }
  submitting.value = true
  try {
    await api.createVoiceActor(form.name.trim(), form.description.trim())
    ElMessage.success('新增声优成功')
    form.name = ''
    form.description = ''
    formRef.value.clearValidate()
    await loadActors()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '新增失败')
  } finally {
    submitting.value = false
  }
}

// ---------- 启用开关 ----------

/** 切换中的声优 id（el-switch :loading，期间不可再点） */
const pendingToggle = reactive<Record<number, boolean>>({})

async function onToggleChange(id: number, val: string | number | boolean) {
  // val 为本次 change 的新值；el-switch 先写 v-model 再触发 change，
  // 不能从 actor.is_active 反推旧值（读到的是翻转后的值），失败按 !newVal 回滚
  // （未配置 active-value，运行期 val 恒为布尔；el-switch 事件类型是 string|number|boolean，需收窄）
  const newVal = val === true
  const actor = actors.value.find((a) => a.id === id)
  if (!actor) return
  pendingToggle[actor.id] = true
  try {
    await api.updateVoiceActor(actor.id, { is_active: newVal })
    ElMessage.success('声优状态已更新')
  } catch (e) {
    // 失败回滚开关 + 报错（对齐原 admin.js 行为）
    actor.is_active = !newVal
    ElMessage.error(e instanceof Error ? e.message : '更新失败')
  } finally {
    pendingToggle[actor.id] = false
  }
}

// ---------- ID 点击复制 ----------

async function copyId(id: number) {
  const text = String(id)
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text)
    } else {
      // http（非 secure context）下 navigator.clipboard 不存在：降级为隐藏 textarea + execCommand('copy')
      const textarea = document.createElement('textarea')
      textarea.value = text
      textarea.style.position = 'fixed'
      textarea.style.opacity = '0'
      document.body.appendChild(textarea)
      let ok = false
      try {
        textarea.select()
        ok = document.execCommand('copy')
      } finally {
        textarea.remove()
      }
      if (!ok) throw new Error('复制被浏览器拒绝')
    }
    ElMessage.success('已复制')
  } catch {
    ElMessage.error('复制失败')
  }
}

// ---------- 加载 ----------

async function loadActors() {
  loading.value = true
  try {
    actors.value = await api.listVoiceActors()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void loadActors()
})
</script>

<template>
  <div class="actors">
    <!-- 新增区 -->
    <el-card shadow="never" class="add-card">
      <template #header>
        <span class="card-title">新增声优</span>
      </template>
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="64px"
        class="add-form"
        @submit.prevent="submitActor"
      >
        <el-form-item label="名称" prop="name">
          <el-input
            v-model="form.name"
            placeholder="请输入声优名称"
            maxlength="100"
            clearable
          />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="2"
            placeholder="请输入描述（可选）"
            maxlength="500"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="submitting" @click="submitActor">
            新增
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 列表区 -->
    <el-card shadow="never" class="list-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">声优列表（{{ filteredActors.length }}）</span>
          <el-input
            v-model="keyword"
            placeholder="搜索名称 / ID"
            clearable
            class="search-input"
          />
        </div>
      </template>
      <el-table :data="filteredActors" :loading="loading" stripe size="default">
        <el-table-column label="ID" width="90">
          <template #default="{ row }">
            <span class="id-cell" title="点击复制 ID" @click="copyId(row.id)">
              {{ row.id }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="名称" prop="name" min-width="160" />
        <el-table-column label="图片数" prop="image_count" width="90" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
              {{ row.is_active ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="启用" width="90">
          <template #default="{ row }">
            <el-switch
              v-model="row.is_active"
              :loading="pendingToggle[row.id]"
              @change="(val) => onToggleChange(row.id, val)"
            />
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.add-card {
  margin-bottom: 16px;
}

.add-form {
  max-width: 520px;
}

.card-title {
  font-weight: 600;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.search-input {
  width: 220px;
}

.id-cell {
  color: var(--el-color-primary);
  cursor: pointer;
  user-select: none;
}

.id-cell:hover {
  text-decoration: underline;
}
</style>
