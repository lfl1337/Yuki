import { useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useStore } from '../store'
import { playerApi } from '../api/player'
import {
  Play, Pause, SkipBack, SkipForward,
  Volume2, VolumeX, FolderOpen
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

  // SSE connection — maps snake_case backend keys to camelCase store keys
  useEffect(() => {
    if (!backendOnline) return

    const connect = () => {
      if (esRef.current) esRef.current.close()
      const es = new EventSource('/api/v1/player/stream')
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
        setTimeout(connect, 3000)
      }
      esRef.current = es
    }

    connect()
    return () => esRef.current?.close()
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

  const handleOpenFolder = useCallback(() => {
    if (playerState.filepath) {
      // Trigger OS file explorer via backend or just navigate to editor
    }
  }, [playerState.filepath])

  const handleCoverClick = useCallback(() => {
    if (playerState.filepath) {
      navigate('/editor', { state: { filepath: playerState.filepath } })
    }
  }, [navigate, playerState.filepath])

  const isActive = playerState.filepath !== ''
  const isPlaying = playerState.isPlaying

  return (
    <div className="h-[72px] flex-shrink-0 bg-bg-secondary border-t border-border flex items-center px-4 gap-4">
      {/* Cover + Open */}
      <div className="flex items-center gap-2 flex-shrink-0">
        <button
          onClick={handleOpenFolder}
          className="p-1.5 rounded text-zinc-500 hover:text-white hover:bg-bg-card transition-colors"
          title="Open folder"
        >
          <FolderOpen size={14} />
        </button>
        <div
          className="w-12 h-12 rounded-lg overflow-hidden bg-bg-card cursor-pointer flex-shrink-0"
          onClick={handleCoverClick}
        >
          {playerState.coverArt ? (
            <img
              src={playerState.coverArt}
              alt="cover"
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-zinc-600">
              <span className="text-lg">雪</span>
            </div>
          )}
        </div>
      </div>

      {/* Title/Artist */}
      <div className="w-[190px] flex-shrink-0 min-w-0">
        <p className="text-sm font-medium text-white truncate">
          {isActive ? playerState.title || 'Unknown' : '—'}
        </p>
        <p className="text-xs text-zinc-400 truncate">
          {isActive ? playerState.artist || '' : ''}
        </p>
      </div>

      {/* Transport */}
      <div className="flex items-center gap-3 flex-shrink-0">
        <button
          disabled={!isActive}
          className="p-1.5 rounded text-zinc-400 hover:text-white transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
        >
          <SkipBack size={16} />
        </button>
        <button
          onClick={handlePlayPause}
          disabled={!isActive}
          className="w-10 h-10 rounded-full bg-white flex items-center justify-center hover:scale-105 transition-transform disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:scale-100"
        >
          {isPlaying
            ? <Pause size={18} className="text-black" />
            : <Play size={18} className="text-black ml-0.5" />}
        </button>
        <button
          disabled={!isActive}
          className="p-1.5 rounded text-zinc-400 hover:text-white transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
        >
          <SkipForward size={16} />
        </button>
      </div>

      {/* Seekbar */}
      <div className="flex-1 flex items-center gap-2 min-w-0">
        <span className="text-xs text-zinc-500 w-8 text-right flex-shrink-0">
          {formatTime(playerState.position)}
        </span>
        <input
          type="range"
          min={0}
          max={playerState.duration || 1}
          step={0.5}
          value={seekingRef.current ? undefined : playerState.position}
          onChange={handleSeek}
          disabled={!isActive}
          className="flex-1 h-1.5 accent-purple-500 cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed"
        />
        <span className="text-xs text-zinc-500 w-8 flex-shrink-0">
          {formatTime(playerState.duration)}
        </span>
      </div>

      {/* Volume */}
      <div className="flex items-center gap-2 flex-shrink-0">
        {playerState.volume === 0 ? (
          <VolumeX size={16} className="text-zinc-400" />
        ) : (
          <Volume2 size={16} className="text-zinc-400" />
        )}
        <input
          type="range"
          min={0}
          max={1}
          step={0.01}
          value={playerState.volume}
          onChange={handleVolume}
          className="w-20 h-1.5 accent-purple-500 cursor-pointer"
        />
      </div>
    </div>
  )
}
