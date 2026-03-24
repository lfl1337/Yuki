import { useState, useEffect, useRef, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { downloadApi } from '../api/download'
import PreviewCard from '../components/PreviewCard'
import QueueItem from '../components/QueueItem'
import { Clipboard, X, Plus, Download, Folder } from 'lucide-react'
import { pickFolder } from '../utils/dialog'

interface DetectResult {
  platform: string
  valid: boolean
  type: string
  title?: string
  uploader?: string
  duration?: number
  thumbnail_url?: string
}

interface DownloadJob {
  job_id: string
  url: string
  format: string
  quality: string
  status: string
  title: string
  artist: string
  platform: string
  thumbnail_url: string
  progress_pct: number
  speed: number
  eta: number
  filepath: string
  error: string
}

const AUDIO_QUALITIES = ['320kbps', '192kbps', '128kbps']
const VIDEO_QUALITIES = ['best', '1080p', '720p', '480p']
const DEFAULT_FOLDER = ''

export default function Downloader() {
  const { t } = useTranslation()
  const [url, setUrl] = useState('')
  const [detecting, setDetecting] = useState(false)
  const [detected, setDetected] = useState<DetectResult | null>(null)
  const [format, setFormat] = useState<'audio' | 'video'>('audio')
  const [quality, setQuality] = useState('320kbps')
  const [outputDir, setOutputDir] = useState(DEFAULT_FOLDER)
  const [batchMode, setBatchMode] = useState(false)
  const [batchUrls, setBatchUrls] = useState('')
  const [jobs, setJobs] = useState<DownloadJob[]>([])
  const detectTimer = useRef<ReturnType<typeof setTimeout>>()
  const esRef = useRef<EventSource | null>(null)

  // SSE for queue updates
  useEffect(() => {
    const connect = () => {
      if (esRef.current) esRef.current.close()
      const es = new EventSource('/api/v1/download/stream')
      es.onmessage = (e) => {
        try {
          const data: DownloadJob[] = JSON.parse(e.data)
          setJobs((prev) => {
            // Merge: update existing, add new
            const map = new Map(prev.map((j) => [j.job_id, j]))
            for (const job of data) map.set(job.job_id, job)
            return Array.from(map.values())
          })
        } catch {}
      }
      es.onerror = () => {
        es.close()
        setTimeout(connect, 3000)
      }
      esRef.current = es
    }
    connect()
    return () => esRef.current?.close()
  }, [])

  // URL detection with debounce
  useEffect(() => {
    clearTimeout(detectTimer.current)
    if (!url.trim()) {
      setDetected(null)
      return
    }
    setDetecting(true)
    detectTimer.current = setTimeout(async () => {
      try {
        const res = await downloadApi.detect(url.trim())
        setDetected(res.valid ? res : null)
      } catch {
        setDetected(null)
      } finally {
        setDetecting(false)
      }
    }, 500)
    return () => clearTimeout(detectTimer.current)
  }, [url])

  // Sync quality default when switching format
  useEffect(() => {
    setQuality(format === 'audio' ? '320kbps' : 'best')
  }, [format])

  const handlePaste = useCallback(async () => {
    try {
      const text = await navigator.clipboard.readText()
      setUrl(text.trim())
    } catch {}
  }, [])

  const handleDownload = useCallback(async () => {
    if (!url.trim()) return
    await downloadApi.start(url.trim(), format, quality, outputDir)
    setUrl('')
    setDetected(null)
  }, [url, format, quality, outputDir])

  const handleBatchDownload = useCallback(async () => {
    const urls = batchUrls
      .split('\n')
      .map((u) => u.trim())
      .filter(Boolean)
    if (!urls.length) return
    await downloadApi.batch(urls, format, quality, outputDir)
    setBatchUrls('')
    setBatchMode(false)
  }, [batchUrls, format, quality, outputDir])

  const handleAddFromPreview = useCallback(() => {
    handleDownload()
  }, [handleDownload])

  const activeJobs = jobs.filter((j) => !['done', 'error', 'cancelled'].includes(j.status))
  const finishedJobs = jobs.filter((j) => ['done', 'error'].includes(j.status))

  return (
    <div className="flex flex-col gap-4 p-6 max-w-2xl mx-auto">
      {/* URL Input Card */}
      <div className="bg-bg-card rounded-xl border border-border p-4">
        <label className="text-sm font-medium text-white mb-2 block">
          {t('downloader.url_label')}
        </label>
        <div className="flex gap-2">
          <div className="relative flex-1">
            <input
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleDownload()}
              placeholder={t('downloader.url_placeholder')}
              className="w-full bg-bg-elevated border border-border rounded-lg px-3 py-2.5 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-accent pr-8"
            />
            {url && (
              <button
                onClick={() => { setUrl(''); setDetected(null) }}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-white"
              >
                <X size={14} />
              </button>
            )}
          </div>
          <button
            onClick={handlePaste}
            className="flex items-center gap-1.5 px-3 py-2.5 rounded-lg bg-bg-elevated border border-border text-sm text-zinc-400 hover:text-white transition-colors"
          >
            <Clipboard size={14} />
            {t('common.paste')}
          </button>
        </div>
        {detecting && (
          <p className="text-xs text-zinc-500 mt-2">{t('downloader.detecting')}</p>
        )}
        {detected && (
          <div className="mt-1 flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
            <span className="text-xs text-zinc-400 capitalize">
              {detected.platform} · {detected.type}
            </span>
          </div>
        )}
      </div>

      {/* Preview Card */}
      {detected?.valid && (
        <PreviewCard result={detected} onAddToQueue={handleAddFromPreview} />
      )}

      {/* Options */}
      <div className="bg-bg-card rounded-xl border border-border p-4 flex flex-col gap-3">
        {/* Format */}
        <div>
          <label className="text-xs font-medium text-zinc-400 mb-1.5 block uppercase tracking-wide">
            {t('downloader.format')}
          </label>
          <div className="flex gap-2">
            {(['audio', 'video'] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFormat(f)}
                className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium border transition-colors ${
                  format === f
                    ? 'bg-accent/20 border-accent text-white'
                    : 'border-border text-zinc-400 hover:text-white hover:border-zinc-500'
                }`}
              >
                {f === 'audio' ? '🎵' : '🎬'}
                {f === 'audio' ? t('downloader.audio') : t('downloader.video')}
              </button>
            ))}
          </div>
        </div>

        {/* Quality */}
        <div>
          <label className="text-xs font-medium text-zinc-400 mb-1.5 block uppercase tracking-wide">
            {t('downloader.quality')}
          </label>
          <select
            value={quality}
            onChange={(e) => setQuality(e.target.value)}
            className="bg-bg-elevated border border-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-accent"
          >
            {(format === 'audio' ? AUDIO_QUALITIES : VIDEO_QUALITIES).map((q) => (
              <option key={q} value={q}>
                {q}
              </option>
            ))}
          </select>
        </div>

        {/* Folder */}
        <div>
          <label className="text-xs font-medium text-zinc-400 mb-1.5 block uppercase tracking-wide">
            {t('downloader.output_folder')}
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              value={outputDir}
              onChange={(e) => setOutputDir(e.target.value)}
              placeholder={t('downloader.folder_placeholder')}
              className="flex-1 bg-bg-elevated border border-border rounded-lg px-3 py-2 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-accent"
            />
            <button
              type="button"
              onClick={async () => {
                const folder = await pickFolder()
                if (folder) setOutputDir(folder)
              }}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-bg-elevated border border-border text-sm text-zinc-400 hover:text-white transition-colors flex-shrink-0"
            >
              <Folder size={14} />
            </button>
          </div>
        </div>
      </div>

      {/* Download Button */}
      <button
        onClick={handleDownload}
        disabled={!url.trim()}
        className="flex items-center justify-center gap-2 py-3 rounded-xl bg-accent hover:bg-accent-hover text-white font-semibold text-sm transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
      >
        <Download size={16} />
        {t('downloader.download')}
      </button>

      {/* Batch Mode Toggle */}
      <button
        onClick={() => setBatchMode((b) => !b)}
        className="flex items-center gap-2 text-sm text-zinc-400 hover:text-white transition-colors self-start"
      >
        <Plus size={14} className={batchMode ? 'rotate-45' : ''} />
        {t('downloader.batch_toggle')}
      </button>

      {batchMode && (
        <div className="bg-bg-card rounded-xl border border-border p-4 flex flex-col gap-3">
          <label className="text-sm font-medium text-white">
            {t('downloader.batch_label')}
          </label>
          <textarea
            value={batchUrls}
            onChange={(e) => setBatchUrls(e.target.value)}
            placeholder={t('downloader.batch_placeholder')}
            rows={5}
            className="w-full bg-bg-elevated border border-border rounded-lg px-3 py-2 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-accent resize-none"
          />
          <button
            onClick={handleBatchDownload}
            disabled={!batchUrls.trim()}
            className="self-end px-5 py-2 rounded-lg bg-accent hover:bg-accent-hover text-white text-sm font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {t('downloader.download_all')}
          </button>
        </div>
      )}

      {/* Queue */}
      {(activeJobs.length > 0 || finishedJobs.length > 0) && (
        <div className="bg-bg-card rounded-xl border border-border p-4">
          <h3 className="text-sm font-medium text-white mb-3">
            {t('downloader.queue')}
          </h3>
          <div className="flex flex-col gap-2">
            {activeJobs.map((job) => (
              <QueueItem key={job.job_id} job={job} />
            ))}
            {finishedJobs.slice(0, 5).map((job) => (
              <QueueItem key={job.job_id} job={job} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
