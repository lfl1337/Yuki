import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { historyApi } from '../api/history'
import HistoryCard from '../components/HistoryCard'
import { Search, Download, Trash2, ChevronLeft, ChevronRight } from 'lucide-react'

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

interface HistoryPage {
  items: HistoryEntry[]
  total: number
  pages: number
  page: number
}

const PLATFORMS = ['all', 'youtube', 'spotify', 'soundcloud', 'tiktok', 'twitter']
const FORMATS = ['all', 'audio', 'video']
const PER_PAGE = 20

export default function History() {
  const { t } = useTranslation()
  const [data, setData] = useState<HistoryPage>({ items: [], total: 0, pages: 1, page: 1 })
  const [search, setSearch] = useState('')
  const [platform, setPlatform] = useState('all')
  const [format, setFormat] = useState('all')
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [confirmClear, setConfirmClear] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await historyApi.get({
        search,
        platform: platform === 'all' ? undefined : platform,
        format: format === 'all' ? undefined : format,
        page,
        per_page: PER_PAGE,
      })
      setData({ ...res, page })
    } catch {}
    setLoading(false)
  }, [search, platform, format, page])

  useEffect(() => {
    const timer = setTimeout(load, search ? 300 : 0)
    return () => clearTimeout(timer)
  }, [load, search])

  // Reset page on filter change
  useEffect(() => {
    setPage(1)
  }, [search, platform, format])

  const handleDeleted = useCallback((id: string) => {
    setData((prev) => ({
      ...prev,
      items: prev.items.filter((e) => e.id !== id),
      total: prev.total - 1,
    }))
  }, [])

  const handleClearAll = useCallback(async () => {
    if (!confirmClear) {
      setConfirmClear(true)
      return
    }
    await historyApi.clearAll()
    setData({ items: [], total: 0, pages: 1, page: 1 })
    setConfirmClear(false)
  }, [confirmClear])

  const handleExport = useCallback(() => {
    const url = historyApi.exportCsvUrl()
    const a = document.createElement('a')
    a.href = url
    a.download = 'yuki-history.csv'
    a.click()
  }, [])

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex flex-col gap-3 p-5 border-b border-border">
        {/* Search */}
        <div className="relative">
          <Search
            size={14}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500"
          />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={t('history.search_placeholder')}
            className="w-full bg-bg-card border border-border rounded-lg pl-9 pr-4 py-2 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-accent"
          />
        </div>

        {/* Filters + Actions */}
        <div className="flex items-center gap-3 flex-wrap">
          {/* Platform pills */}
          <div className="flex gap-1.5 flex-wrap">
            {PLATFORMS.map((p) => (
              <button
                key={p}
                onClick={() => setPlatform(p)}
                className={`px-2.5 py-1 rounded-full text-xs font-medium capitalize transition-colors ${
                  platform === p
                    ? 'bg-accent text-white'
                    : 'bg-bg-card border border-border text-zinc-400 hover:text-white'
                }`}
              >
                {p === 'all' ? t('history.all') : p}
              </button>
            ))}
          </div>

          {/* Format pills */}
          <div className="flex gap-1.5">
            {FORMATS.map((f) => (
              <button
                key={f}
                onClick={() => setFormat(f)}
                className={`px-2.5 py-1 rounded-full text-xs font-medium capitalize transition-colors ${
                  format === f
                    ? 'bg-accent text-white'
                    : 'bg-bg-card border border-border text-zinc-400 hover:text-white'
                }`}
              >
                {f === 'all' ? t('history.all_formats') : f}
              </button>
            ))}
          </div>

          <div className="ml-auto flex items-center gap-2">
            <button
              onClick={handleExport}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-bg-card border border-border text-xs text-zinc-400 hover:text-white transition-colors"
            >
              <Download size={12} />
              {t('history.export_csv')}
            </button>
            <button
              onClick={handleClearAll}
              onBlur={() => setConfirmClear(false)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs transition-colors ${
                confirmClear
                  ? 'bg-red-500/20 border border-red-500/50 text-red-400'
                  : 'bg-bg-card border border-border text-zinc-400 hover:text-red-400'
              }`}
            >
              <Trash2 size={12} />
              {confirmClear ? t('history.confirm_clear') : t('history.clear_all')}
            </button>
          </div>
        </div>

        {/* Count */}
        <p className="text-xs text-zinc-500">
          {t('history.total_count', { count: data.total })}
        </p>
      </div>

      {/* Grid */}
      <div className="flex-1 overflow-y-auto p-5">
        {loading ? (
          <div className="flex items-center justify-center h-32 text-zinc-500 text-sm">
            {t('common.loading')}
          </div>
        ) : data.items.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-zinc-600">
            <span className="text-4xl mb-3">歴</span>
            <p className="text-sm">{t('history.empty')}</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-4 xl:grid-cols-3">
            {data.items.map((entry) => (
              <HistoryCard key={entry.id} entry={entry} onDeleted={handleDeleted} />
            ))}
          </div>
        )}
      </div>

      {/* Pagination */}
      {data.pages > 1 && (
        <div className="flex items-center justify-center gap-3 py-4 border-t border-border">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="p-1.5 rounded-lg text-zinc-400 hover:text-white hover:bg-bg-card transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          >
            <ChevronLeft size={16} />
          </button>
          <span className="text-sm text-zinc-400">
            {t('history.page', { current: page, total: data.pages })}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(data.pages, p + 1))}
            disabled={page === data.pages}
            className="p-1.5 rounded-lg text-zinc-400 hover:text-white hover:bg-bg-card transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          >
            <ChevronRight size={16} />
          </button>
        </div>
      )}
    </div>
  )
}
