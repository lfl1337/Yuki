import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useStore } from '../store'
import { apiFetch } from '../api/client'
import { LANGUAGES } from '../i18n'
import { X, ExternalLink, RefreshCw, Folder } from 'lucide-react'
import { applyTheme } from '../utils/theme'
import { pickFolder } from '../utils/dialog'

interface SettingsModalProps {
  open: boolean
  onClose: () => void
}

interface AppSettings {
  theme: string
  language: string
  download_folder: string
  ask_download_folder: boolean
  auto_load_last: boolean
  autostart: boolean
  ytdlp_auto_update: boolean
}

const defaultSettings: AppSettings = {
  theme: 'dark',
  language: 'en',
  download_folder: '',
  ask_download_folder: false,
  auto_load_last: false,
  autostart: false,
  ytdlp_auto_update: false,
}

function Toggle({
  checked,
  onChange,
}: {
  checked: boolean
  onChange: (v: boolean) => void
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
        checked ? 'bg-accent' : 'bg-zinc-600'
      }`}
    >
      <span
        className={`inline-block h-3.5 w-3.5 rounded-full bg-white shadow-sm transform transition-transform ${
          checked ? 'translate-x-4' : 'translate-x-0.5'
        }`}
      />
    </button>
  )
}

export default function Settings({ open, onClose }: SettingsModalProps) {
  const { t, i18n } = useTranslation()
  const { setSettingsOpen } = useStore()
  const [settings, setSettings] = useState<AppSettings>(defaultSettings)
  const [section, setSection] = useState<'appearance' | 'downloads' | 'system' | 'about'>(
    'appearance'
  )
  const [updateStatus, setUpdateStatus] = useState<string>('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!open) return
    apiFetch<Record<string, string>>('/api/v1/settings')
      .then((data) => {
        const parsed: Partial<AppSettings> = {}
        for (const [k, v] of Object.entries(data)) {
          try {
            ;(parsed as Record<string, unknown>)[k] = JSON.parse(v)
          } catch {
            ;(parsed as Record<string, unknown>)[k] = v
          }
        }
        setSettings({ ...defaultSettings, ...parsed })
      })
      .catch(() => {})
  }, [open])

  const set = <K extends keyof AppSettings>(key: K, value: AppSettings[K]) => {
    setSettings((s) => ({ ...s, [key]: value }))
    if (key === 'language') {
      i18n.changeLanguage(value as string)
    }
    if (key === 'theme') {
      applyTheme(value as string)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const payload = Object.entries(settings).map(([key, value]) => ({
        key,
        value: JSON.stringify(value),
      }))
      await apiFetch('/api/v1/settings/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
    } catch {}
    setSaving(false)
    onClose()
  }

  const handleCheckUpdate = async () => {
    setUpdateStatus('Checking…')
    try {
      const res = await apiFetch<{ has_update: boolean; latest_version: string }>(
        '/api/v1/updater/check-app',
        { method: 'POST' }
      )
      if (res.has_update) {
        setUpdateStatus(`Update available: v${res.latest_version}`)
      } else {
        setUpdateStatus('You are up to date.')
      }
    } catch {
      setUpdateStatus('Check failed.')
    }
  }

  if (!open) return null

  const SECTIONS = [
    { id: 'appearance', label: t('settings.appearance') },
    { id: 'downloads', label: t('settings.downloads') },
    { id: 'system', label: t('settings.system') },
    { id: 'about', label: t('settings.about') },
  ] as const

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="w-[600px] max-h-[80vh] bg-bg-secondary rounded-2xl border border-border shadow-2xl flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <h2 className="text-base font-semibold text-white">{t('settings.title')}</h2>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-zinc-400 hover:text-white hover:bg-bg-card transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        <div className="flex flex-1 overflow-hidden">
          {/* Sidebar */}
          <div className="w-[160px] border-r border-border py-4 flex flex-col gap-0.5 px-2 flex-shrink-0">
            {SECTIONS.map((s) => (
              <button
                key={s.id}
                onClick={() => setSection(s.id)}
                className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                  section === s.id
                    ? 'bg-accent/20 text-white'
                    : 'text-zinc-400 hover:text-white hover:bg-bg-card'
                }`}
              >
                {s.label}
              </button>
            ))}
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6">
            {section === 'appearance' && (
              <div className="flex flex-col gap-5">
                <div>
                  <label className="text-sm font-medium text-white mb-2 block">
                    {t('settings.theme')}
                  </label>
                  <div className="flex gap-2">
                    {['dark', 'light', 'system'].map((t_) => (
                      <button
                        key={t_}
                        onClick={() => set('theme', t_)}
                        className={`px-4 py-1.5 rounded-lg text-sm capitalize border transition-colors ${
                          settings.theme === t_
                            ? 'bg-accent border-accent text-white'
                            : 'border-border text-zinc-400 hover:text-white hover:border-zinc-500'
                        }`}
                      >
                        {t_}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium text-white mb-2 block">
                    {t('settings.language')}
                  </label>
                  <select
                    value={settings.language}
                    onChange={(e) => set('language', e.target.value)}
                    className="w-full bg-bg-card border border-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-accent"
                  >
                    {Object.entries(LANGUAGES).map(([code, label]) => (
                      <option key={code} value={code}>
                        {label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            )}

            {section === 'downloads' && (
              <div className="flex flex-col gap-5">
                <div>
                  <label className="text-sm font-medium text-white mb-2 block">
                    {t('settings.download_folder')}
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={settings.download_folder}
                      onChange={(e) => set('download_folder', e.target.value)}
                      placeholder={t('settings.download_folder_placeholder')}
                      className="flex-1 bg-bg-card border border-border rounded-lg px-3 py-2 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-accent"
                    />
                    <button
                      type="button"
                      onClick={async () => {
                        const folder = await pickFolder()
                        if (folder) set('download_folder', folder)
                      }}
                      className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-bg-card border border-border text-sm text-zinc-400 hover:text-white transition-colors flex-shrink-0"
                    >
                      <Folder size={14} />
                    </button>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-white">{t('settings.ask_folder')}</p>
                    <p className="text-xs text-zinc-500 mt-0.5">{t('settings.ask_folder_hint')}</p>
                  </div>
                  <Toggle
                    checked={settings.ask_download_folder}
                    onChange={(v) => set('ask_download_folder', v)}
                  />
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-white">{t('settings.auto_load_last')}</p>
                    <p className="text-xs text-zinc-500 mt-0.5">{t('settings.auto_load_last_hint')}</p>
                  </div>
                  <Toggle
                    checked={settings.auto_load_last}
                    onChange={(v) => set('auto_load_last', v)}
                  />
                </div>
              </div>
            )}

            {section === 'system' && (
              <div className="flex flex-col gap-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-white">{t('settings.autostart')}</p>
                    <p className="text-xs text-zinc-500 mt-0.5">{t('settings.autostart_hint')}</p>
                  </div>
                  <Toggle
                    checked={settings.autostart}
                    onChange={(v) => set('autostart', v)}
                  />
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-white">{t('settings.ytdlp_auto_update')}</p>
                    <p className="text-xs text-zinc-500 mt-0.5">{t('settings.ytdlp_hint')}</p>
                  </div>
                  <Toggle
                    checked={settings.ytdlp_auto_update}
                    onChange={(v) => set('ytdlp_auto_update', v)}
                  />
                </div>
                <div>
                  <p className="text-sm text-white mb-2">{t('settings.check_updates')}</p>
                  <button
                    onClick={handleCheckUpdate}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg bg-bg-card hover:bg-bg-elevated border border-border text-sm text-white transition-colors"
                  >
                    <RefreshCw size={14} />
                    {t('settings.check_now')}
                  </button>
                  {updateStatus && (
                    <p className="text-xs text-zinc-400 mt-2">{updateStatus}</p>
                  )}
                </div>
              </div>
            )}

            {section === 'about' && (
              <div className="flex flex-col gap-4">
                <div className="flex items-center gap-4">
                  <span className="text-5xl text-accent">雪</span>
                  <div>
                    <p className="text-lg font-semibold text-white">Yuki — Media Suite</p>
                    <p className="text-sm text-zinc-400">Version 2.0.0</p>
                  </div>
                </div>
                <p className="text-sm text-zinc-400 leading-relaxed">
                  {t('settings.about_description')}
                </p>
                <a
                  href="#"
                  onClick={(e) => e.preventDefault()}
                  className="flex items-center gap-2 text-sm text-accent hover:text-accent-hover transition-colors"
                >
                  <ExternalLink size={14} />
                  GitHub
                </a>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 px-6 py-4 border-t border-border">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-sm text-zinc-400 hover:text-white hover:bg-bg-card transition-colors"
          >
            {t('common.cancel')}
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-5 py-2 rounded-lg text-sm bg-accent hover:bg-accent-hover text-white font-medium transition-colors disabled:opacity-60"
          >
            {saving ? t('common.saving') : t('common.save')}
          </button>
        </div>
      </div>
    </div>
  )
}
