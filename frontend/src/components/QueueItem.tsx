import { useCallback } from 'react'
import { downloadApi } from '../api/download'
import { openFolder } from '../utils/shell'
import { X, CheckCircle, FolderOpen, AlertCircle } from 'lucide-react'

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

interface QueueItemProps {
  job: DownloadJob
}

const PLATFORM_COLORS: Record<string, string> = {
  youtube: 'bg-red-500/20 text-red-400',
  spotify: 'bg-green-500/20 text-green-400',
  soundcloud: 'bg-orange-500/20 text-orange-400',
  tiktok: 'bg-pink-500/20 text-pink-400',
  twitter: 'bg-sky-500/20 text-sky-400',
  default: 'bg-zinc-500/20 text-zinc-400',
}

function formatSpeed(bytesPerSec: number) {
  if (!bytesPerSec) return ''
  if (bytesPerSec > 1024 * 1024) return `${(bytesPerSec / 1024 / 1024).toFixed(1)} MB/s`
  return `${(bytesPerSec / 1024).toFixed(0)} KB/s`
}

function formatEta(seconds: number) {
  if (!seconds) return ''
  if (seconds < 60) return `${seconds}s`
  return `${Math.floor(seconds / 60)}m ${seconds % 60}s`
}

export default function QueueItem({ job }: QueueItemProps) {
  const handleCancel = useCallback(async () => {
    await downloadApi.cancel(job.job_id)
  }, [job.job_id])

  const handleOpenFolder = useCallback(() => {
    openFolder(job.filepath)
  }, [job.filepath])

  const platformColor =
    PLATFORM_COLORS[job.platform?.toLowerCase() || 'default'] ||
    PLATFORM_COLORS.default

  const isDone = job.status === 'done'
  const isError = job.status === 'error'
  const isCancelled = job.status === 'cancelled'
  const isActive = !isDone && !isError && !isCancelled

  return (
    <div className="flex items-center gap-3 p-3 bg-bg-card rounded-lg border border-border">
      {/* Thumbnail */}
      <div className="w-[80px] h-[60px] rounded-md overflow-hidden bg-bg-elevated flex-shrink-0">
        {job.thumbnail_url ? (
          <img
            src={job.thumbnail_url}
            alt=""
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-zinc-600 text-xl">
            雪
          </div>
        )}
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${platformColor}`}>
            {job.platform || 'URL'}
          </span>
          <span className="text-xs px-1.5 py-0.5 rounded bg-accent/20 text-accent font-medium">
            {job.format?.toUpperCase() || 'MP3'}
          </span>
        </div>
        <p className="text-sm text-white truncate font-medium">
          {job.title || job.url || 'Fetching…'}
        </p>

        {/* Progress */}
        {isActive && (
          <div className="mt-1.5">
            <div className="flex items-center justify-between mb-0.5">
              <span className="text-xs text-zinc-500 capitalize">{job.status}</span>
              <span className="text-xs text-zinc-500">
                {formatSpeed(job.speed)}
                {job.eta ? ` · ${formatEta(job.eta)}` : ''}
              </span>
            </div>
            <div className="h-1 bg-bg-elevated rounded-full overflow-hidden">
              <div
                className="h-full bg-accent rounded-full transition-all duration-300"
                style={{ width: `${job.progress_pct || 0}%` }}
              />
            </div>
          </div>
        )}

        {isDone && (
          <div className="mt-1 flex items-center gap-2">
            <CheckCircle size={12} className="text-green-500" />
            <span className="text-xs text-green-400">Complete</span>
            {job.filepath && (
              <button
                onClick={handleOpenFolder}
                className="text-xs text-zinc-400 hover:text-white flex items-center gap-1 ml-2"
              >
                <FolderOpen size={11} />
                Open folder
              </button>
            )}
          </div>
        )}

        {isError && (
          <div className="mt-1 flex items-center gap-2">
            <AlertCircle size={12} className="text-red-500" />
            <span className="text-xs text-red-400 truncate">{job.error || 'Download failed'}</span>
          </div>
        )}

        {isCancelled && (
          <span className="text-xs text-zinc-500 mt-1">Cancelled</span>
        )}
      </div>

      {/* Cancel */}
      {isActive && (
        <button
          onClick={handleCancel}
          className="p-1.5 rounded text-zinc-500 hover:text-white hover:bg-bg-elevated transition-colors flex-shrink-0"
          title="Cancel"
        >
          <X size={14} />
        </button>
      )}
    </div>
  )
}
