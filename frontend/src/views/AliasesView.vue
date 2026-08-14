<script setup lang="ts">
// 别名管理页：新增区（别名必填 + 目标声优下拉 + 优先级）+ 列表（ID/别名/目标声优/优先级/操作）
// 行为对齐原面板 backend/bot/admin/static/admin.js 的 initAliases / loadAliases / bindAliasActions / bindAliasTableEvents：
//   - 声优下拉 label 为「名称 (#id)」（对齐 populateAliasTarget）
//   - 一次性拉全量列表，顶部搜索框客户端过滤（filterTable 语义：任一列命中即显示）
//   - 新增成功：提示「新增别名成功」+ 清空别名输入 + 刷新列表；别名/目标声优缺失客户端拦截
//   - 删除经 el-popconfirm 确认，文案对齐原面板「确定删除别名「…」吗？此操作不可撤销。」；成功提示「别名已删除」
//   - 409 重复别名等后端错误：client.ts 已透传 {detail}，直接展示 e.message
//   - ID 点击复制（navigator.clipboard，非 secure context 下降级 textarea + execCommand）
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import 'element-plus/es/components/message/style/css'
import api from '../api'
import type { AliasItem, VoiceActor } from '../api'

// 显式组件名：AdminLayout 的 keep-alive 靠 name 匹配缓存实例
defineOptions({ name: 'AliasesView' })

const loading = ref(false)
const aliases = ref<AliasItem[]>([])
const actors = ref<VoiceActor[]>([])

/** 搜索关键字：客户端过滤（数据量小，一次性拉全量，对齐原 filterTable 语义） */
const keyword = ref('')
const filteredAliases = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return aliases.value
  return aliases.value.filter((a) =>
    [
      String(a.id),
      a.alias_name,
      a.target_voice_actor_name,
      String(a.priority),
    ].some((text) => text.toLowerCase().includes(kw)),
  )
})

// ---------- 新增 ----------

const formRef = ref<FormInstance>()
const form = reactive({
  alias_name: '',
  target_voice_actor_id: undefined as number | undefined,
  priority: 0,
})
const submitting = ref(false)

/** 别名必填（trim 后为空同样拦截）+ 目标声优必选（对齐原面板的客户端校验） */
const rules: FormRules<typeof form> = {
  alias_name: [
    {
      validator: (_rule, value, callback) => {
        if (typeof value === 'string' && value.trim()) return callback()
        callback(new Error('请输入别名'))
      },
      trigger: 'blur',
    },
  ],
  target_voice_actor_id: [
    {
      validator: (_rule, value, callback) => {
        if (typeof value === 'number' && value > 0) return callback()
        callback(new Error('请选择目标声优'))
      },
      trigger: 'change',
    },
  ],
}

async function submitAlias() {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    return // 校验未通过：表单内联错误提示
  }
  submitting.value = true
  try {
    // 默认优先级 0：对齐原面板 Number(priorityInput.value || 0)
    await api.createAlias({
      alias_name: form.alias_name.trim(),
      target_voice_actor_id: form.target_voice_actor_id as number,
      priority: form.priority,
    })
    ElMessage.success('新增别名成功')
    form.alias_name = ''
    formRef.value.clearValidate()
    await loadAliases()
  } catch (e) {
    // 409 重复别名等错误：后端 {detail} 已由 client.ts 透传进 e.message
    ElMessage.error(e instanceof Error ? e.message : '新增失败')
  } finally {
    submitting.value = false
  }
}

// ---------- 删除 ----------

async function onDeleteAlias(row: AliasItem) {
  try {
    await api.deleteAlias(row.id)
    ElMessage.success('别名已删除')
    await loadAliases()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '删除失败')
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

async function loadAliases() {
  loading.value = true
  try {
    aliases.value = await api.listAliases()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '加载失败')
  } finally {
    loading.value = false
  }
}

async function loadVoiceActors() {
  try {
    actors.value = await api.listVoiceActors()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '声优列表加载失败')
  }
}

onMounted(() => {
  void loadVoiceActors()
  void loadAliases()
})
</script>

<template>
  <div class="aliases">
    <!-- 新增区 -->
    <el-card shadow="never" class="add-card">
      <template #header>
        <span class="card-title">新增别名</span>
      </template>
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="90px"
        class="add-form"
        @submit.prevent="submitAlias"
      >
        <el-form-item label="别名" prop="alias_name">
          <el-input
            v-model="form.alias_name"
            placeholder="请输入别名"
            maxlength="100"
            clearable
          />
        </el-form-item>
        <el-form-item label="目标声优" prop="target_voice_actor_id">
          <!-- label 格式「名称 (#id)」，对齐原面板 populateAliasTarget -->
          <el-select
            v-model="form.target_voice_actor_id"
            placeholder="请选择目标声优"
            filterable
            clearable
            class="target-select"
          >
            <el-option
              v-for="actor in actors"
              :key="actor.id"
              :value="actor.id"
              :label="`${actor.name} (#${actor.id})`"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="优先级" prop="priority">
          <el-input-number v-model="form.priority" :min="0" :max="9999" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="submitting" @click="submitAlias">
            新增
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 列表区 -->
    <el-card shadow="never" class="list-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">别名列表（{{ filteredAliases.length }}）</span>
          <el-input
            v-model="keyword"
            placeholder="搜索别名 / 目标声优 / ID / 优先级"
            clearable
            class="search-input"
          />
        </div>
      </template>
      <el-table :data="filteredAliases" :loading="loading" stripe size="default">
        <el-table-column label="ID" width="90">
          <template #default="{ row }">
            <span class="id-cell" title="点击复制 ID" @click="copyId(row.id)">
              {{ row.id }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="别名" prop="alias_name" min-width="160" />
        <el-table-column label="目标声优" prop="target_voice_actor_name" min-width="160" />
        <el-table-column label="优先级" prop="priority" width="100" />
        <el-table-column label="操作" width="110">
          <template #default="{ row }">
            <el-popconfirm
              :title="`确定删除别名「${row.alias_name}」吗？此操作不可撤销。`"
              confirm-button-text="确定"
              cancel-button-text="取消"
              @confirm="onDeleteAlias(row as AliasItem)"
            >
              <template #reference>
                <el-button type="danger" size="small" text>删除</el-button>
              </template>
            </el-popconfirm>
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

.target-select {
  width: 260px;
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
