<script setup lang="ts">
// 图片管理页 - 按声优分类视图（按需加载 + 缓存）
// 数据策略：首屏只拉声优列表（分组骨架）；点击展开某声优时才拉取该声优的图片（page_size=100 循环翻页），
//   拉取结果按声优缓存——收起再展开直接读缓存不再请求；已展开的声优图片操作（开关/删除）局部更新缓存。
// 失效时机：筛选（关键词/声优）变化 → 清缓存 + 全部收起；reload（上传后/切回页面）→ 清缓存 + 刷新展开中的声优。
// 组内操作与表格视图对齐：启用开关（失败回滚）+ 删除（el-popconfirm 确认「同时删除文件，不可撤销」）
import { onMounted, reactive, ref, watch } from 'vue'
import { ElCollapse, ElCollapseItem, ElMessage } from 'element-plus'
import 'element-plus/es/components/collapse/style/css'
import 'element-plus/es/components/collapse-item/style/css'
import 'element-plus/es/components/message/style/css'
import api, { imageFileUrl } from '../api'
import type { ImageItem, ImageQuery, VoiceActor } from '../api'

defineOptions({ name: 'ImageGroupedView' })

const props = defineProps<{
  keyword: string
  filterActorId?: number
}>()

/** 分组骨架：全部声优（名称序，来自声优列表接口） */
const groups = ref<VoiceActor[]>([])
const groupsLoading = ref(false)

/** 展开中的声优 id（el-collapse activeNames，字符串 key） */
const expandedIds = ref<string[]>([])

/** 图片缓存：声优 id -> 已拉取的图片列表；缺失表示未加载过 */
const imageCache = reactive<Record<string, ImageItem[]>>({})
/** 单声优加载中标记 */
const loadingMap = reactive<Record<string, boolean>>({})

/** 数据代际：筛选变化 / reload 时递增，使在途请求的结果作废，防止旧数据写回缓存 */
let generation = 0

const cacheKey = (actorId: number) => String(actorId)

// ---------- 首屏：加载声优列表（分组骨架） ----------

async function loadGroups() {
  groupsLoading.value = true
  try {
    groups.value = await api.listVoiceActors()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '加载声优失败')
  } finally {
    groupsLoading.value = false
  }
}

onMounted(() => void loadGroups())

// ---------- 按需加载：展开时才拉取该声优的图片 ----------

/** 拉取单个声优的全部图片（page_size=100 循环翻页，含关键词过滤） */
async function fetchActorImages(actorId: number): Promise<ImageItem[]> {
  const query: ImageQuery = { voice_actor_id: actorId, page_size: 100 }
  const kw = props.keyword.trim()
  if (kw) query.search = kw

  const all: ImageItem[] = []
  let page = 1
  for (;;) {
    const data = await api.listImages({ ...query, page })
    all.push(...data.items)
    if (page * data.page_size >= data.total) break
    page++
  }
  return all
}

async function loadActor(key: string) {
  if (imageCache[key] || loadingMap[key]) return // 已缓存 / 加载中，跳过
  const gen = generation
  loadingMap[key] = true
  try {
    const list = await fetchActorImages(Number(key))
    if (gen !== generation) return // 期间筛选/reload 已失效本次结果
    imageCache[key] = list
  } catch (e) {
    if (gen !== generation) return
    ElMessage.error(e instanceof Error ? e.message : '加载失败')
  } finally {
    if (gen === generation) loadingMap[key] = false
  }
}

/** 展开变化：新增展开的声优若未缓存则拉取 */
watch(expandedIds, (now, prev) => {
  for (const key of now) {
    if (!prev.includes(key)) void loadActor(key)
  }
})

// ---------- 失效与刷新 ----------

/** 清空图片缓存（保留声优骨架） */
function clearCache() {
  for (const k of Object.keys(imageCache)) delete imageCache[k]
}

/** 筛选（关键词/声优）变化：数据范围已变，清缓存 + 全部收起，重新按需加载 */
watch(
  () => [props.keyword, props.filterActorId],
  () => {
    generation++
    clearCache()
    expandedIds.value = []
  },
)

/**
 * 刷新：清缓存并重新拉取当前展开中的声优（保持展开状态）。
 * 父组件在上传成功 / 切回页面时调用；未展开的声优缓存清掉，下次展开自然拉到最新。
 */
function reload() {
  generation++
  clearCache()
  for (const key of expandedIds.value) void loadActor(key)
}

defineExpose({ reload })

// ---------- 组内操作（与表格视图对齐） ----------

/** 切换中的图片 id（el-switch :loading，期间不可再点） */
const pendingToggle = reactive<Record<number, boolean>>({})

async function onToggleChange(img: ImageItem, val: string | number | boolean) {
  const newVal = val === true
  pendingToggle[img.id] = true
  try {
    await api.updateImage(img.id, newVal)
    ElMessage.success('图片状态已更新')
  } catch (e) {
    img.is_active = !newVal // 失败回滚开关
    ElMessage.error(e instanceof Error ? e.message : '更新失败')
  } finally {
    pendingToggle[img.id] = false
  }
}

/** 删除进行中标记：防并发删除 */
const deleting = ref(false)

async function onDelete(img: ImageItem) {
  if (deleting.value) return
  deleting.value = true
  try {
    await api.deleteImage(img.id)
    // 局部更新：从所属声优的缓存中移除该图
    const key = cacheKey(img.voice_actor_id)
    const list = imageCache[key]
    if (list) {
      const idx = list.findIndex((i) => i.id === img.id)
      if (idx !== -1) list.splice(idx, 1)
    }
    ElMessage.success('图片已删除')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '删除失败')
  } finally {
    deleting.value = false
  }
}

/** 组头张数：已加载显示实际数，未加载显示声优总图数（image_count） */
function visibleCount(actor: VoiceActor): number {
  const cached = imageCache[cacheKey(actor.id)]
  return cached ? cached.length : actor.image_count
}
</script>

<template>
  <div class="grouped">
    <el-collapse v-model="expandedIds">
      <el-collapse-item
        v-for="a in groups"
        :key="a.id"
        :name="cacheKey(a.id)"
        :disabled="a.image_count === 0"
      >
        <template #title>
          <div class="group-title">
            <span class="group-name">{{ a.name }}</span>
            <el-tag v-if="a.image_count > 0" size="small">{{ visibleCount(a) }} 张</el-tag>
            <span v-else class="empty-text">无可用图片</span>
            <el-tag v-if="!a.is_active" size="small" type="info">已禁用</el-tag>
          </div>
        </template>

        <div class="group-body">
          <!-- 该声优加载中 -->
          <div v-if="loadingMap[cacheKey(a.id)]" class="loading-tip">加载中…</div>

          <template v-else-if="(imageCache[cacheKey(a.id)] ?? []).length">
            <div v-for="img in imageCache[cacheKey(a.id)]" :key="img.id" class="img-cell">
              <el-image
                class="grid-thumb"
                :src="imageFileUrl(img.id)"
                fit="cover"
                lazy
                :preview-src-list="[imageFileUrl(img.id)]"
                preview-teleported
              />
              <!-- hover 操作条：启用开关 + 删除 -->
              <div class="img-actions">
                <el-switch
                  v-model="img.is_active"
                  size="small"
                  :loading="pendingToggle[img.id]"
                  @change="(val) => onToggleChange(img, val)"
                />
                <el-popconfirm
                  :title="`确定删除图片「${img.filename}」吗？此操作会同时删除文件，不可撤销。`"
                  confirm-button-text="删除"
                  cancel-button-text="取消"
                  @confirm="onDelete(img)"
                >
                  <template #reference>
                    <el-button type="danger" size="small" text>删除</el-button>
                  </template>
                </el-popconfirm>
              </div>
              <div class="img-name" :title="img.filename">{{ img.filename }}</div>
            </div>
          </template>

          <!-- 已加载但无图（或筛选后无匹配） -->
          <el-empty v-else description="暂无图片" :image-size="60" />
        </div>
      </el-collapse-item>
    </el-collapse>
  </div>
</template>

<style scoped>
.grouped {
  min-height: 160px;
}

.group-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.group-name {
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.empty-text {
  font-size: 13px;
  color: var(--el-text-color-placeholder);
}

.loading-tip {
  padding: 24px 0;
  text-align: center;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.group-body {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(132px, 1fr));
  gap: 12px;
  padding: 4px 8px 8px;
}

.img-cell {
  position: relative;
}

.grid-thumb {
  display: block;
  width: 100%;
  aspect-ratio: 1;
  border-radius: 6px;
  background-color: var(--el-fill-color-light);
  cursor: pointer;
}

.img-actions {
  position: absolute;
  top: 6px;
  right: 6px;
  display: none;
  align-items: center;
  gap: 2px;
  padding: 4px 6px;
  background-color: rgba(255, 255, 255, 0.92);
  border-radius: 6px;
  box-shadow: var(--el-box-shadow-light);
}

.img-cell:hover .img-actions {
  display: flex;
}

.img-name {
  margin-top: 6px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
