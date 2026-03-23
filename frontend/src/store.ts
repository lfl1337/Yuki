import { create } from "zustand";

export interface PlayerState {
  isPlaying: boolean;
  isPaused: boolean;
  position: number;
  duration: number;
  volume: number;
  filepath: string;
  title: string;
  artist: string;
  coverArt: string | null;
}

interface YukiStore {
  backendOnline: boolean;
  activeTab: string;
  playerState: PlayerState;
  settingsOpen: boolean;
  setBackendOnline: (v: boolean) => void;
  setActiveTab: (tab: string) => void;
  setPlayerState: (s: Partial<PlayerState>) => void;
  setSettingsOpen: (v: boolean) => void;
}

const defaultPlayer: PlayerState = {
  isPlaying: false,
  isPaused: false,
  position: 0,
  duration: 0,
  volume: 0.8,
  filepath: "",
  title: "",
  artist: "",
  coverArt: null,
};

export const useStore = create<YukiStore>((set) => ({
  backendOnline: false,
  activeTab: "/",
  playerState: defaultPlayer,
  settingsOpen: false,

  setBackendOnline: (v) => set({ backendOnline: v }),
  setActiveTab: (tab) => set({ activeTab: tab }),
  setPlayerState: (s) =>
    set((state) => ({ playerState: { ...state.playerState, ...s } })),
  setSettingsOpen: (v) => set({ settingsOpen: v }),
}));
