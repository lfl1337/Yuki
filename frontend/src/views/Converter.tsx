import { useState, useEffect, useRef, useCallback, DragEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { converterApi } from '../api/converter'
import { X, Upload, CheckCircle, AlertCircle, Folder } from 'lucide-react'
import { pickFolder } from '../utils/dialog'
import { loadSettings, patchSettings } from '../api/settings'

interface FileEntry {
  path: string
  name: string
}

interface ConversionJob {
  job_id: string
  input_path: string
  output_format: string
  status: string
  progress_pct: number
  error: string
  output_path: string
}

const AUDIO_FORMATS = ['mp3', 'wav', 'flac', 'ogg', 'aac', 'opus', 'm4a']
const VIDEO_FORMATS = ['mp4', 'mkv', 'avi', 'mov', 'webm']
const AUDIO_QUALITIES = ['128k', '192k', '256k', '320k']
const VIDEO_RESOLUTIONS = ['480p', '720p', '1080p', 'original']
const VIDEO_CODECS = ['H.264', 'H.265', 'VP9']
const FILENAME_MODES = ['keep', 'suffix', 'custom']

export default function Converter() {
  const { t } = useTranslation()
  const [files, setFiles] = useState<FileEntry[]>([])
  const [dragging, setDragging] = useState(false)
  const [outputFormat, setOutputFormat] = useState('mp3')
  const [audioQuality, setAudioQuality] = useState('192k')
  const [videoResolution, setVideoResolution] = useState('720p')
  const [videoCodec, setVideoCodec] = useState('H.264')
  const [outputDir, setOutputDir] = useState('')
  const [filenameMode, setFilenameMode] = useState('keep')
  const [createSubfolder, setCreateSubfolder] = useState(false)
  const [jobs, setJobs] = useState<Map<string, ConversionJob>>(new Map())
  const fileInputRef = useRef<HTMLInputElement>(null)
  const esRef = useRef<EventSource | null>(null)

  const isVideoFormat = VIDEO_FORMATS.includes(outputFormat)

  // Load persisted output folder on mount (converter dir, fallback to download dir)
  useEffect(() => {
    loadSettings().then((s) => {
      const converter = s['default_converter_dir']
      const download = s['default_download_dir']
      const saved = (typeof converter === 'string' && converter)
        ? converter
        : (typeof download === 'string' ? download : '')
      if (saved) setOutputDir(saved)
    })
  }, [])

  // SSE for conversion progress
  useEffect(() => {
    const connect = () => {
      if (esRef.current) esRef.current.close()
      const es = new EventSource('/api/v1/converter/stream')
      es.onmessage = (e) => {
        try {
          const data: ConversionJob[] = JSON.parse(e.data)
          setJobs((prev) => {
            const next = new Map(prev)
            for (const job of data) next.set(job.job_id, job)
            return next
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

  const addFiles = useCallback((paths: string[]) => {
    setFiles((prev) => {
      const existing = new Set(prev.map((f) => f.path))
      const newFiles = paths
        .filter((p) => !existing.has(p))
        .map((p) => ({
          path: p,
          name: p.replace(/\\/g, '/').split('/').pop() || p,
        }))
      return [...prev, ...newFiles]
    })
  }, [])

  const handleDrop = useCallback(
    (e: DragEvent<HTMLDivElement>) => {
      e.preventDefault()
      setDragging(false)
      const paths: string[] = []
      for (const item of Array.from(e.dataTransfer.items)) {
        const file = item.getAsFile()
        if (file) paths.push((file as File & { path?: string }).path || file.name)
      }
      if (paths.length) addFiles(paths)
    },
    [addFiles]
  )

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const fileList = e.target.files
      if (!fileList) return
      const paths: string[] = Array.from(fileList).map(
        (f) => (f as File & { path?: string }).path || f.name
      )
      addFiles(paths)
      e.target.value = ''
    },
    [addFiles]
  )

  const removeFile = useCallback((path: string) => {
    setFiles((prev) => prev.filter((f) => f.path !== path))
  }, [])

  const handleConvert = useCallback(async () => {
    if (!files.length) return
    const qualitySettings: Record<string, string> = isVideoFormat
      ? {
          video_resolution: videoResolution,
          video_codec: videoCodec.toLowerCase().replace('.', '').replace('-', ''),
        }
      : { audio_bitrate: audioQuality }

    await converterApi.start(
      files.map((f) => f.path),
      outputFormat,
      qualitySettings,
      outputDir,
      { filename_mode: filenameMode, create_subfolder: createSubfolder }
    )
  }, [files, outputFormat, audioQuality, videoResolution, videoCodec, outputDir, filenameMode, createSubfolder, isVideoFormat])

  const handleCancel = useCallback(async (jobId: string) => {
    await converterApi.cancel(jobId)
  }, [])

  const activeJobs = Array.from(jobs.values()).filter(
    (j) => !['done', 'error', 'cancelled'].includes(j.status)
  )
  const finishedJobs = Array.from(jobs.values()).filter((j) =>
    ['done', 'error'].includes(j.status)
  )

  return (
    <div className="flex flex-col gap-4 p-6 max-w-2xl mx-auto">
      {/* Drop Zone */}
      <div
        onDrop={handleDrop}
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
          dragging
            ? 'border-accent bg-accent/10'
            : 'border-border hover:border-zinc-500 hover:bg-bg-card'
        }`}
      >
        <Upload size={28} className="mx-auto mb-3 text-zinc-500" />
        <p className="text-sm text-white font-medium">{t('converter.drop_zone')}</p>
        <p className="text-xs text-zinc-500 mt-1">{t('converter.drop_hint')}</p>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept="audio/*,video/*"
          className="hidden"
          onChange={handleFileInput}
        />
      </div>

      {/* File List */}
      {files.length > 0 && (
        <div className="bg-bg-card rounded-xl border border-border overflow-hidden">
          {files.map((file) => (
            <div
              key={file.path}
              className="flex items-center gap-3 px-4 py-2.5 border-b border-border/50 last:border-b-0"
            >
              <span className="flex-1 text-sm text-white truncate">{file.name}</span>
              <button
                onClick={() => removeFile(file.path)}
                className="p-1 rounded text-zinc-500 hover:text-white hover:bg-bg-elevated transition-colors"
              >
                <X size={13} />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Settings */}
      <div className="bg-bg-card rounded-xl border border-border p-4 flex flex-col gap-4">
        {/* Format */}
        <div>
          <label className="text-xs text-zinc-400 uppercase tracking-wide mb-2 block">
            {t('converter.output_format')}
          </label>
          <div className="flex flex-col gap-2">
            <div className="flex gap-1.5 flex-wrap">
              {AUDIO_FORMATS.map((f) => (
                <button
                  key={f}
                  onClick={() => setOutputFormat(f)}
                  className={`px-2.5 py-1 rounded-md text-xs font-mono uppercase border transition-colors ${
                    outputFormat === f
                      ? 'bg-accent border-accent text-white'
                      : 'border-border text-zinc-400 hover:text-white hover:border-zinc-500'
                  }`}
                >
                  {f}
                </button>
              ))}
            </div>
            <div className="flex gap-1.5 flex-wrap">
              {VIDEO_FORMATS.map((f) => (
                <button
                  key={f}
                  onClick={() => setOutputFormat(f)}
                  className={`px-2.5 py-1 rounded-md text-xs font-mono uppercase border transition-colors ${
                    outputFormat === f
                      ? 'bg-accent border-accent text-white'
                      : 'border-border text-zinc-400 hover:text-white hover:border-zinc-500'
                  }`}
                >
                  {f}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Quality */}
        {!isVideoFormat ? (
          <div>
            <label className="text-xs text-zinc-400 uppercase tracking-wide mb-2 block">
              {t('converter.audio_quality')}
            </label>
            <div className="flex gap-2">
              {AUDIO_QUALITIES.map((q) => (
                <button
                  key={q}
                  onClick={() => setAudioQuality(q)}
                  className={`px-3 py-1 rounded-lg text-xs border transition-colors ${
                    audioQuality === q
                      ? 'bg-accent border-accent text-white'
                      : 'border-border text-zinc-400 hover:text-white'
                  }`}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="flex gap-4">
            <div>
              <label className="text-xs text-zinc-400 uppercase tracking-wide mb-2 block">
                {t('converter.resolution')}
              </label>
              <div className="flex gap-2">
                {VIDEO_RESOLUTIONS.map((r) => (
                  <button
                    key={r}
                    onClick={() => setVideoResolution(r)}
                    className={`px-3 py-1 rounded-lg text-xs border transition-colors ${
                      videoResolution === r
                        ? 'bg-accent border-accent text-white'
                        : 'border-border text-zinc-400 hover:text-white'
                    }`}
                  >
                    {r}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="text-xs text-zinc-400 uppercase tracking-wide mb-2 block">
                {t('converter.codec')}
              </label>
              <div className="flex gap-2">
                {VIDEO_CODECS.map((c) => (
                  <button
                    key={c}
                    onClick={() => setVideoCodec(c)}
                    className={`px-3 py-1 rounded-lg text-xs border transition-colors ${
                      videoCodec === c
                        ? 'bg-accent border-accent text-white'
                        : 'border-border text-zinc-400 hover:text-white'
                    }`}
                  >
                    {c}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Output folder */}
        <div>
          <label className="text-xs text-zinc-400 uppercase tracking-wide mb-2 block">
            {t('converter.output_folder')}
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              value={outputDir}
              onChange={(e) => setOutputDir(e.target.value)}
              placeholder={t('converter.folder_placeholder')}
              className="flex-1 bg-bg-elevated border border-border rounded-lg px-3 py-2 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-accent"
            />
            <button
              type="button"
              onClick={async () => {
                const folder = await pickFolder()
                if (folder) {
                  setOutputDir(folder)
                  patchSettings({ default_converter_dir: folder })
                }
              }}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-bg-elevated border border-border text-sm text-zinc-400 hover:text-white transition-colors flex-shrink-0"
            >
              <Folder size={14} />
            </button>
          </div>
        </div>

        {/* Filename mode */}
        <div>
          <label className="text-xs text-zinc-400 uppercase tracking-wide mb-2 block">
            {t('converter.filename_mode')}
          </label>
          <div className="flex gap-2">
            {FILENAME_MODES.map((m) => (
              <button
                key={m}
                onClick={() => setFilenameMode(m)}
                className={`px-3 py-1 rounded-lg text-xs border capitalize transition-colors ${
                  filenameMode === m
                    ? 'bg-accent border-accent text-white'
                    : 'border-border text-zinc-400 hover:text-white'
                }`}
              >
                {t(`converter.filename_${m}`)}
              </button>
            ))}
          </div>
        </div>

        {/* Subfolder toggle */}
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={createSubfolder}
            onChange={(e) => setCreateSubfolder(e.target.checked)}
            className="rounded border-border bg-bg-elevated accent-purple-500"
          />
          <span className="text-sm text-zinc-300">{t('converter.create_subfolder')}</span>
        </label>
      </div>

      {/* Convert Button */}
      <button
        onClick={handleConvert}
        disabled={files.length === 0}
        className="flex items-center justify-center gap-2 py-3 rounded-xl bg-accent hover:bg-accent-hover text-white font-semibold text-sm transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
      >
        <Upload size={16} />
        {t('converter.convert_all')} ({files.length})
      </button>

      {/* Progress */}
      {(activeJobs.length > 0 || finishedJobs.length > 0) && (
        <div className="bg-bg-card rounded-xl border border-border p-4">
          <h3 className="text-sm font-medium text-white mb-3">{t('converter.progress')}</h3>
          <div className="flex flex-col gap-2">
            {[...activeJobs, ...finishedJobs.slice(0, 5)].map((job) => (
              <div key={job.job_id} className="flex items-center gap-3">
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-white truncate">
                    {job.input_path.replace(/\\/g, '/').split('/').pop()}
                    <span className="text-zinc-500 ml-1">→ .{job.output_format}</span>
                  </p>
                  {job.status !== 'done' && job.status !== 'error' && (
                    <div className="h-1 bg-bg-elevated rounded-full mt-1.5 overflow-hidden">
                      <div
                        className="h-full bg-accent rounded-full transition-all"
                        style={{ width: `${job.progress_pct || 0}%` }}
                      />
                    </div>
                  )}
                  {job.status === 'error' && (
                    <div className="flex items-center gap-1.5 mt-1">
                      <AlertCircle size={11} className="text-red-500" />
                      <span className="text-xs text-red-400">{job.error || 'Failed'}</span>
                    </div>
                  )}
                  {job.status === 'done' && (
                    <div className="flex items-center gap-1.5 mt-1">
                      <CheckCircle size={11} className="text-green-500" />
                      <span className="text-xs text-green-400">Done</span>
                    </div>
                  )}
                </div>
                {!['done', 'error', 'cancelled'].includes(job.status) && (
                  <button
                    onClick={() => handleCancel(job.job_id)}
                    className="p-1 rounded text-zinc-500 hover:text-white hover:bg-bg-elevated transition-colors flex-shrink-0"
                  >
                    <X size={13} />
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
