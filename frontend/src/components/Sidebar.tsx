import { useState, useEffect } from 'react'
import { NavLink } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useStore } from '../store'
import { Settings as SettingsIcon } from 'lucide-react'
import { getBase } from '../api/client'

const NAV_ITEMS = [
  { to: '/', label: 'nav.downloader', kanji: '載', exact: true },
  { to: '/history', label: 'nav.history', kanji: '歴', exact: false },
  { to: '/editor', label: 'nav.editor', kanji: '編', exact: false },
  { to: '/converter', label: 'nav.converter', kanji: '換', exact: false },
]

export default function Sidebar() {
  const { t } = useTranslation()
  const { setSettingsOpen } = useStore()
  const [online, setOnline] = useState(false)

  useEffect(() => {
    const check = async () => {
      try {
        const base = getBase()
        const url = `${base}/health`
        console.log("[Yuki] getBase():", base)
        console.log("[Yuki] health check URL:", url)
        const res = await fetch(url, {
          credentials: 'omit',
          signal: AbortSignal.timeout(3000),
        })
        console.log("[Yuki] health response:", res.status)
        setOnline(res.ok)
      } catch (err) {
        console.log("[Yuki] health check error:", err)
        setOnline(false)
      }
    }
    check()
    const id = setInterval(check, 3000)
    return () => clearInterval(id)
  }, [])

  return (
    <aside className="w-[180px] flex-shrink-0 flex flex-col bg-bg-secondary border-r border-border h-full">
      {/* Logo */}
      <div className="px-5 pt-6 pb-4 flex items-center gap-3">
        <span className="text-4xl text-accent leading-none select-none">雪</span>
        <span className="text-lg font-semibold text-white tracking-wide">Yuki</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-2 py-2 flex flex-col gap-1">
        {NAV_ITEMS.map(({ to, label, kanji, exact }) => (
          <NavLink
            key={to}
            to={to}
            end={exact}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors relative group ${
                isActive
                  ? 'bg-accent/20 text-white border-l-2 border-accent pl-[10px]'
                  : 'text-zinc-400 hover:text-white hover:bg-bg-card border-l-2 border-transparent pl-[10px]'
              }`
            }
          >
            <span className="text-xl w-6 text-center leading-none">{kanji}</span>
            <span>{t(label)}</span>
          </NavLink>
        ))}
      </nav>

      {/* Bottom */}
      <div className="px-3 pb-4 flex flex-col gap-2">
        <button
          onClick={() => setSettingsOpen(true)}
          className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-zinc-400 hover:text-white hover:bg-bg-card transition-colors w-full"
        >
          <SettingsIcon size={16} />
          <span>{t('nav.settings')}</span>
        </button>
        <div className="flex items-center gap-2 px-3 py-1">
          <span
            className={`w-2 h-2 rounded-full flex-shrink-0 ${
              online ? 'bg-green-500' : 'bg-red-500'
            }`}
          />
          <span className="text-xs text-zinc-500">v2.0.4</span>
        </div>
      </div>
    </aside>
  )
}
