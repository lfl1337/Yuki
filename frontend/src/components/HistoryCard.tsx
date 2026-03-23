import { useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { historyApi } from '../api/history'
import { playerApi } from '../api/player'
import { useStore } from '../store'
import { openFolder } from '../utils/shell'
import { Play, Pencil, FolderOpen, Trash2 } from 'lucide-react'

interface HistoryEntry {
  id: string
  title: string
  artist: string
  platform: string
  format: string
  quality: string
  filepath: string
  thumbnail_url: string
  duration: number
  filesize: number
  url: string
  downloaded_at: string
}

interface HistoryCardProps {
  entry: HistoryEntry
  onDeleted: (id: string) => void
}

const PLATFORM_COLORS: Record<string, string> = {
  youtube: 'bg-red-500/20 text-red-400',
  spotify: 'bg-green-500/20 text-green-400',
  soundcloud: 'bg-orange-500/20 text-orange-400',
  tiktok: 'bg-pink-500/20 text-pink-400',
  twitter: 'bg-sky-500/20 text-sky-400',
  default: 'bg-zinc-500/20 text-zinc-400',
}

function formatDuration(sec: number) {
  if (!sec) return ''
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

function formatDate(iso: string) {
  try {
    return new Date(iso).toLocaleDateString()
  } catch {
    return iso
  }
}

function formatSize(bytes: number) {
  if (!bytes) return ''
  if (bytes > 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  return `${(bytes / 1024).toFixed(0)} KB`
}

export default function HistoryCard({ entry, onDeleted }: HistoryCardProps) {
  const navigate = useNavigate()
  const { setPlayerState } = useStore()

  const platformColor =
    PLATFORM_COLORS[entry.platform?.toLowerCase() || 'default'] ||
    PLATFORM_COLORS.default

  const handlePlay = useCallback(async () => {
    if (!entry.filepath) return
    await playerApi.load(entry.filepath)
    await playerApi.play()
    setPlayerState({ filepath: entry.filepath, title: entry.title, artist: entry.artist })
  }, [entry, setPlayerState])

  const handleOpenFolder = useCallback(() => {
    openFolder(entry.filepath)
  }, [entry.filepath])

  const handleEdit = useCallback(() => {
    navigate('/editor', { state: { filepath: entry.filepath } })
  }, [navigate, entry.filepath])

  const handleDelete = useCallback(async () => {
    await historyApi.delete(entry.id)
    onDeleted(entry.id)
  }, [entry.id, onDeleted])

  return (
    <div className="bg-bg-card rounded-xl border border-border overflow-hidden flex flex-col hover:border-zinc-500 transition-colors">
      {/* Thumbnail */}
      <div className="relative h-[120px] bg-bg-elevated flex-shrink-0">
        {entry.thumbnail_url ? (
          <img
            src={entry.thumbnail_url}
            alt=""
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-zinc-700 text-3xl">
            雪
          </div>
        )}
        {entry.duration > 0 && (
          <span className="absolute bottom-1.5 right-2 text-xs bg-black/70 text-white px-1.5 py-0.5 rounded">
            {formatDuration(entry.duration)}
          </span>
        )}
      </div>

      {/* Content */}
      <div className="p-3 flex flex-col gap-2 flex-1">
        {/* Badges */}
        <div className="flex items-center gap-1.5 flex-wrap">
          {entry.platform && (
            <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${platformColor}`}>
              {entry.platform}
            </span>
          )}
          <span className="text-xs px-1.5 py-0.5 rounded bg-accent/20 text-accent font-medium">
            {entry.format?.toUpperCase() || 'AUDIO'}
          </span>
          {entry.quality && (
            <span className="text-xs px-1.5 py-0.5 rounded bg-zinc-700/60 text-zinc-400">
              {entry.quality}
            </span>
          )}
        </div>

        <div>
          <p className="text-sm font-medium text-white leading-snug line-clamp-2">
            {entry.title || 'Unknown'}
          </p>
          {entry.artist && (
            <p className="text-xs text-zinc-400 mt-0.5 truncate">{entry.artist}</p>
          )}
        </div>

        <div className="flex items-center justify-between mt-auto">
          <div className="text-xs text-zinc-600">
            {formatDate(entry.downloaded_at)}
            {entry.filesize ? ` · ${formatSize(entry.filesize)}` : ''}
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-1 pt-1 border-t border-border/50">
          <button
            onClick={handlePlay}
            disabled={!entry.filepath}
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs rounded-lg bg-accent/20 text-accent hover:bg-accent hover:text-white transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          >
            <Play size={11} />
            Play
          </button>
          <button
            onClick={handleOpenFolder}
            disabled={!entry.filepath}
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs rounded-lg text-zinc-400 hover:text-white hover:bg-bg-elevated transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          >
            <FolderOpen size={11} />
          </button>
          <button
            onClick={handleEdit}
            disabled={!entry.filepath}
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs rounded-lg text-zinc-400 hover:text-white hover:bg-bg-elevated transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          >
            <Pencil size={11} />
            Edit
          </button>
          <button
            onClick={handleDelete}
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs rounded-lg text-zinc-500 hover:text-red-400 hover:bg-red-500/10 transition-colors ml-auto"
          >
            <Trash2 size={11} />
          </button>
        </div>
      </div>
    </div>
  )
}
