// pai-inbox: Cloudflare Email Worker for agents@ and security@.
// Tags each message with its request type and forwards it to the maintainer inbox.
// Docs: https://developers.cloudflare.com/email-service/api/route-emails/email-handler/

export const TYPES = ['bug', 'install', 'model', 'feature', 'docs']
const MAX_BYTES = 10 * 1024 * 1024

// "[Install] help" -> "install"; unknown or missing tag -> "general".
export function requestType(subject = '', to = '') {
  if (to.toLowerCase().startsWith('security@')) return 'security'
  const tag = /^\s*(?:(?:re|fwd?):\s*)*\[([a-z]+)\]/i.exec(subject)?.[1]?.toLowerCase()
  return TYPES.includes(tag) ? tag : 'general'
}

export default {
  async email(message, env) {
    if (message.rawSize > MAX_BYTES) {
      message.setReject('Message too large; please send logs as a link.')
      return
    }
    const type = requestType(message.headers.get('subject') || '', message.to)
    // shortcut: forward-only notification; add auto-reply or GitHub issue creation when volume needs it.
    await message.forward(
      env.FORWARD_TO,
      new Headers({ 'X-PAI-Request-Type': type, 'X-PAI-Workflow': `docs/agent-workflows/${type}` }),
    )
  },
}
