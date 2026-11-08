import { AssistantRuntimeProvider, ComposerPrimitive, MessagePrimitive, ThreadPrimitive, useAui, useAuiState, useLocalRuntime } from '@assistant-ui/react'
import { MarkdownTextPrimitive } from '@assistant-ui/react-markdown'
import remarkGfm from 'remark-gfm'
import { ArrowUp, Cloud, Mic, Square, Volume2, VolumeX } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { api, paiAdapter } from './api.js'
import { isImeComposing } from './format.js'
import { useRecorder } from './useRecorder.js'

const Text = () => <MarkdownTextPrimitive remarkPlugins={[remarkGfm]} />

const PERSONAS = [
  { id: 'hermes', name: 'Hermes Core', role: 'Primary Local Assistant', badge: 'Voice & Chat' },
  { id: 'chief', name: 'Chief of Staff', role: 'Daily Briefings & Priorities', badge: 'Paperclip' },
  { id: 'rakazo', name: 'Rakazo Research', role: 'Sandboxed Web & Document Analysis', badge: 'Sandbox' },
  { id: 'auditor', name: 'Policy Reviewer', role: 'Vault & Outbound Guard', badge: 'Local Gate' },
]

const STARTERS = [
  'Remember our client call priority order is Mona, Summer, then Sam.',
  'What do you know about me and my operating rules so far?',
  'Draft a concise morning operations checklist from my priorities.',
  'How are sensitive numbers and memories protected on this machine?',
]

const UserMessage = () => (
  <MessagePrimitive.Root className="msg-user"><MessagePrimitive.Parts /></MessagePrimitive.Root>
)

const AssistantMessage = () => (
  <MessagePrimitive.Root className="msg-pai">
    <span className="avatar" aria-hidden>H</span>
    <div className="text"><MessagePrimitive.Parts components={{ Text }} /></div>
  </MessagePrimitive.Root>
)

function QuickPrompts({ onPick }) {
  const aui = useAui()
  const sendStarter = (p) => {
    aui.composer().setText(p)
    onPick?.(p)
  }
  return (
    <div className="starter-grid">
      {STARTERS.map((s) => (
        <button key={s} type="button" className="starter-card" onClick={() => sendStarter(s)}>
          <span>{s}</span>
        </button>
      ))}
    </div>
  )
}

function Composer({ speak, setSpeak, canCloud, cloud, setCloud, onRecordingChange }) {
  const aui = useAui()
  const running = useAuiState((s) => s.thread.isRunning)
  const { recording, toggle } = useRecorder(async (blob) => {
    const fd = new FormData()
    fd.append('audio', blob, 'speech.webm')
    const r = await fetch('/api/transcribe', { method: 'POST', body: fd }).then((x) => x.json())
    if (r.text) aui.composer().setText(r.text)
  })
  useEffect(() => { onRecordingChange?.(recording || running) }, [recording, running, onRecordingChange])
  return (
    <ComposerPrimitive.Root className="composer">
      <label htmlFor="chat-composer-input" className="sr-only">Message PAI</label>
      <ComposerPrimitive.Input
        id="chat-composer-input"
        rows={1}
        autoFocus
        placeholder="Ask a question, dictate by voice, or say “remember …”"
        aria-label="Message PAI"
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey && isImeComposing(e)) {
            e.preventDefault()
            e.stopPropagation()
          }
        }}
      />
      {canCloud && (
        <button type="button" className="icon-btn cloud-toggle" onClick={() => setCloud(!cloud)} aria-pressed={cloud} aria-label="Allow a cloud model for this message" title="Cloud, this message only">
          <Cloud size={17} />
        </button>
      )}
      <button type="button" className="icon-btn" onClick={() => setSpeak(!speak)} aria-label={speak ? 'Turn spoken replies off' : 'Turn spoken replies on'} aria-pressed={speak}>
        {speak ? <Volume2 size={17} /> : <VolumeX size={17} />}
      </button>
      <button type="button" className={`icon-btn ${recording ? 'rec' : ''}`} onClick={toggle} aria-label={recording ? 'Stop recording' : 'Dictate'}>
        {recording ? <Square size={15} /> : <Mic size={17} />}
      </button>
      {running ? (
        <ComposerPrimitive.Cancel asChild><button type="button" className="icon-btn send" aria-label="Stop"><Square size={15} /></button></ComposerPrimitive.Cancel>
      ) : (
        <ComposerPrimitive.Send asChild><button type="submit" className="icon-btn send" aria-label="Send"><ArrowUp size={17} /></button></ComposerPrimitive.Send>
      )}
    </ComposerPrimitive.Root>
  )
}

function useSpeak(enabled, setSpeaking) {
  const audio = useRef(null)
  return async (text) => {
    if (!enabled || !text) return
    setSpeaking?.(true)
    try {
      const r = await fetch('/api/speak', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text }) })
      if (!r.ok) { setSpeaking?.(false); return }
      const { audio: b64 } = await r.json()
      audio.current?.pause()
      audio.current = new Audio(`data:audio/mpeg;base64,${b64}`)
      audio.current.onended = () => setSpeaking?.(false)
      audio.current.play().catch(() => setSpeaking?.(false))
    } catch {
      setSpeaking?.(false)
    }
  }
}

export function Chat({ onNavigate }) {
  const [speak, setSpeak] = useState(false)
  const [speaking, setSpeaking] = useState(false)
  const [voiceActive, setVoiceActive] = useState(false)
  const say = useSpeak(speak, setSpeaking)
  const [canCloud, setCanCloud] = useState(false)
  const [cloud, setCloudState] = useState(false)
  const [persona, setPersona] = useState(PERSONAS[0])
  const [mems, setMems] = useState([])
  const [routeProbe, setRouteProbe] = useState('')
  const [routeResult, setRouteResult] = useState(null)

  const cloudRef = useRef(false)
  const setCloud = (v) => { cloudRef.current = v; setCloudState(v) }

  const refreshMems = () => api('/api/memories').then(setMems).catch(() => {})

  useEffect(() => {
    api('/api/providers').then((p) => setCanCloud(p.cloud_enabled && p.providers.some((x) => x.has_key && x.cloud))).catch(() => {})
    refreshMems()
  }, [])

  const runtime = useLocalRuntime({
    async run(opts) {
      const asked = cloudRef.current
      setCloud(false)
      const result = await paiAdapter.run({ ...opts, cloud: asked })
      refreshMems()
      say(result.content[0].text)
      return result
    },
  })

  const testRoute = async (e) => {
    e.preventDefault()
    if (!routeProbe.trim()) return
    try {
      const r = await api('/api/route', { method: 'POST', body: JSON.stringify({ message: routeProbe, history: [] }) })
      setRouteResult(r)
    } catch (err) {
      setRouteResult({ route: 'error', tier: '-', score: err.message })
    }
  }

  const audioStateLabel = speaking ? 'Speaking reply' : voiceActive ? 'Listening' : 'Idle'

  return (
    <div className="hermes-cockpit">
      <aside className="cockpit-rail" aria-label="Profiles and memory">
        <div className="rail-section">
          <div className="rail-section-head">
            <span>Assistant Profile</span>
          </div>
          <div className="persona-list">
            {PERSONAS.map((p) => (
              <button
                key={p.id}
                type="button"
                className={`persona-item ${persona.id === p.id ? 'active' : ''}`}
                onClick={() => setPersona(p)}
              >
                <div>
                  <strong>{p.name}</strong>
                  <span>{p.role}</span>
                </div>
                <em className="persona-badge">{p.badge}</em>
              </button>
            ))}
          </div>
        </div>

        <div className="rail-section">
          <div className="rail-section-head">
            <span>Voice &amp; Audio</span>
            <span className="status-tag">{audioStateLabel}</span>
          </div>
          <div className="telemetry-kv">
            <div><span>Speech-to-text</span><code>Faster-Whisper</code></div>
            <div><span>Text-to-speech</span><code>Kokoro-82M</code></div>
            <div><span>Spoken replies</span><code>{speak ? 'Enabled' : 'Muted'}</code></div>
          </div>
        </div>

        <div className="rail-section">
          <div className="rail-section-head">
            <span>Saved Memories ({mems.length})</span>
            {onNavigate && (
              <button type="button" className="link-btn" onClick={() => onNavigate('memory')}>View all</button>
            )}
          </div>
          {mems.length === 0 ? (
            <p className="muted" style={{ fontSize: 12.5, margin: 0 }}>No facts stored yet. Start a message with “remember …” to save one.</p>
          ) : (
            <div className="mini-mem-list">
              {mems.slice(0, 4).map((m) => (
                <div key={m.id} className="mini-mem-item">
                  <code>#{m.id}</code> <span>{m.text}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </aside>

      <div className="cockpit-center">
        <div className="cockpit-banner">
          <div className="row">
            <strong>{persona.name}</strong>
            <span className="muted">{persona.role}</span>
          </div>
          <span className="status-tag">Local model · 0 API keys</span>
        </div>

        <AssistantRuntimeProvider runtime={runtime}>
          <ThreadPrimitive.Root className="thread">
            <ThreadPrimitive.Viewport className="viewport">
              <ThreadPrimitive.Empty>
                <div className="empty">
                  <h2>How can I help today?</h2>
                  <span>Everything runs locally on this machine. Choose a prompt or type below.</span>
                  <QuickPrompts />
                </div>
              </ThreadPrimitive.Empty>
              <ThreadPrimitive.Messages components={{ UserMessage, AssistantMessage }} />
            </ThreadPrimitive.Viewport>
            <Composer
              speak={speak}
              setSpeak={setSpeak}
              canCloud={canCloud}
              cloud={cloud}
              setCloud={setCloud}
              onRecordingChange={setVoiceActive}
            />
            <p className="note">PAI asks for confirmation before sending, deleting, or spending anything.</p>
          </ThreadPrimitive.Root>
        </AssistantRuntimeProvider>
      </div>

      <aside className="cockpit-rail" aria-label="Routing and system status">
        <div className="rail-section">
          <div className="rail-section-head">
            <span>Intent Router Inspector</span>
          </div>
          <p className="muted" style={{ fontSize: 12.5, margin: 0 }}>
            Preview how a prompt is classified across Rule (Tier 1), Vector (Tier 2), or Local Model (Tier 3):
          </p>
          <form onSubmit={testRoute} className="probe-form">
            <label htmlFor="route-probe-input" className="sr-only">Test router prompt</label>
            <input
              id="route-probe-input"
              value={routeProbe}
              onChange={(e) => setRouteProbe(e.target.value)}
              placeholder="e.g., remember my gate code is 4412"
            />
            <button type="submit" className="btn btn-sm">Inspect route</button>
          </form>
          {routeResult && (
            <div className="probe-result">
              <div><span>Route</span><code>{routeResult.route}</code></div>
              <div><span>Tier</span><code>Tier {routeResult.tier}</code></div>
              <div><span>Confidence</span><code>{typeof routeResult.score === 'number' ? routeResult.score.toFixed(2) : routeResult.score}</code></div>
            </div>
          )}
        </div>

        <div className="rail-section">
          <div className="rail-section-head">
            <span>Local Services</span>
          </div>
          <div className="telemetry-kv">
            <div><span>Inference</span><code>llama.cpp :8080</code></div>
            <div><span>Router</span><code>LiteLLM :4000</code></div>
            <div><span>Speech</span><code>Speaches :8000</code></div>
            <div><span>Storage</span><code>SQLite + FTS5</code></div>
            <div><span>Outbound</span><code>{canCloud ? 'Optional' : 'Blocked'}</code></div>
          </div>
        </div>
      </aside>
    </div>
  )
}
