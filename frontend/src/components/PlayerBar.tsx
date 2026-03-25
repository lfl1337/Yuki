import { useEffect, useRef, useCallback, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { open as openDialog } from '@tauri-apps/plugin-dialog'
import { useStore } from '../store'
import { playerApi } from '../api/player'
import { getStreamUrl } from '../api/client'
import {
  Play, Pause,
  Volume2, VolumeX, FolderOpen, Shuffle, Repeat
} from 'lucide-react'

function formatTime(sec: number) {
  if (!isFinite(sec) || sec < 0) return '0:00'
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

export default function PlayerBar() {
  const navigate = useNavigate()
  const { playerState, setPlayerState, backendOnline } = useStore()
  const esRef = useRef<EventSource | null>(null)
  const seekingRef = useRef(false)
  const [shuffle, setShuffle] = useState(false)
  const [repeat, setRepeat] = useState(false)

  // SSE connection
  useEffect(() => {
    if (!backendOnline) return

    let reconnectTimer: ReturnType<typeof setTimeout> | null = null

    const connect = () => {
      if (esRef.current) esRef.current.close()
      const es = new EventSource(getStreamUrl('/api/v1/player/stream'))
      es.onmessage = (e) => {
        try {
          const raw = JSON.parse(e.data)
          setPlayerState({
            isPlaying: raw.is_playing,
            isPaused: raw.is_paused,
            position: raw.position,
            duration: raw.duration,
            volume: raw.volume,
            filepath: raw.filepath,
            title: raw.title,
            artist: raw.artist,
            coverArt: raw.cover_art_b64 ?? null,
          })
        } catch {}
      }
      es.onerror = () => {
        es.close()
        reconnectTimer = setTimeout(connect, 2000)
      }
      esRef.current = es
    }

    connect()
    return () => {
      if (reconnectTimer !== null) clearTimeout(reconnectTimer)
      esRef.current?.close()
    }
  }, [backendOnline, setPlayerState])

  const handlePlayPause = useCallback(async () => {
    if (playerState.isPlaying) {
      await playerApi.pause()
    } else {
      await playerApi.play()
    }
  }, [playerState.isPlaying])

  const handleSeek = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    seekingRef.current = false
    await playerApi.seek(parseFloat(e.target.value))
  }, [])

  const handleVolume = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const vol = parseFloat(e.target.value)
    setPlayerState({ volume: vol })
    await playerApi.volume(vol)
  }, [setPlayerState])

  // Repeat: restart track when it ends (triggers on playing→stopped transition)
  useEffect(() => {
    if (!repeat) return
    if (!playerState.isPlaying && !playerState.isPaused) {
      if (playerState.duration > 0 && playerState.position > 0) {
        let id: ReturnType<typeof setTimeout>
        playerApi.seek(0).then(() => {
          id = setTimeout(() => playerApi.play(), 100)
        })
        return () => clearTimeout(id)
      }
    }
  }, [playerState.isPlaying, playerState.isPaused, repeat])

  const handleOpenFolder = useCallback(async () => {
    const selected = await openDialog({
      multiple: false,
      filters: [{ name: 'Audio', extensions: ['mp3', 'flac', 'wav', 'm4a', 'ogg', 'aac', 'opus'] }],
    })
    if (selected && typeof selected === 'string') {
      await playerApi.load(selected)
    }
  }, [])

  const handleCoverClick = useCallback(() => {
    if (playerState.filepath) {
      navigate('/editor', { state: { filepath: playerState.filepath } })
    }
  }, [navigate, playerState.filepath])

  const isActive = playerState.filepath !== ''
  const isPlaying = playerState.isPlaying
  const seekPct = playerState.duration > 0
    ? (playerState.position / playerState.duration) * 100
    : 0
  const volumePct = playerState.volume * 100

  return (
    <div className="h-20 flex-shrink-0 bg-bg-primary border-t border-border grid grid-cols-[200px_1fr_200px] items-center">
      {/* LEFT: Cover + Title + Artist + Open */}
      <div className="flex items-center gap-3 pl-4 min-w-0">
        <div
          className="w-12 h-12 rounded-lg overflow-hidden bg-bg-card flex-shrink-0 cursor-pointer"
          onClick={handleCoverClick}
        >
          {playerState.coverArt ? (
            <img src={playerState.coverArt} alt="cover" className="w-full h-full object-cover" />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-text3">
              <span className="text-lg">雪</span>
            </div>
          )}
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-[13px] font-bold text-text1 truncate leading-tight">
            {isActive ? (playerState.title || 'Unknown') : 'No file loaded'}
          </p>
          <p className="text-[11px] text-text2 truncate leading-tight">
            {isActive ? (playerState.artist || '') : ''}
          </p>
        </div>
        <button
          onClick={handleOpenFolder}
          className="p-1 text-text3 hover:text-text1 transition-colors flex-shrink-0"
          title="Open audio file"
        >
          <FolderOpen size={14} />
        </button>
      </div>

      {/* CENTER: Controls + Seekbar */}
      <div className="flex flex-col items-center justify-center gap-1 px-4">
        {/* Transport controls */}
        <div className="flex items-center gap-4">
          <button
            onClick={() => setShuffle(v => !v)}
            className={`transition-colors ${shuffle ? 'text-accent' : 'text-text3 hover:text-text1'}`}
            title="Shuffle"
          >
            <Shuffle size={16} />
          </button>
          <button
            onClick={handlePlayPause}
            disabled={!isActive}
            className="w-11 h-11 rounded-full bg-text1 flex items-center justify-center hover:scale-105 transition-transform disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:scale-100"
          >
            {isPlaying
              ? <Pause size={20} className="text-bg-primary" />
              : <Play size={20} className="text-bg-primary ml-0.5" />}
          </button>
          <button
            onClick={() => setRepeat(v => !v)}
            className={`transition-colors ${repeat ? 'text-accent' : 'text-text3 hover:text-text1'}`}
            title="Repeat"
          >
            <Repeat size={16} />
          </button>
        </div>

        {/* Seekbar */}
        <div className="flex items-center gap-2 w-full player-slider-container">
          <span className="text-[11px] text-text3 font-mono min-w-[2.5rem] text-right flex-shrink-0">
            {formatTime(playerState.position)}
          </span>
          <input
            type="range"
            min={0}
            max={playerState.duration || 1}
            step={0.5}
            value={playerState.position}
            onChange={handleSeek}
            disabled={!isActive}
            className="player-slider flex-1"
            style={{
              background: `linear-gradient(to right, var(--text-1) ${seekPct}%, var(--bg-elevated) ${seekPct}%)`,
            }}
          />
          <span className="text-[11px] text-text3 font-mono min-w-[2.5rem] flex-shrink-0">
            {formatTime(playerState.duration)}
          </span>
        </div>
      </div>

      {/* RIGHT: Volume */}
      <div className="flex items-center justify-end gap-2 pr-4">
        <button className="text-text2 hover:text-text1 transition-colors flex-shrink-0">
          {playerState.volume === 0 ? (
            <VolumeX size={16} />
          ) : (
            <Volume2 size={16} />
          )}
        </button>
        <div className="player-slider-container">
          <input
            type="range"
            min={0}
            max={1}
            step={0.01}
            value={playerState.volume}
            onChange={handleVolume}
            className="player-slider w-[120px]"
            style={{
              background: `linear-gradient(to right, var(--text-1) ${volumePct}%, var(--bg-elevated) ${volumePct}%)`,
            }}
          />
        </div>
      </div>
    </div>
  )
}
