interface DetectResult {
  platform: string
  valid: boolean
  type: string
  title?: string
  uploader?: string
  duration?: number
  thumbnail_url?: string
}

interface PreviewCardProps {
  result: DetectResult
  onAddToQueue: () => void
}

const PLATFORM_COLORS: Record<string, string> = {
  youtube: 'bg-red-500/20 text-red-400 border-red-500/30',
  spotify: 'bg-green-500/20 text-green-400 border-green-500/30',
  soundcloud: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  tiktok: 'bg-pink-500/20 text-pink-400 border-pink-500/30',
  twitter: 'bg-sky-500/20 text-sky-400 border-sky-500/30',
  default: 'bg-zinc-500/20 text-zinc-400 border-zinc-500/30',
}

function formatDuration(sec: number) {
  if (!sec) return ''
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

export default function PreviewCard({ result, onAddToQueue }: PreviewCardProps) {
  const platformColor =
    PLATFORM_COLORS[result.platform?.toLowerCase() || 'default'] ||
    PLATFORM_COLORS.default

  return (
    <div className="flex items-start gap-4 p-4 bg-bg-card rounded-xl border border-border">
      {/* Thumbnail */}
      <div className="w-[160px] h-[120px] rounded-lg overflow-hidden bg-bg-elevated flex-shrink-0">
        {result.thumbnail_url ? (
          <img
            src={result.thumbnail_url}
            alt=""
            className="w-full h-full object-cover"
            onError={(e) => { e.currentTarget.style.display = 'none' }}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-zinc-700 text-3xl">
            雪
          </div>
        )}
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0 flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <span className={`text-xs px-2 py-0.5 rounded border font-medium ${platformColor}`}>
            {result.platform}
          </span>
          <span className="text-xs text-zinc-500 capitalize">{result.type}</span>
        </div>

        <p className="text-base font-semibold text-white leading-snug line-clamp-2">
          {result.title || 'Unknown title'}
        </p>

        <div className="flex items-center gap-3 text-xs text-zinc-400">
          {result.uploader && <span>{result.uploader}</span>}
          {result.duration ? (
            <>
              <span>·</span>
              <span>{formatDuration(result.duration)}</span>
            </>
          ) : null}
        </div>

        <button
          onClick={onAddToQueue}
          className="mt-auto w-fit px-4 py-1.5 rounded-lg bg-accent hover:bg-accent-hover text-white text-sm font-medium transition-colors"
        >
          Add to Queue
        </button>
      </div>
    </div>
  )
}
