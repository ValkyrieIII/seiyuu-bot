// 模块级内存数据（模拟数据库表）：POST/PATCH/DELETE 直接修改这些数组以模拟副作用
// 字段与 backend/bot/admin/routes.py 各接口返回逐字段对齐
//
// 注意：vite-plugin-mock 会为每个 mock 文件单独 esbuild 打包，直接 import 本文件
// 会在每个 bundle 内联一份独立拷贝，导致各接口之间的状态互不可见。
// 因此真实状态挂在 globalThis 上（各 bundle 共享同一 dev server 进程），
// 本文件只是种子数据 + 状态访问层。修改 mock 文件触发重新打包时状态也得以保留。
// 本文件不导出 MockMethod，仅作为共享状态被各接口 mock 文件引用

export interface MockActor {
  id: number
  name: string
  description: string
  image_count: number
  is_active: boolean
}

export interface MockAlias {
  id: number
  alias_name: string
  target_voice_actor_id: number
  priority: number
  description: string
  is_global: boolean
  is_active: boolean
}

export interface MockImage {
  id: number
  voice_actor_id: number
  filename: string
  file_path: string
  size_kb: number
  file_hash: string
  is_active: boolean
  created_at: string
}

interface MockState {
  actors: MockActor[]
  aliases: MockAlias[]
  images: MockImage[]
  seqActor: number
  seqAlias: number
  seqImage: number
}

const GLOBAL_KEY = '__seiyuu_bot_mock_state__'
const g = globalThis as unknown as Record<string, MockState | undefined>

/** 种子数据（仅首次求值时初始化一次，之后各 bundle 共用同一份状态） */
if (!g[GLOBAL_KEY]) {
  g[GLOBAL_KEY] = {
    actors: [
      { id: 1, name: '中岛由贵', description: '日本女性声优，代表角色：莱莎琳·斯托特（莱莎的炼金工房）', image_count: 6, is_active: true },
      { id: 2, name: '高桥李依', description: '日本女性声优，代表角色：玛修·基列莱特（Fate/Grand Order）', image_count: 4, is_active: true },
      { id: 3, name: '水濑祈', description: '日本女性声优，代表角色：雷姆（Re:从零开始的异世界生活）', image_count: 4, is_active: true },
      { id: 4, name: '早见沙织', description: '日本女性声优，代表角色：雪之下雪乃（我的青春恋爱物语果然有问题）', image_count: 3, is_active: true },
      { id: 5, name: '花泽香菜', description: '日本女性声优，代表角色：千石抚子（物语系列）', image_count: 3, is_active: true },
      { id: 6, name: '东山奈央', description: '日本女性声优，代表角色：桐崎千棘（伪恋）', image_count: 2, is_active: true },
      { id: 7, name: '佐仓绫音', description: '日本女性声优，代表角色：宝多六花（SSSS.GRIDMAN）', image_count: 2, is_active: false },
      { id: 8, name: '茅野爱衣', description: '日本女性声优，代表角色：椎名真白（樱花庄的宠物女孩）', image_count: 1, is_active: false },
    ],
    aliases: [
      { id: 1, alias_name: '贵贵', target_voice_actor_id: 1, priority: 10, description: '中岛由贵的常见昵称', is_global: true, is_active: true },
      { id: 2, alias_name: '李依酱', target_voice_actor_id: 2, priority: 9, description: '高桥李依的昵称', is_global: true, is_active: true },
      { id: 3, alias_name: '雷姆酱', target_voice_actor_id: 3, priority: 10, description: '水濑祈代表角色名', is_global: true, is_active: true },
      { id: 4, alias_name: '由贵', target_voice_actor_id: 1, priority: 8, description: '中岛由贵的简称', is_global: true, is_active: true },
      { id: 5, alias_name: '沙织', target_voice_actor_id: 4, priority: 8, description: '早见沙织的简称', is_global: true, is_active: true },
      { id: 6, alias_name: '祈酱', target_voice_actor_id: 3, priority: 7, description: '水濑祈的昵称', is_global: true, is_active: true },
      { id: 7, alias_name: '香菜', target_voice_actor_id: 5, priority: 7, description: '花泽香菜的简称', is_global: true, is_active: true },
      { id: 8, alias_name: '小贵', target_voice_actor_id: 1, priority: 6, description: '中岛由贵的昵称', is_global: true, is_active: true },
      { id: 9, alias_name: '六花酱', target_voice_actor_id: 7, priority: 6, description: '用户自定义别名', is_global: false, is_active: true },
      { id: 10, alias_name: '高桥', target_voice_actor_id: 2, priority: 5, description: '高桥李依的简称', is_global: true, is_active: true },
    ],
    images: [
      // 中岛由贵（6 张）
      { id: 1, voice_actor_id: 1, filename: '中岛由贵_000001.jpg', file_path: '/app/images/中岛由贵/中岛由贵_000001.jpg', size_kb: 842, file_hash: '3a1f9c2d4e5b6a7c8d9e0f1a2b3c4d5e', is_active: true, created_at: '2026-08-13T18:42:11' },
      { id: 2, voice_actor_id: 1, filename: '中岛由贵_000002.jpg', file_path: '/app/images/中岛由贵/中岛由贵_000002.jpg', size_kb: 512, file_hash: '9b8c7d6e5f4a3b2c1d0e9f8a7b6c5d4e', is_active: true, created_at: '2026-08-12T09:15:33' },
      { id: 3, voice_actor_id: 1, filename: '中岛由贵_000003.jpg', file_path: '/app/images/中岛由贵/中岛由贵_000003.jpg', size_kb: 1204, file_hash: '4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a', is_active: true, created_at: '2026-08-10T14:22:05' },
      { id: 4, voice_actor_id: 1, filename: '中岛由贵_000004.png', file_path: '/app/images/中岛由贵/中岛由贵_000004.png', size_kb: 2368, file_hash: 'a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6', is_active: true, created_at: '2026-08-08T11:05:47' },
      { id: 5, voice_actor_id: 1, filename: '中岛由贵_000005.jpg', file_path: '/app/images/中岛由贵/中岛由贵_000005.jpg', size_kb: 356, file_hash: '7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b', is_active: true, created_at: '2026-08-05T16:40:19' },
      { id: 6, voice_actor_id: 1, filename: '中岛由贵_000006.jpg', file_path: '/app/images/中岛由贵/中岛由贵_000006.jpg', size_kb: 981, file_hash: '2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f', is_active: true, created_at: '2026-08-02T10:18:52' },
      // 高桥李依（4 张）
      { id: 7, voice_actor_id: 2, filename: '高桥李依_000001.jpg', file_path: '/app/images/高桥李依/高桥李依_000001.jpg', size_kb: 1287, file_hash: '5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c', is_active: true, created_at: '2026-08-11T13:33:27' },
      { id: 8, voice_actor_id: 2, filename: '高桥李依_000002.jpg', file_path: '/app/images/高桥李依/高桥李依_000002.jpg', size_kb: 743, file_hash: '8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d', is_active: true, created_at: '2026-08-09T08:57:41' },
      { id: 9, voice_actor_id: 2, filename: '高桥李依_000003.png', file_path: '/app/images/高桥李依/高桥李依_000003.png', size_kb: 1982, file_hash: '0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a', is_active: true, created_at: '2026-08-06T19:24:36' },
      { id: 10, voice_actor_id: 2, filename: '高桥李依_000004.jpg', file_path: '/app/images/高桥李依/高桥李依_000004.jpg', size_kb: 621, file_hash: '6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e', is_active: true, created_at: '2026-08-03T15:48:09' },
      // 水濑祈（4 张）
      { id: 11, voice_actor_id: 3, filename: '水濑祈_000001.png', file_path: '/app/images/水濑祈/水濑祈_000001.png', size_kb: 2751, file_hash: '3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b', is_active: true, created_at: '2026-08-11T10:12:55' },
      { id: 12, voice_actor_id: 3, filename: '水濑祈_000002.png', file_path: '/app/images/水濑祈/水濑祈_000002.png', size_kb: 1894, file_hash: '9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f', is_active: true, created_at: '2026-08-07T12:36:18' },
      { id: 13, voice_actor_id: 3, filename: '水濑祈_000003.jpg', file_path: '/app/images/水濑祈/水濑祈_000003.jpg', size_kb: 1043, file_hash: '1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c', is_active: true, created_at: '2026-08-04T17:09:44' },
      { id: 14, voice_actor_id: 3, filename: '水濑祈_000004.png', file_path: '/app/images/水濑祈/水濑祈_000004.png', size_kb: 2245, file_hash: '7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a', is_active: true, created_at: '2026-08-01T09:53:21' },
      // 早见沙织（3 张）
      { id: 15, voice_actor_id: 4, filename: '早见沙织_000001.jpg', file_path: '/app/images/早见沙织/早见沙织_000001.jpg', size_kb: 965, file_hash: '4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e', is_active: true, created_at: '2026-08-10T20:31:58' },
      { id: 16, voice_actor_id: 4, filename: '早见沙织_000002.jpg', file_path: '/app/images/早见沙织/早见沙织_000002.jpg', size_kb: 1380, file_hash: '0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b', is_active: true, created_at: '2026-08-06T11:26:13' },
      { id: 17, voice_actor_id: 4, filename: '早见沙织_000003.jpg', file_path: '/app/images/早见沙织/早见沙织_000003.jpg', size_kb: 507, file_hash: '6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d', is_active: true, created_at: '2026-07-30T14:47:36' },
      // 花泽香菜（3 张）
      { id: 18, voice_actor_id: 5, filename: '花泽香菜_000001.jpg', file_path: '/app/images/花泽香菜/花泽香菜_000001.jpg', size_kb: 1120, file_hash: '2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c', is_active: true, created_at: '2026-08-09T16:18:42' },
      { id: 19, voice_actor_id: 5, filename: '花泽香菜_000002.webp', file_path: '/app/images/花泽香菜/花泽香菜_000002.webp', size_kb: 684, file_hash: '8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f', is_active: true, created_at: '2026-08-05T13:41:26' },
      { id: 20, voice_actor_id: 5, filename: '花泽香菜_000003.jpg', file_path: '/app/images/花泽香菜/花泽香菜_000003.jpg', size_kb: 1567, file_hash: '5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a', is_active: true, created_at: '2026-07-28T10:04:57' },
      // 东山奈央（2 张）
      { id: 21, voice_actor_id: 6, filename: '东山奈央_000001.jpg', file_path: '/app/images/东山奈央/东山奈央_000001.jpg', size_kb: 892, file_hash: '1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e', is_active: true, created_at: '2026-08-08T15:23:10' },
      { id: 22, voice_actor_id: 6, filename: '东山奈央_000002.jpg', file_path: '/app/images/东山奈央/东山奈央_000002.jpg', size_kb: 429, file_hash: '7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c', is_active: true, created_at: '2026-07-25T09:37:48' },
      // 佐仓绫音（2 张，图片停用）
      { id: 23, voice_actor_id: 7, filename: '佐仓绫音_000001.jpg', file_path: '/app/images/佐仓绫音/佐仓绫音_000001.jpg', size_kb: 1185, file_hash: '3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a', is_active: true, created_at: '2026-08-07T18:55:03' },
      { id: 24, voice_actor_id: 7, filename: '佐仓绫音_000002.jpg', file_path: '/app/images/佐仓绫音/佐仓绫音_000002.jpg', size_kb: 764, file_hash: '9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d', is_active: false, created_at: '2026-07-22T14:29:31' },
      // 茅野爱衣（1 张，图片停用）
      { id: 25, voice_actor_id: 8, filename: '茅野爱衣_000001.jpg', file_path: '/app/images/茅野爱衣/茅野爱衣_000001.jpg', size_kb: 1342, file_hash: '5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b', is_active: false, created_at: '2026-07-18T11:12:09' },
    ],
    seqActor: 100,
    seqAlias: 100,
    seqImage: 100,
  }
}

const state = g[GLOBAL_KEY] as MockState

/** 声优表（共享实例，各 mock 接口 bundle 读写同一份） */
export const actors: MockActor[] = state.actors
/** 别名表（共享实例） */
export const aliases: MockAlias[] = state.aliases
/** 图片表（共享实例） */
export const images: MockImage[] = state.images

// 自增 ID 计数器（起始值高于现有最大 ID，模拟数据库自增）
export function nextActorId(): number {
  return state.seqActor++
}

export function nextAliasId(): number {
  return state.seqAlias++
}

export function nextImageId(): number {
  return state.seqImage++
}
