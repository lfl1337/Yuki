import { useState, useEffect, useCallback, useRef } from 'react'
import { useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { taggerApi } from '../api/tagger'
import { useStore } from '../store'
import { Pencil, RotateCcw, Save, Image, Link, Wand2 } from 'lucide-react'

interface Tags {
  title: string
  artist: string
  album: string
  album_artist: string
  year: string
  genre: string
  track_number: string
  total_tracks: string
  disc_number: string
  bpm: string
  composer: string
  comment: string
  cover_art_b64: string
}

const emptyTags: Tags = {
  title: '',
  artist: '',
  album: '',
  album_artist: '',
  year: '',
  genre: '',
  track_number: '',
  total_tracks: '',
  disc_number: '',
  bpm: '',
  composer: '',
  comment: '',
  cover_art_b64: '',
}

export default function Editor() {
  const { t } = useTranslation()
  const location = useLocation()
  const { playerState } = useStore()
  const [filepath, setFilepath] = useState<string>('')
  const [tags, setTags] = useState<Tags>(emptyTags)
  const [original, setOriginal] = useState<Tags>(emptyTags)
  const [filename, setFilename] = useState('')
  const [fileInfo, setFileInfo] = useState<{ size: string; format: string; duration: string }>({
    size: '',
    format: '',
    duration: '',
  })
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [coverUrlMode, setCoverUrlMode] = useState(false)
  const [coverUrl, setCoverUrl] = useState('')
  const [statusMsg, setStatusMsg] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  const loadFile = useCallback(async (path: string) => {
    setLoading(true)
    setStatusMsg('')
    try {
      const res = await taggerApi.read(path)
      const t_: Tags = {
        title: res.title || '',
        artist: res.artist || '',
        album: res.album || '',
        album_artist: res.album_artist || '',
        year: res.year || '',
        genre: res.genre || '',
        track_number: res.track_number || '',
        total_tracks: res.total_tracks || '',
        disc_number: res.disc_number || '',
        bpm: res.bpm || '',
        composer: res.composer || '',
        comment: res.comment || '',
        cover_art_b64: res.cover_art_b64 || '',
      }
      setTags(t_)
      setOriginal(t_)
      setFilepath(path)
      const parts = path.replace(/\\/g, '/').split('/')
      const fname = parts[parts.length - 1]
      setFilename(fname.replace(/\.[^.]+$/, ''))
      setFileInfo({
        size: res.filesize ? `${(res.filesize / 1024 / 1024).toFixed(1)} MB` : '',
        format: res.format || '',
        duration: res.duration
          ? `${Math.floor(res.duration / 60)}:${(res.duration % 60).toString().padStart(2, '0')}`
          : '',
      })
    } catch {}
    setLoading(false)
  }, [])

  // Load from navigation state (History → Editor)
  useEffect(() => {
    if (location.state?.filepath) {
      loadFile(location.state.filepath)
    } else if (playerState.filepath) {
      loadFile(playerState.filepath)
    }
  }, [location.state, loadFile])

  const set = (key: keyof Tags, value: string) =>
    setTags((t_) => ({ ...t_, [key]: value }))

  const handleSave = async () => {
    if (!filepath) return
    setSaving(true)
    setStatusMsg('')
    try {
      await taggerApi.write({ filepath, ...tags })
      setOriginal(tags)
      setStatusMsg(t('editor.saved'))
    } catch (e: unknown) {
      setStatusMsg(t('editor.save_error'))
    }
    setSaving(false)
  }

  const handleReset = () => {
    setTags(original)
    setStatusMsg('')
  }

  const handleAutoName = async () => {
    if (!filepath) return
    const res = await taggerApi.autoName(filepath)
    if (res.suggested_name) setFilename(res.suggested_name)
  }

  const handleRename = async () => {
    if (!filepath || !filename.trim()) return
    const res = await taggerApi.rename(filepath, filename.trim())
    if (res.ok && res.new_filepath) {
      setFilepath(res.new_filepath)
      setStatusMsg(t('editor.renamed'))
    } else if (res.error) {
      setStatusMsg(res.error)
    }
  }

  const handleCoverFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => {
      if (typeof reader.result === 'string') {
        setTags((t_) => ({ ...t_, cover_art_b64: reader.result as string }))
      }
    }
    reader.readAsDataURL(file)
  }

  const handleCoverFromUrl = async () => {
    if (!coverUrl.trim()) return
    try {
      const res = await taggerApi.coverFromUrl(coverUrl.trim())
      if (res.cover_art_b64) setTags((t_) => ({ ...t_, cover_art_b64: res.cover_art_b64 }))
      setCoverUrl('')
      setCoverUrlMode(false)
    } catch {}
  }

  const labelClass = 'text-xs text-zinc-400 mb-1 block'
  const inputClass =
    'w-full bg-bg-elevated border border-border rounded-lg px-3 py-2 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-accent'

  return (
    <div className="flex h-full overflow-hidden">
      {/* Left panel */}
      <div className="w-[280px] flex-shrink-0 border-r border-border p-5 flex flex-col gap-4 overflow-y-auto">
        {/* Cover art */}
        <div className="flex flex-col items-center gap-3">
          <div className="w-[220px] h-[220px] rounded-2xl overflow-hidden bg-bg-card border border-border flex items-center justify-center">
            {tags.cover_art_b64 ? (
              <img
                src={tags.cover_art_b64}
                alt="cover"
                className="w-full h-full object-cover"
              />
            ) : (
              <span className="text-5xl text-zinc-700">雪</span>
            )}
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => fileInputRef.current?.click()}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-bg-card border border-border text-xs text-zinc-400 hover:text-white transition-colors"
            >
              <Image size={12} />
              {t('editor.change_cover')}
            </button>
            <button
              onClick={() => setCoverUrlMode((v) => !v)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-bg-card border border-border text-xs text-zinc-400 hover:text-white transition-colors"
            >
              <Link size={12} />
              URL
            </button>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={handleCoverFile}
          />
          {coverUrlMode && (
            <div className="flex gap-2 w-full">
              <input
                type="text"
                value={coverUrl}
                onChange={(e) => setCoverUrl(e.target.value)}
                placeholder="https://…"
                className="flex-1 bg-bg-elevated border border-border rounded-lg px-3 py-1.5 text-xs text-white placeholder-zinc-600 focus:outline-none focus:border-accent"
              />
              <button
                onClick={handleCoverFromUrl}
                className="px-3 py-1.5 rounded-lg bg-accent text-white text-xs"
              >
                {t('common.load')}
              </button>
            </div>
          )}
        </div>

        {/* File info */}
        {filepath && (
          <div className="bg-bg-card rounded-lg border border-border p-3 text-xs text-zinc-400 flex flex-col gap-1">
            <p className="text-white font-medium truncate text-xs">
              {filepath.replace(/\\/g, '/').split('/').pop()}
            </p>
            {fileInfo.format && <p>Format: {fileInfo.format}</p>}
            {fileInfo.duration && <p>Duration: {fileInfo.duration}</p>}
            {fileInfo.size && <p>Size: {fileInfo.size}</p>}
          </div>
        )}

        {!filepath && !loading && (
          <div className="text-center text-zinc-600 text-sm py-8">
            <span className="text-3xl block mb-2">編</span>
            <p>{t('editor.no_file')}</p>
          </div>
        )}
      </div>

      {/* Right panel */}
      <div className="flex-1 overflow-y-auto p-6">
        {loading ? (
          <div className="flex items-center justify-center h-32 text-zinc-500 text-sm">
            {t('common.loading')}
          </div>
        ) : !filepath ? (
          <div className="flex flex-col items-center justify-center h-full text-zinc-600">
            <span className="text-5xl mb-3">編</span>
            <p className="text-sm">{t('editor.open_hint')}</p>
          </div>
        ) : (
          <div className="flex flex-col gap-5 max-w-xl">
            {/* Filename row */}
            <div>
              <label className={labelClass}>{t('editor.filename')}</label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={filename}
                  onChange={(e) => setFilename(e.target.value)}
                  className={`flex-1 ${inputClass}`}
                />
                <span className="text-sm text-zinc-500 self-center">
                  {filepath.match(/\.[^.]+$/)?.[0] || ''}
                </span>
                <button
                  onClick={handleAutoName}
                  title={t('editor.auto_name')}
                  className="p-2 rounded-lg bg-bg-card border border-border text-zinc-400 hover:text-white transition-colors"
                >
                  <Wand2 size={14} />
                </button>
                <button
                  onClick={handleRename}
                  className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-bg-card border border-border text-sm text-zinc-400 hover:text-white transition-colors"
                >
                  <Pencil size={13} />
                  {t('editor.rename')}
                </button>
              </div>
            </div>

            {/* Tag fields */}
            <div className="grid grid-cols-1 gap-3">
              <div>
                <label className={labelClass}>{t('editor.title')}</label>
                <input
                  value={tags.title}
                  onChange={(e) => set('title', e.target.value)}
                  className={inputClass}
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className={labelClass}>{t('editor.artist')}</label>
                  <input value={tags.artist} onChange={(e) => set('artist', e.target.value)} className={inputClass} />
                </div>
                <div>
                  <label className={labelClass}>{t('editor.album_artist')}</label>
                  <input value={tags.album_artist} onChange={(e) => set('album_artist', e.target.value)} className={inputClass} />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className={labelClass}>{t('editor.album')}</label>
                  <input value={tags.album} onChange={(e) => set('album', e.target.value)} className={inputClass} />
                </div>
                <div>
                  <label className={labelClass}>{t('editor.year')}</label>
                  <input value={tags.year} onChange={(e) => set('year', e.target.value)} className={inputClass} />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className={labelClass}>{t('editor.genre')}</label>
                  <input value={tags.genre} onChange={(e) => set('genre', e.target.value)} className={inputClass} />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className={labelClass}>{t('editor.track')}</label>
                    <input value={tags.track_number} onChange={(e) => set('track_number', e.target.value)} className={inputClass} placeholder="1" />
                  </div>
                  <div>
                    <label className={labelClass}>{t('editor.total')}</label>
                    <input value={tags.total_tracks} onChange={(e) => set('total_tracks', e.target.value)} className={inputClass} placeholder="12" />
                  </div>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className={labelClass}>{t('editor.bpm')}</label>
                  <input value={tags.bpm} onChange={(e) => set('bpm', e.target.value)} className={inputClass} />
                </div>
                <div>
                  <label className={labelClass}>{t('editor.disc')}</label>
                  <input value={tags.disc_number} onChange={(e) => set('disc_number', e.target.value)} className={inputClass} />
                </div>
              </div>
              <div>
                <label className={labelClass}>{t('editor.composer')}</label>
                <input value={tags.composer} onChange={(e) => set('composer', e.target.value)} className={inputClass} />
              </div>
              <div>
                <label className={labelClass}>{t('editor.comment')}</label>
                <textarea
                  value={tags.comment}
                  onChange={(e) => set('comment', e.target.value)}
                  rows={3}
                  className={`${inputClass} resize-none`}
                />
              </div>
            </div>

            {/* Status */}
            {statusMsg && (
              <p className="text-sm text-zinc-400">{statusMsg}</p>
            )}

            {/* Actions */}
            <div className="flex items-center gap-3">
              <button
                onClick={handleSave}
                disabled={saving}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-accent hover:bg-accent-hover text-white text-sm font-semibold transition-colors disabled:opacity-60"
              >
                <Save size={14} />
                {saving ? t('common.saving') : t('editor.save_tags')}
              </button>
              <button
                onClick={handleReset}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-bg-card border border-border text-sm text-zinc-400 hover:text-white transition-colors"
              >
                <RotateCcw size={14} />
                {t('editor.reset')}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
