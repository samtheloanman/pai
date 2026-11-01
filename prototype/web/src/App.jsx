import { useState } from 'react'
import { Chat } from './Chat.jsx'
import { Memory, Rules, Setup } from './Panels.jsx'

const TABS = [['chat', 'Chat'], ['setup', 'Setup'], ['rules', 'Rules'], ['memory', 'Memory']]

export function App() {
  const [tab, setTab] = useState('chat')
  return (
    <div className="shell">
      <header className="top">
        <span className="brand">PAI</span>
        <nav className="tabs" aria-label="Sections">
          {TABS.map(([id, label]) => (
            <button key={id} aria-current={tab === id} onClick={() => setTab(id)}>{label}</button>
          ))}
        </nav>
      </header>
      <main className="body">
        {tab === 'chat' && <Chat />}
        {tab === 'setup' && <Setup onDone={() => setTab('rules')} />}
        {tab === 'rules' && <Rules />}
        {tab === 'memory' && <Memory />}
      </main>
    </div>
  )
}
