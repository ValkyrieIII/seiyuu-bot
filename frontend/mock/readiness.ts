import type { MockMethod } from 'vite-plugin-mock'
import { ok } from './_utils'

export default [{
  url: '/admin/api/readiness',
  method: 'get',
  response: () => ok({
    ready: true,
    database: { ready: true, error_code: null },
    onebot: { ready: true, error_code: null, connected_bots: 1 },
  }),
}] satisfies MockMethod[]
