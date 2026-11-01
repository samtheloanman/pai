// Plain-words lines for the audit log and approval cards. Reads known fields only.
const n = (v) => Number(v).toLocaleString('en-US')
const RISK = { send: 'Sends', delete: 'Deletes', spend: 'Spends', system: 'Changes system' }
export const riskLabel = (kind) => RISK[kind] || 'Changes system'

export function activityLine({ kind, fields: f = {} }) {
  const model = f['gen_ai.request.model']
  switch (kind) {
    case 'model_call': {
      if (f.error) return `Model call failed · ${model}`
      const i = f['gen_ai.usage.input_tokens'], o = f['gen_ai.usage.output_tokens']
      return i == null && o == null ? `Model call · ${model}` : `Model call · ${model} · ${n((i || 0) + (o || 0))} tokens`
    }
    case 'route': return `Routed to ${f['pai.route']} (tier ${f.tier})`
    case 'outbound': return `Sent to ${f['pai.provider']} · ${n(f.chars)} chars`
    case 'action_proposed': return 'Approval requested'
    case 'action_confirmed': return 'Approved'
    case 'action_rejected': return 'Rejected'
    case 'memory_added': return 'Memory added'
    case 'memory_deleted': return 'Memory deleted'
    case 'config_changed': return `Settings changed · ${f.what}`
    default: { const s = String(kind).replace(/_/g, ' '); return s.charAt(0).toUpperCase() + s.slice(1) }
  }
}
