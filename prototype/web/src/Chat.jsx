import { AssistantRuntimeProvider, ComposerPrimitive, MessagePrimitive, ThreadPrimitive, useAui, useAuiState, useLocalRuntime } from '@assistant-ui/react'
import { MarkdownTextPrimitive } from '@assistant-ui/react-markdown'
import remarkGfm from 'remark-gfm'
import { ArrowUp, Mic, Square, Volume2, VolumeX } from 'lucide-react'
import { useRef, useState } from 'react'
import { paiAdapter } from './api.js'
import { useRecorder } from './useRecorder.js'

const Text = () => <MarkdownTextPrimitive remarkPlugins={[remarkGfm]} />

const UserMessage = () => (
  <MessagePrimitive.Root className="msg-user"><MessagePrimitive.Parts /></MessagePrimitive.Root>
)

const AssistantMessage = () => (
  <MessagePrimitive.Root className="msg-pai">
    <span className="avatar" aria-hidden>P</span>
    <div className="text"><MessagePrimitive.Parts components={{ Text }} /></div>
  </MessagePrimitive.Root>
)

function Composer({ speak, setSpeak }) {
  const aui = useAui()
  const running = useAuiState((s) => s.thread.isRunning)
  const { recording, toggle } = useRecorder(async (blob) => {
    const fd = new FormData(); fd.append('audio', blob, 'speech.webm')
    const r = await fetch('/api/transcribe', { method: 'POST', body: fd }).then((x) => x.json())
    if (r.text) aui.composer().setText(r.text) // you review it, then press send
  })
  return (
    <ComposerPrimitive.Root className="composer">
      <ComposerPrimitive.Input rows={1} autoFocus placeholder="Ask PAI, or say “remember …”" aria-label="Message PAI" />
      <button type="button" className="icon-btn" onClick={() => setSpeak(!speak)} aria-label={speak ? 'Turn spoken replies off' : 'Turn spoken replies on'} aria-pressed={speak}>
        {speak ? <Volume2 size={18} /> : <VolumeX size={18} />}
      </button>
      <button type="button" className={`icon-btn ${recording ? 'rec' : ''}`} onClick={toggle} aria-label={recording ? 'Stop recording' : 'Dictate'}>
        {recording ? <Square size={16} /> : <Mic size={18} />}
      </button>
      {running ? (
        <ComposerPrimitive.Cancel asChild><button type="button" className="icon-btn send" aria-label="Stop"><Square size={16} /></button></ComposerPrimitive.Cancel>
      ) : (
        <ComposerPrimitive.Send asChild><button type="submit" className="icon-btn send" aria-label="Send"><ArrowUp size={18} /></button></ComposerPrimitive.Send>
      )}
    </ComposerPrimitive.Root>
  )
}

// Speaks each finished PAI reply when the speaker toggle is on; audio comes from the box.
function useSpeak(enabled) {
  const audio = useRef(null)
  return async (text) => {
    if (!enabled || !text) return
    const r = await fetch('/api/speak', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text }) })
    if (!r.ok) return
    const { audio: b64 } = await r.json()
    audio.current?.pause()
    audio.current = new Audio(`data:audio/mpeg;base64,${b64}`)
    audio.current.play().catch(() => {})
  }
}

export function Chat() {
  const [speak, setSpeak] = useState(false)
  const say = useSpeak(speak)
  const runtime = useLocalRuntime({
    async run(opts) {
      const result = await paiAdapter.run(opts)
      say(result.content[0].text)
      return result
    },
  })
  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <ThreadPrimitive.Root className="thread">
        <ThreadPrimitive.Viewport className="viewport">
          <ThreadPrimitive.Empty>
            <div className="empty"><h2>What can I help with?</h2><span>Everything here runs on this box.</span></div>
          </ThreadPrimitive.Empty>
          <ThreadPrimitive.Messages components={{ UserMessage, AssistantMessage }} />
        </ThreadPrimitive.Viewport>
        <Composer speak={speak} setSpeak={setSpeak} />
        <p className="note">PAI can be wrong. It asks before it sends, deletes or spends anything.</p>
      </ThreadPrimitive.Root>
    </AssistantRuntimeProvider>
  )
}
