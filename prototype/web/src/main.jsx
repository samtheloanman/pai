import { createRoot } from 'react-dom/client'
import './styles.css'
import { App } from './App.jsx'
import { Gate } from './Auth.jsx'

createRoot(document.getElementById('root')).render(<Gate><App /></Gate>)
