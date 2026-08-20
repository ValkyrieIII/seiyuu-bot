<script setup lang="ts">
// 图片管理页：上传（选声优 + 多文件）/ 双视图（表格列表 | 按声优分类）/ 启用开关 / 删除
// 行为对齐原面板 backend/bot/admin/static/admin.js 的 initImages / loadImages / bindImageActions：
//   - 上传：el-select 选目标声优 + el-upload（http-request 自定义走 api.uploadImages，FormData files 字段），
//     完成后按 results 统计成功/失败数，失败列出文件名，并刷新当前视图
//   - 表格视图：el-image 缩略图点击放大、文件名、所属声优、大小(KB)、
//     启用开关（失败回滚）、删除（el-popconfirm 确认「同时删除文件，不可撤销」）
//   - 分类视图：ImageGroupedView 子组件（按需展开 + 缓存，看哪个声优拉哪个），与表格共用筛选状态
//   - 筛选：按声优 el-select + 文件名搜索（防抖 300ms），任一变化回第 1 页（表格视图）
//   - 分页：服务端分页，page_size 固定 20（对齐原面板 imagePageSize）
import { onActivated, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import ImageGroupedView from '../components/ImageGroupedView.vue'
import { ElMessage } from 'element-plus'
import type { UploadInstance, UploadRawFile, UploadRequestOptions } from 'element-plus'
import 'element-plus/es/components/message/style/css'
import api, { imageFileUrl } from '../api'
import type { ImageItem, ImageQuery, VoiceActor } from '../api'

// 显式组件名：AdminLayout 的 keep-alive 靠 name 匹配缓存实例
defineOptions({ name: 'ImagesView' })

const loading = ref(false)
const items = ref<ImageItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20

// ---------- 视图切换：表格列表 | 按声优分类（v-show 双挂载，keep-alive 下切换不丢状态） ----------

const viewMode = ref<'table' | 'grouped'>('table')
const groupedViewRef = ref<InstanceType<typeof ImageGroupedView>>()

function switchView(mode: string | number | boolean | undefined) {
  const m: 'table' | 'grouped' = mode === 'grouped' ? 'grouped' : 'table'
  viewMode.value = m
  // 切到分类视图时刷新一次（首次挂载由子组件自身加载；切回时保持最新）
  if (m === 'grouped') groupedViewRef.value?.reload()
}

// ---------- 声优下拉（上传目标 / 筛选共用） ----------

const actors = ref<VoiceActor[]>([])
const uploadActorId = ref<number>()
const filterActorId = ref<number>()

async function loadActors() {
  try {
    actors.value = await api.listVoiceActors()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '加载声优失败')
  }
}

// ---------- 上传 ----------

const uploadRef = ref<UploadInstance>()

/** 本批上传统计：el-upload 对多文件逐个调用 http-request，批量完成后统一提示（对齐原面板的汇总文案） */
interface UploadBatch {
  total: number
  done: number
  ok: number
  fail: string[]
}
let batch: UploadBatch | null = null

/** 未选声优时拦截：返回 false 该文件不进队列（对齐原面板「请选择目标声优」拦截） */
function beforeUpload(_file: UploadRawFile) {
  if (!uploadActorId.value) {
    ElMessage.warning('请选择目标声优')
    return false
  }
  return true
}

function customUpload(options: UploadRequestOptions): Promise<unknown> {
  if (!batch) batch = { total: 0, done: 0, ok: 0, fail: [] }
  batch.total++
  void doUpload(options)
  // 本版本 el-upload 会对 http-request 的返回值额外挂 request.then(onSuccess, onError)（upload-content 源码），
  // 与手动调用 options.onSuccess/onError 会二次触发（失败路径下会把失败文件误标为成功）。
  // 因此返回一个永不 settle 的 Promise，回调只走手动调用这一次。
  return new Promise(() => {})
}

async function doUpload(options: UploadRequestOptions) {
  try {
    const actorId = uploadActorId.value
    if (!actorId) throw new Error('请选择目标声优')
    const { results } = await api.uploadImages([options.file], actorId)
    const r = results[0]
    if (r?.status === 'ok') {
      batch!.ok++
      options.onSuccess(r)
    } else {
      batch!.fail.push(r?.filename ?? options.file.name)
      options.onError(plainUploadError(r?.detail || '上传失败'))
    }
  } catch (e) {
    batch!.fail.push(options.file.name)
    options.onError(plainUploadError(e instanceof Error ? e.message : '上传失败'))
  } finally {
    finishUpload()
  }
}

/** 构造结构上兼容 UploadAjaxError 的错误（onError 参数类型要求 status/method/url 字段） */
function plainUploadError(message: string) {
  return Object.assign(new Error(message), {
    name: 'UploadAjaxError',
    status: 400,
    method: 'POST',
    url: '/admin/api/images/upload',
  })
}

/** 本批全部完成后：清空文件列表 + 汇总提示 + 刷新列表 */
function finishUpload() {
  if (!batch) return
  batch.done++
  if (batch.done < batch.total) return
  const b = batch
  batch = null
  uploadRef.value?.clearFiles()
  const failText = b.fail.length > 0 ? `，失败 ${b.fail.length} 张 (${b.fail.join(', ')})` : ''
  if (b.fail.length > 0) ElMessage.warning(`上传完成: 成功 ${b.ok} 张${failText}`)
  else ElMessage.success(`上传完成: 成功 ${b.ok} 张`)
  // 刷新当前视图：表格直接重载；分类视图（已挂载时）调 reload
  if (viewMode.value === 'table') void loadImages()
  else groupedViewRef.value?.reload()
}

// ---------- 筛选 / 搜索 ----------

const keyword = ref('')
let searchTimer: ReturnType<typeof setTimeout> | undefined

/** 文件名搜索：防抖 300ms 后回第 1 页刷新（对齐原面板 bindImageFilterEvents） */
function onSearchInput() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    page.value = 1
    void loadImages()
  }, 300)
}

/** 按声优筛选：立即回第 1 页刷新 */
function onFilterActorChange() {
  page.value = 1
  void loadImages()
}

// 组件卸载时清理搜索防抖定时器，避免卸载后回调
onBeforeUnmount(() => clearTimeout(searchTimer))

// ---------- 启用开关 ----------

/** 切换中的图片 id（el-switch :loading，期间不可再点） */
const pendingToggle = reactive<Record<number, boolean>>({})

async function onToggleChange(id: number, val: string | number | boolean) {
  // val 为本次 change 的新值；el-switch 先写 v-model 再触发 change，
  // 不能从 item.is_active 反推旧值（读到的是翻转后的值），失败按 !newVal 回滚（对齐原面板）
  const newVal = val === true
  const item = items.value.find((i) => i.id === id)
  if (!item) return
  pendingToggle[id] = true
  try {
    await api.updateImage(id, newVal)
    ElMessage.success('图片状态已更新')
  } catch (e) {
    item.is_active = !newVal // 失败回滚开关
    ElMessage.error(e instanceof Error ? e.message : '更新失败')
  } finally {
    pendingToggle[id] = false
  }
}

// ---------- 删除 ----------

/** 删除进行中标记：防并发删除 */
const deleting = ref(false)

async function onDelete(item: ImageItem) {
  if (deleting.value) return
  deleting.value = true
  try {
    await api.deleteImage(item.id)
    ElMessage.success('图片已删除')
    await loadImages() // 重载当前页（对齐原面板 loadImages(imagePage)）
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '删除失败')
  } finally {
    deleting.value = false
  }
}

// ---------- 列表加载（服务端分页） ----------

/** 请求序号：快速切换筛选/翻页时并发请求，旧响应后到会被丢弃，防止覆盖新数据 */
let loadSeq = 0

async function loadImages() {
  const seq = ++loadSeq
  loading.value = true
  try {
    const query: ImageQuery = { page: page.value, page_size: pageSize }
    if (filterActorId.value) query.voice_actor_id = filterActorId.value
    const kw = keyword.value.trim()
    if (kw) query.search = kw
    const data = await api.listImages(query)
    if (seq !== loadSeq) return // 丢弃过期响应
    items.value = data.items
    total.value = data.total
  } catch (e) {
    if (seq !== loadSeq) return // 过期请求的报错不弹
    ElMessage.error(e instanceof Error ? e.message : '加载失败')
  } finally {
    if (seq === loadSeq) loading.value = false // 仅最新请求控制 loading
  }
}

function onPageChange(p: number) {
  page.value = p
  void loadImages()
}

onMounted(() => {
  void loadImages()
})

// keep-alive 缓存下 onMounted 仅首次触发；切回本页时刷新声优下拉（新增声优后立即可选/可筛选）
// 同时刷新当前视图数据，保证切回页面时看到最新内容
onActivated(() => {
  void loadActors()
  if (viewMode.value === 'table') void loadImages()
  else groupedViewRef.value?.reload()
})
</script>

<template>
  <div class="images">
    <!-- 上传区 -->
    <el-card shadow="never" class="upload-card">
      <template #header>
        <span class="card-title">上传图片</span>
      </template>
      <div class="upload-bar">
        <el-select
          v-model="uploadActorId"
          placeholder="请选择目标声优"
          clearable
          class="actor-select"
        >
          <el-option
            v-for="a in actors"
            :key="a.id"
            :label="`${a.name} (#${a.id})`"
            :value="a.id"
          />
        </el-select>
        <el-upload
          ref="uploadRef"
          multiple
          accept="image/*"
          :before-upload="beforeUpload"
          :http-request="customUpload"
        >
          <el-button type="primary">选择图片并上传</el-button>
          <template #tip>
            <div class="el-upload__tip">支持多选，仅限图片文件</div>
          </template>
        </el-upload>
      </div>
    </el-card>

    <!-- 列表区：视图切换 + 公共筛选 -->
    <el-card shadow="never" class="list-card">
      <template #header>
        <div class="card-header">
          <el-radio-group v-model="viewMode" size="small" @change="switchView">
            <el-radio-button value="table">表格列表</el-radio-button>
            <el-radio-button value="grouped">按声优分类</el-radio-button>
          </el-radio-group>
          <div class="filters">
            <el-select
              v-model="filterActorId"
              placeholder="全部声优"
              clearable
              class="filter-actor"
              @change="onFilterActorChange"
            >
              <el-option
                v-for="a in actors"
                :key="a.id"
                :label="`${a.name} (#${a.id})`"
                :value="a.id"
              />
            </el-select>
            <el-input
              v-model="keyword"
              placeholder="搜索文件名"
              clearable
              class="search-input"
              @input="onSearchInput"
              @clear="onSearchInput"
            />
          </div>
        </div>
      </template>

      <!-- 表格视图（服务端分页，原面板对齐行为） -->
      <div v-show="viewMode === 'table'">
        <el-table :data="items" :loading="loading" stripe>
          <el-table-column label="预览" width="90">
            <template #default="{ row }">
              <el-image
                class="thumb"
                :src="imageFileUrl(row.id)"
                :preview-src-list="[imageFileUrl(row.id)]"
                preview-teleported
                fit="cover"
              />
            </template>
          </el-table-column>
          <el-table-column
            prop="filename"
            label="文件名"
            min-width="220"
            show-overflow-tooltip
          />
          <el-table-column prop="voice_actor_name" label="所属声优" width="150" />
          <el-table-column label="大小(KB)" width="100">
            <template #default="{ row }">{{ row.size_kb }}</template>
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
          <el-table-column label="操作" width="90">
            <template #default="{ row }">
              <el-popconfirm
                :title="`确定删除图片「${row.filename}」吗？此操作会同时删除文件，不可撤销。`"
                confirm-button-text="删除"
                cancel-button-text="取消"
                @confirm="onDelete(row as ImageItem)"
              >
                <template #reference>
                  <el-button type="danger" size="small" text>删除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
        <!-- 单页（total <= page_size）不渲染分页，对齐原面板 totalPages > 1 才显示 -->
        <div v-if="total > pageSize" class="pager">
          <el-pagination
            background
            layout="total, prev, pager, next"
            :total="total"
            :current-page="page"
            :page-size="pageSize"
            @current-change="onPageChange"
          />
        </div>
      </div>

      <!-- 分类视图：按声优分组，与表格共用筛选状态 -->
      <ImageGroupedView
        v-show="viewMode === 'grouped'"
        ref="groupedViewRef"
        :keyword="keyword"
        :filter-actor-id="filterActorId"
      />
    </el-card>
  </div>
</template>

<style scoped>
.upload-card {
  margin-bottom: 16px;
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

.upload-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.actor-select {
  width: 240px;
}

.thumb {
  display: block;
  width: 64px;
  height: 64px;
  border-radius: 4px;
  background-color: var(--el-fill-color-light);
}

.filters {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.filter-actor {
  width: 180px;
}

.search-input {
  width: 220px;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
