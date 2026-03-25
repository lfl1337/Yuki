import { useState, useEffect, useCallback, useRef } from 'react'
import { useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { taggerApi } from '../api/tagger'
import { useStore } from '../store'
import { Pencil, RotateCcw, Save, Image, Link, Wand2, FolderOpen, X, CheckCircle, AlertCircle } from 'lucide-react'
import { open as openDialog } from '@tauri-apps/plugin-dialog'

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

interface BatchFile {
  filepath: string
  filename: string
  format: string
  status: 'pending' | 'success' | 'error'
  error?: string
}

type BatchTags = Partial<Omit<Tags, 'cover_art_b64'>>

const emptyTags: Tags = {
  title: '', artist: '', album: '', album_artist: '',
  year: '', genre: '', track_number: '', total_tracks: '',
  disc_number: '', bpm: '', composer: '', comment: '',
  cover_art_b64: '',
}

export default function Editor() {
  const { t } = useTranslation()
  const location = useLocation()
  const { playerState } = useStore()

  // ── Mode toggle ──────────────────────────────────────────────────────
  const [batchMode, setBatchMode] = useState(false)

  // ── Single-file state ─────────────────────────────────────────────────
  const [filepath, setFilepath] = useState<string>('')
  const [tags, setTags] = useState<Tags>(emptyTags)
  const [original, setOriginal] = useState<Tags>(emptyTags)
  const [filename, setFilename] = useState('')
  const [fileInfo, setFileInfo] = useState<{ size: string; format: string; duration: string }>({
    size: '', format: '', duration: '',
  })
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [coverUrlMode, setCoverUrlMode] = useState(false)
  const [coverUrl, setCoverUrl] = useState('')
  const [statusMsg, setStatusMsg] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)
  const mountedRef = useRef(true)
  useEffect(() => {
    mountedRef.current = true
    return () => { mountedRef.current = false }
  }, [])

  // ── Batch state ───────────────────────────────────────────────────────
  const [batchFiles, setBatchFiles] = useState<BatchFile[]>([])
  const [batchTags, setBatchTags] = useState<BatchTags>({})
  const [selectedFiles, setSelectedFiles] = useState<Set<string>>(new Set())
  const [isApplying, setIsApplying] = useState(false)
  const [applyResults, setApplyResults] = useState<{ file: string; ok: boolean; error?: string }[]>([])
  const [batchCoverB64, setBatchCoverB64] = useState<string>('')
  const [batchStatusMsg, setBatchStatusMsg] = useState('')
  const batchCoverFileRef = useRef<HTMLInputElement>(null)

  // ── Single-file logic ─────────────────────────────────────────────────
  const loadFile = useCallback(async (path: string, mounted: { current: boolean }) => {
    setLoading(true)
    setStatusMsg('')
    try {
      const res = await taggerApi.read(path)
      const t_: Tags = {
        title: res.title || '', artist: res.artist || '',
        album: res.album || '', album_artist: res.album_artist || '',
        year: res.year || '', genre: res.genre || '',
        track_number: res.track_number || '', total_tracks: res.total_tracks || '',
        disc_number: res.disc_number || '', bpm: res.bpm || '',
        composer: res.composer || '', comment: res.comment || '',
        cover_art_b64: res.cover_art_b64 || '',
      }
      if (mounted.current) {
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
      }
    } catch {}
    if (mounted.current) setLoading(false)
  }, [])

  const handleOpenFile = async () => {
    const selected = await openDialog({
      multiple: false,
      filters: [{ name: 'Audio', extensions: ['mp3', 'flac', 'wav', 'm4a', 'ogg', 'aac', 'opus'] }],
    })
    if (selected && typeof selected === 'string') loadFile(selected, { current: true })
  }

  useEffect(() => {
    const mounted = { current: true }
    if (location.state?.filepath) loadFile(location.state.filepath, mounted)
    else if (playerState.filepath) loadFile(playerState.filepath, mounted)
    return () => { mounted.current = false }
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
    } catch { setStatusMsg(t('editor.save_error')) }
    setSaving(false)
  }

  const handleReset = () => { setTags(original); setStatusMsg('') }

  const handleAutoName = async () => {
    if (!filepath) return
    const res = await taggerApi.autoName(filepath)
    if (res.suggested_name) setFilename(res.suggested_name)
  }

  const handleRename = async () => {
    if (!filepath || !filename.trim()) return
    const res = await taggerApi.rename(filepath, filename.trim())
    if (res.ok && res.new_filepath) { setFilepath(res.new_filepath); setStatusMsg(t('editor.renamed')) }
    else if (res.error) setStatusMsg(res.error)
  }

  const handleCoverFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => {
      if (!mountedRef.current) return
      if (typeof reader.result === 'string')
        setTags((t_) => ({ ...t_, cover_art_b64: reader.result as string }))
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

  // ── Batch logic ───────────────────────────────────────────────────────
  const hasBatchValue = (key: keyof BatchTags) => {
    const v = batchTags[key]
    return v !== undefined && v !== null && String(v).trim() !== ''
  }

  const batchInputClass = (key: keyof BatchTags) =>
    `w-full bg-bg-elevated rounded-lg px-3 py-2 text-sm text-text1 placeholder-text3 focus:outline-none border transition-colors ${
      hasBatchValue(key) ? 'border-accent' : 'border-border'
    }`

  const setBatch = (key: keyof BatchTags, value: string) =>
    setBatchTags(prev => ({ ...prev, [key]: value }))

  const handleBatchAddFiles = async () => {
    const selected = await openDialog({
      multiple: true,
      filters: [{ name: 'Audio', extensions: ['mp3', 'flac', 'wav', 'm4a', 'ogg', 'aac', 'opus'] }],
    })
    if (!selected) return
    const paths = Array.isArray(selected) ? selected : [selected]
    setBatchFiles(prev => {
      const existing = new Set(prev.map(f => f.filepath))
      const newFiles: BatchFile[] = paths
        .filter(p => !existing.has(p))
        .map(p => ({
          filepath: p,
          filename: p.replace(/\\/g, '/').split('/').pop() || p,
          format: p.split('.').pop()?.toUpperCase() || '',
          status: 'pending',
        }))
      return [...prev, ...newFiles]
    })
  }

  const removeBatchFile = (fp: string) => {
    setBatchFiles(prev => prev.filter(f => f.filepath !== fp))
    setSelectedFiles(prev => { const s = new Set(prev); s.delete(fp); return s })
  }

  const toggleFileSelect = (fp: string) => {
    setSelectedFiles(prev => {
      const s = new Set(prev)
      s.has(fp) ? s.delete(fp) : s.add(fp)
      return s
    })
  }

  const handleBatchCoverFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => {
      if (!mountedRef.current) return
      if (typeof reader.result === 'string') setBatchCoverB64(reader.result)
    }
    reader.readAsDataURL(file)
  }

  const handleApplyBatch = async () => {
    const selected = batchFiles.filter(f => selectedFiles.has(f.filepath))
    if (selected.length === 0) return

    const tagsToApply = Object.fromEntries(
      Object.entries(batchTags).filter(([, v]) =>
        v !== null && v !== undefined && String(v).trim() !== ''
      )
    ) as Record<string, string>

    if (Object.keys(tagsToApply).length === 0 && !batchCoverB64) {
      setBatchStatusMsg('Please fill in at least one tag field')
      return
    }

    setIsApplying(true)
    setApplyResults([])
    setBatchStatusMsg('')

    try {
      const results: { file: string; ok: boolean; error?: string }[] = []

      if (Object.keys(tagsToApply).length > 0) {
        const result = await taggerApi.batchSave(selected.map(f => f.filepath), tagsToApply)
        const successSet = new Set(result.success)
        const failureMap = new Map(result.failed.map(f => [f.file, f.error]))

        setBatchFiles(prev => prev.map(f => ({
          ...f,
          status: successSet.has(f.filepath) ? 'success'
            : failureMap.has(f.filepath) ? 'error'
            : f.status,
          error: failureMap.get(f.filepath),
        })))

        results.push(
          ...result.success.map(file => ({ file, ok: true })),
          ...result.failed.map(f => ({ file: f.file, ok: false, error: f.error })),
        )
      }

      if (batchCoverB64) {
        for (const f of selected) {
          try {
            await taggerApi.write({ filepath: f.filepath, cover_art_b64: batchCoverB64 })
            if (!results.find(r => r.file === f.filepath)) {
              results.push({ file: f.filepath, ok: true })
              setBatchFiles(prev => prev.map(bf =>
                bf.filepath === f.filepath ? { ...bf, status: 'success' } : bf
              ))
            }
          } catch (err) {
            if (!results.find(r => r.file === f.filepath)) {
              results.push({ file: f.filepath, ok: false, error: String(err) })
              setBatchFiles(prev => prev.map(bf =>
                bf.filepath === f.filepath ? { ...bf, status: 'error', error: String(err) } : bf
              ))
            }
          }
        }
      }

      setApplyResults(results)
      const ok = results.filter(r => r.ok).length
      setBatchStatusMsg(`Applied to ${ok} of ${selected.length} file${selected.length !== 1 ? 's' : ''}`)
    } catch {
      setBatchStatusMsg('Batch apply failed')
    } finally {
      setIsApplying(false)
    }
  }

  // ── Shared styles ─────────────────────────────────────────────────────
  const labelClass = 'text-xs text-text2 mb-1 block'
  const inputClass =
    'w-full bg-bg-elevated border border-border rounded-lg px-3 py-2 text-sm text-text1 placeholder-text3 focus:outline-none focus:border-accent'

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Mode toggle */}
      <div className="px-6 pt-4 pb-3 border-b border-border flex gap-2 flex-shrink-0">
        <button
          onClick={() => setBatchMode(false)}
          className={`px-4 py-1.5 rounded-lg text-sm border transition-colors ${
            !batchMode ? 'bg-accent border-accent text-text1' : 'border-border text-text2 hover:text-text1'
          }`}
        >
          Single File
        </button>
        <button
          onClick={() => setBatchMode(true)}
          className={`px-4 py-1.5 rounded-lg text-sm border transition-colors ${
            batchMode ? 'bg-accent border-accent text-text1' : 'border-border text-text2 hover:text-text1'
          }`}
        >
          Batch Edit
        </button>
      </div>

      {/* ── Single File mode ── */}
      {!batchMode && (
        <div className="flex flex-1 overflow-hidden">
          {/* Left panel */}
          <div className="w-[280px] flex-shrink-0 border-r border-border p-5 flex flex-col gap-4 overflow-y-auto">
            <button
              onClick={handleOpenFile}
              className="w-full flex items-center justify-center gap-2 py-2 rounded-xl bg-bg-elevated border border-border text-sm text-text2 hover:text-text1 hover:border-accent transition-colors"
            >
              <FolderOpen size={14} />
              Open File
            </button>
            <div className="flex flex-col items-center gap-3">
              <div className="w-[220px] h-[220px] rounded-2xl overflow-hidden bg-bg-card border border-border flex items-center justify-center">
                {tags.cover_art_b64 ? (
                  <img src={tags.cover_art_b64} alt="cover" className="w-full h-full object-cover" />
                ) : (
                  <span className="text-5xl text-text3">雪</span>
                )}
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-bg-card border border-border text-xs text-text2 hover:text-text1 transition-colors"
                >
                  <Image size={12} />
                  {t('editor.change_cover')}
                </button>
                <button
                  onClick={() => setCoverUrlMode((v) => !v)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-bg-card border border-border text-xs text-text2 hover:text-text1 transition-colors"
                >
                  <Link size={12} />
                  URL
                </button>
              </div>
              <input ref={fileInputRef} type="file" accept="image/*" className="hidden" onChange={handleCoverFile} />
              {coverUrlMode && (
                <div className="flex gap-2 w-full">
                  <input
                    type="text"
                    value={coverUrl}
                    onChange={(e) => setCoverUrl(e.target.value)}
                    placeholder="https://…"
                    className="flex-1 bg-bg-elevated border border-border rounded-lg px-3 py-1.5 text-xs text-text1 placeholder-text3 focus:outline-none focus:border-accent"
                  />
                  <button onClick={handleCoverFromUrl} className="px-3 py-1.5 rounded-lg bg-accent text-text1 text-xs">
                    {t('common.load')}
                  </button>
                </div>
              )}
            </div>

            {filepath && (
              <div className="bg-bg-card rounded-lg border border-border p-3 text-xs text-text2 flex flex-col gap-1">
                <p className="text-text1 font-medium truncate text-xs">
                  {filepath.replace(/\\/g, '/').split('/').pop()}
                </p>
                {fileInfo.format && <p>Format: {fileInfo.format}</p>}
                {fileInfo.duration && <p>Duration: {fileInfo.duration}</p>}
                {fileInfo.size && <p>Size: {fileInfo.size}</p>}
              </div>
            )}

            {!filepath && !loading && (
              <div className="text-center text-text3 text-sm py-8">
                <span className="text-3xl block mb-2">編</span>
                <p>{t('editor.no_file')}</p>
              </div>
            )}
          </div>

          {/* Right panel */}
          <div className="flex-1 overflow-y-auto p-6">
            {loading ? (
              <div className="flex items-center justify-center h-32 text-text3 text-sm">{t('common.loading')}</div>
            ) : !filepath ? (
              <div className="flex flex-col items-center justify-center h-full text-text3">
                <span className="text-5xl mb-3">編</span>
                <p className="text-sm">{t('editor.open_hint')}</p>
              </div>
            ) : (
              <div className="flex flex-col gap-5 max-w-xl">
                <div>
                  <label className={labelClass}>{t('editor.filename')}</label>
                  <div className="flex gap-2">
                    <input type="text" value={filename} onChange={(e) => setFilename(e.target.value)} className={`flex-1 ${inputClass}`} />
                    <span className="text-sm text-text3 self-center">{filepath.match(/\.[^.]+$/)?.[0] || ''}</span>
                    <button onClick={handleAutoName} title={t('editor.auto_name')} className="p-2 rounded-lg bg-bg-card border border-border text-text2 hover:text-text1 transition-colors">
                      <Wand2 size={14} />
                    </button>
                    <button onClick={handleRename} className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-bg-card border border-border text-sm text-text2 hover:text-text1 transition-colors">
                      <Pencil size={13} />
                      {t('editor.rename')}
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-1 gap-3">
                  <div>
                    <label className={labelClass}>{t('editor.title')}</label>
                    <input value={tags.title} onChange={(e) => set('title', e.target.value)} className={inputClass} />
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
                    <textarea value={tags.comment} onChange={(e) => set('comment', e.target.value)} rows={3} className={`${inputClass} resize-none`} />
                  </div>
                </div>

                {statusMsg && <p className="text-sm text-text2">{statusMsg}</p>}

                <div className="flex items-center gap-3">
                  <button onClick={handleSave} disabled={saving} className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-accent hover:bg-accent-hover text-text1 text-sm font-semibold transition-colors disabled:opacity-60">
                    <Save size={14} />
                    {saving ? t('common.saving') : t('editor.save_tags')}
                  </button>
                  <button onClick={handleReset} className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-bg-card border border-border text-sm text-text2 hover:text-text1 transition-colors">
                    <RotateCcw size={14} />
                    {t('editor.reset')}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Batch Edit mode ── */}
      {batchMode && (
        <div className="flex flex-1 overflow-hidden">
          {/* Left: file list */}
          <div className="w-[280px] flex-shrink-0 border-r border-border flex flex-col">
            <div className="px-4 py-3 border-b border-border flex-shrink-0">
              <p className="text-sm font-medium text-text1">
                Selected Files ({batchFiles.length})
              </p>
            </div>

            <div className="flex-1 overflow-y-auto">
              {batchFiles.length === 0 && (
                <div className="text-center text-text3 text-xs py-8 px-4">
                  Click "Add Files" to select audio files
                </div>
              )}
              {batchFiles.map(f => (
                <div
                  key={f.filepath}
                  onClick={() => toggleFileSelect(f.filepath)}
                  className={`flex items-center gap-2 px-3 py-2 border-b border-border/50 cursor-pointer hover:bg-bg-card transition-colors ${
                    f.status === 'success' ? 'bg-green-500/10' : ''
                  } ${f.status === 'error' ? 'bg-red-500/10' : ''}`}
                >
                  <input
                    type="checkbox"
                    checked={selectedFiles.has(f.filepath)}
                    readOnly
                    className="accent-accent flex-shrink-0"
                    onClick={e => e.stopPropagation()}
                    onChange={() => toggleFileSelect(f.filepath)}
                  />
                  <span className="flex-1 text-xs text-text1 truncate min-w-0">{f.filename}</span>
                  <span className="text-[10px] font-mono text-text3 border border-border rounded px-1 flex-shrink-0">
                    {f.format}
                  </span>
                  {f.status === 'success' && <CheckCircle size={11} className="text-green-500 flex-shrink-0" />}
                  {f.status === 'error' && (
                    <span title={f.error}>
                      <AlertCircle size={11} className="text-red-500 flex-shrink-0" />
                    </span>
                  )}
                  <button
                    onClick={e => { e.stopPropagation(); removeBatchFile(f.filepath) }}
                    className="p-0.5 text-text3 hover:text-error flex-shrink-0"
                  >
                    <X size={11} />
                  </button>
                </div>
              ))}
            </div>

            <div className="p-3 flex flex-col gap-2 border-t border-border flex-shrink-0">
              <button
                onClick={handleBatchAddFiles}
                className="w-full py-2 rounded-lg bg-bg-elevated border border-border text-sm text-text2 hover:text-text1 transition-colors"
              >
                + Add Files
              </button>
              <div className="flex gap-2">
                <button
                  onClick={() => setSelectedFiles(new Set(batchFiles.map(f => f.filepath)))}
                  className="flex-1 py-1 text-xs border border-border rounded-lg text-text2 hover:text-text1 transition-colors"
                >
                  Select All
                </button>
                <button
                  onClick={() => setSelectedFiles(new Set())}
                  className="flex-1 py-1 text-xs border border-border rounded-lg text-text2 hover:text-text1 transition-colors"
                >
                  Deselect All
                </button>
              </div>
              <p className="text-[11px] text-text3 text-center">
                {selectedFiles.size} of {batchFiles.length} files selected
              </p>
            </div>
          </div>

          {/* Right: tag fields */}
          <div className="flex-1 overflow-y-auto p-6">
            <div className="flex flex-col gap-1 mb-5">
              <h2 className="text-sm font-bold text-text1">Batch Tag Editor</h2>
              <p className="text-xs text-text3 italic">Only filled fields will be applied to selected files</p>
            </div>

            <div className="flex flex-col gap-3 max-w-xl">
              <div>
                <label className={labelClass}>{t('editor.title')}</label>
                <input value={batchTags.title || ''} onChange={e => setBatch('title', e.target.value)} placeholder="Leave empty to skip" className={batchInputClass('title')} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className={labelClass}>{t('editor.artist')}</label>
                  <input value={batchTags.artist || ''} onChange={e => setBatch('artist', e.target.value)} placeholder="Leave empty to skip" className={batchInputClass('artist')} />
                </div>
                <div>
                  <label className={labelClass}>{t('editor.album_artist')}</label>
                  <input value={batchTags.album_artist || ''} onChange={e => setBatch('album_artist', e.target.value)} placeholder="Leave empty to skip" className={batchInputClass('album_artist')} />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className={labelClass}>{t('editor.album')}</label>
                  <input value={batchTags.album || ''} onChange={e => setBatch('album', e.target.value)} placeholder="Leave empty to skip" className={batchInputClass('album')} />
                </div>
                <div>
                  <label className={labelClass}>{t('editor.year')}</label>
                  <input value={batchTags.year || ''} onChange={e => setBatch('year', e.target.value)} placeholder="Leave empty to skip" className={batchInputClass('year')} />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className={labelClass}>{t('editor.genre')}</label>
                  <input value={batchTags.genre || ''} onChange={e => setBatch('genre', e.target.value)} placeholder="Leave empty to skip" className={batchInputClass('genre')} />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className={labelClass}>{t('editor.track')}</label>
                    <input value={batchTags.track_number || ''} onChange={e => setBatch('track_number', e.target.value)} placeholder="Skip" className={batchInputClass('track_number')} />
                  </div>
                  <div>
                    <label className={labelClass}>{t('editor.disc')}</label>
                    <input value={batchTags.disc_number || ''} onChange={e => setBatch('disc_number', e.target.value)} placeholder="Skip" className={batchInputClass('disc_number')} />
                  </div>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className={labelClass}>{t('editor.bpm')}</label>
                  <input value={batchTags.bpm || ''} onChange={e => setBatch('bpm', e.target.value)} placeholder="Leave empty to skip" className={batchInputClass('bpm')} />
                </div>
                <div>
                  <label className={labelClass}>{t('editor.composer')}</label>
                  <input value={batchTags.composer || ''} onChange={e => setBatch('composer', e.target.value)} placeholder="Leave empty to skip" className={batchInputClass('composer')} />
                </div>
              </div>
              <div>
                <label className={labelClass}>{t('editor.comment')}</label>
                <textarea value={batchTags.comment || ''} onChange={e => setBatch('comment', e.target.value)} placeholder="Leave empty to skip" rows={2} className={`${batchInputClass('comment')} resize-none`} />
              </div>
            </div>

            {/* Cover art */}
            <div className="mt-5 pt-4 border-t border-border">
              <p className="text-xs text-text2 mb-2">Change Cover for all selected files</p>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => batchCoverFileRef.current?.click()}
                  className="px-3 py-1.5 rounded-lg border border-border text-xs text-text2 hover:text-text1 transition-colors"
                >
                  Choose Cover Image
                </button>
                {batchCoverB64 && (
                  <div className="relative">
                    <img src={batchCoverB64} className="w-[60px] h-[60px] rounded-lg object-cover border border-border" />
                    <button
                      onClick={() => setBatchCoverB64('')}
                      className="absolute -top-1.5 -right-1.5 w-4 h-4 rounded-full bg-bg-elevated border border-border flex items-center justify-center text-text3 hover:text-error"
                    >
                      <X size={8} />
                    </button>
                  </div>
                )}
                {!batchCoverB64 && <span className="text-xs text-text3">No cover — will not change</span>}
              </div>
              <input ref={batchCoverFileRef} type="file" accept="image/*" className="hidden" onChange={handleBatchCoverFile} />
            </div>

            {/* Apply */}
            <div className="mt-5 flex flex-col gap-3 max-w-xl">
              <p className="text-sm text-text2">
                Will apply to {selectedFiles.size} selected file{selectedFiles.size !== 1 ? 's' : ''}
              </p>
              {batchStatusMsg && (
                <p className="text-sm text-text2">{batchStatusMsg}</p>
              )}
              <button
                onClick={handleApplyBatch}
                disabled={selectedFiles.size === 0 || isApplying}
                className="w-full h-11 rounded-xl bg-accent hover:bg-accent-hover text-text1 font-semibold text-sm transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {isApplying ? 'Applying…' : `Apply to Selected (${selectedFiles.size})`}
              </button>

              {applyResults.length > 0 && (
                <div className="flex flex-col gap-1 max-h-36 overflow-y-auto">
                  {applyResults.map((r, i) => (
                    <div key={i} className={`flex items-center gap-2 text-xs ${r.ok ? 'text-green-500' : 'text-red-400'}`}>
                      {r.ok ? <CheckCircle size={11} /> : <AlertCircle size={11} />}
                      <span className="truncate">{r.file.replace(/\\/g, '/').split('/').pop()}</span>
                      {!r.ok && <span className="text-red-400/70 truncate">— {r.error}</span>}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
