import { useRef, useState } from 'react'

/** Records mic audio in the browser; calls onBlob when stopped. Needs HTTPS or localhost. */
export function useRecorder(onBlob) {
  const [recording, setRecording] = useState(false)
  const rec = useRef(null)
  const toggle = async () => {
    if (rec.current) { rec.current.stop(); return }
    let stream
    try { stream = await navigator.mediaDevices.getUserMedia({ audio: true }) }
    catch { alert('Microphone blocked. Allow it in the browser (HTTPS or localhost only).'); return }
    const r = new MediaRecorder(stream); const chunks = []
    r.ondataavailable = (e) => chunks.push(e.data)
    r.onstop = () => {
      stream.getTracks().forEach((t) => t.stop())
      rec.current = null; setRecording(false)
      onBlob(new Blob(chunks, { type: r.mimeType }))
    }
    r.start(); rec.current = r; setRecording(true)
  }
  return { recording, toggle }
}
