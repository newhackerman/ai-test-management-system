// @ts-nocheck
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { 
  MeetingRecording, 
  RecordingType, 
  RecordingStatus, 
  FileFormat,
  RecordingPlaybackInfo,
  RecordingShareInfo
} from '@/types/meeting'

interface RecordingState {
  // 褰曞埗鍒楄〃鐘舵€?
  recordings: MeetingRecording[]
  currentRecording: MeetingRecording | null
  activeRecordings: Map<number, MeetingRecording> // meetingId -> recording
  
  // 鎾斁鍣ㄧ姸鎬?
  playbackInfo: RecordingPlaybackInfo | null
  playbackState: {
    isPlaying: boolean
    currentTime: number
    duration: number
    volume: number
    isMuted: boolean
    playbackRate: number
    isFullscreen: boolean
    quality: string
  }
  
  // 鎾斁杩涘害鍜岀粺璁?
  watchProgress: Map<number, {
    currentTime: number
    watchedPercentage: number
    lastWatchedAt: string
  }>
  
  // 鍒嗕韩鐘舵€?
  shareInfo: Map<number, RecordingShareInfo> // recordingId -> shareInfo
  
  // 鍔犺浇鐘舵€?
  loading: boolean
  error: string | null
  
  // 绛涢€夊拰鎼滅储
  filters: {
    status?: RecordingStatus
    type?: RecordingType
    format?: FileFormat
    dateRange?: [Date, Date]
    searchQuery?: string
    meetingId?: number
  }
  
  // 鍒嗛〉
  pagination: {
    page: number
    pageSize: number
    total: number
  }
  
  // 鎵归噺鎿嶄綔
  selectedRecordings: Set<number>
  
  // Actions - 鍩虹鐘舵€佺鐞?
  setRecordings: (recordings: MeetingRecording[]) => void
  setCurrentRecording: (recording: MeetingRecording | null) => void
  setPlaybackInfo: (info: RecordingPlaybackInfo | null) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  setFilters: (filters: Partial<RecordingState['filters']>) => void
  setPagination: (pagination: Partial<RecordingState['pagination']>) => void
  
  // Actions - 褰曞埗绠＄悊
  addRecording: (recording: MeetingRecording) => void
  updateRecording: (id: number, updates: Partial<MeetingRecording>) => void
  removeRecording: (id: number) => void
  
  // Actions - 娲昏穬褰曞埗绠＄悊
  setActiveRecording: (meetingId: number, recording: MeetingRecording) => void
  removeActiveRecording: (meetingId: number) => void
  updateActiveRecording: (meetingId: number, updates: Partial<MeetingRecording>) => void
  
  // Actions - 鎾斁鍣ㄦ帶鍒?
  updatePlaybackState: (updates: Partial<RecordingState['playbackState']>) => void
  setPlaybackProgress: (recordingId: number, progress: {
    currentTime: number
    watchedPercentage: number
  }) => void
  
  // Actions - 鍒嗕韩绠＄悊
  setShareInfo: (recordingId: number, shareInfo: RecordingShareInfo) => void
  removeShareInfo: (recordingId: number) => void
  
  // Actions - 鎵归噺鎿嶄綔
  toggleRecordingSelection: (recordingId: number) => void
  selectAllRecordings: () => void
  clearSelection: () => void
  
  // Actions - 缁熻鍜屽垎鏋?
  getRecordingStats: () => {
    total: number
    byStatus: Record<RecordingStatus, number>
    byType: Record<RecordingType, number>
    totalSize: number
    totalDuration: number
  }
  
  // 閲嶇疆鐘舵€?
  reset: () => void
}

const initialPlaybackState = {
  isPlaying: false,
  currentTime: 0,
  duration: 0,
  volume: 1,
  isMuted: false,
  playbackRate: 1,
  isFullscreen: false,
  quality: 'auto'
}

const initialState = {
  recordings: [],
  currentRecording: null,
  activeRecordings: new Map(),
  playbackInfo: null,
  playbackState: initialPlaybackState,
  watchProgress: new Map(),
  shareInfo: new Map(),
  loading: false,
  error: null,
  filters: {},
  pagination: {
    page: 1,
    pageSize: 10,
    total: 0
  },
  selectedRecordings: new Set()
}

export const useRecordingStore = create<RecordingState>()(
  persist(
    (set, get) => ({
      ...initialState,
      
      // 鍩虹鐘舵€佺鐞?
      setRecordings: (recordings) => set({ recordings }),
      setCurrentRecording: (recording) => set({ currentRecording: recording }),
      setPlaybackInfo: (info) => set({ playbackInfo: info }),
      setLoading: (loading) => set({ loading }),
      setError: (error) => set({ error }),
      setFilters: (filters) => set((state) => ({ 
        filters: { ...state.filters, ...filters } 
      })),
      setPagination: (pagination) => set((state) => ({ 
        pagination: { ...state.pagination, ...pagination } 
      })),
      
      // 褰曞埗绠＄悊
      addRecording: (recording) => set((state) => ({
        recordings: [recording, ...state.recordings],
        pagination: {
          ...state.pagination,
          total: state.pagination.total + 1
        }
      })),
      
      updateRecording: (id, updates) => set((state) => ({
        recordings: state.recordings.map(recording => 
          recording.id === id ? { ...recording, ...updates } : recording
        ),
        currentRecording: state.currentRecording?.id === id 
          ? { ...state.currentRecording, ...updates }
          : state.currentRecording
      })),
      
      removeRecording: (id) => set((state) => ({
        recordings: state.recordings.filter(recording => recording.id !== id),
        currentRecording: state.currentRecording?.id === id ? null : state.currentRecording,
        pagination: {
          ...state.pagination,
          total: Math.max(0, state.pagination.total - 1)
        },
        selectedRecordings: new Set([...state.selectedRecordings].filter(recordingId => recordingId !== id))
      })),
      
      // 娲昏穬褰曞埗绠＄悊
      setActiveRecording: (meetingId, recording) => set((state) => {
        const newActiveRecordings = new Map(state.activeRecordings)
        newActiveRecordings.set(meetingId, recording)
        return { activeRecordings: newActiveRecordings }
      }),
      
      removeActiveRecording: (meetingId) => set((state) => {
        const newActiveRecordings = new Map(state.activeRecordings)
        newActiveRecordings.delete(meetingId)
        return { activeRecordings: newActiveRecordings }
      }),
      
      updateActiveRecording: (meetingId, updates) => set((state) => {
        const newActiveRecordings = new Map(state.activeRecordings)
        const existing = newActiveRecordings.get(meetingId)
        if (existing) {
          newActiveRecordings.set(meetingId, { ...existing, ...updates })
        }
        return { activeRecordings: newActiveRecordings }
      }),
      
      // 鎾斁鍣ㄦ帶鍒?
      updatePlaybackState: (updates) => set((state) => ({
        playbackState: { ...state.playbackState, ...updates }
      })),
      
      setPlaybackProgress: (recordingId, progress) => set((state) => {
        const newWatchProgress = new Map(state.watchProgress)
        newWatchProgress.set(recordingId, {
          ...progress,
          lastWatchedAt: new Date().toISOString()
        })
        return { watchProgress: newWatchProgress }
      }),
      
      // 鍒嗕韩绠＄悊
      setShareInfo: (recordingId, shareInfo) => set((state) => {
        const newShareInfo = new Map(state.shareInfo)
        newShareInfo.set(recordingId, shareInfo)
        return { shareInfo: newShareInfo }
      }),
      
      removeShareInfo: (recordingId) => set((state) => {
        const newShareInfo = new Map(state.shareInfo)
        newShareInfo.delete(recordingId)
        return { shareInfo: newShareInfo }
      }),
      
      // 鎵归噺鎿嶄綔
      toggleRecordingSelection: (recordingId) => set((state) => {
        const newSelection = new Set(state.selectedRecordings)
        if (newSelection.has(recordingId)) {
          newSelection.delete(recordingId)
        } else {
          newSelection.add(recordingId)
        }
        return { selectedRecordings: newSelection }
      }),
      
      selectAllRecordings: () => set((state) => ({
        selectedRecordings: new Set(state.recordings.map(r => r.id))
      })),
      
      clearSelection: () => set({ selectedRecordings: new Set() }),
      
      // 缁熻鍜屽垎鏋?
      getRecordingStats: () => {
        const { recordings } = get()
        
        const byStatus = recordings.reduce((acc, recording) => {
          acc[recording.recording_status] = (acc[recording.recording_status] || 0) + 1
          return acc
        }, {} as Record<RecordingStatus, number>)
        
        const byType = recordings.reduce((acc, recording) => {
          acc[recording.recording_type] = (acc[recording.recording_type] || 0) + 1
          return acc
        }, {} as Record<RecordingType, number>)
        
        const totalSize = recordings.reduce((sum, recording) => sum + recording.file_size, 0)
        const totalDuration = recordings.reduce((sum, recording) => sum + recording.duration_seconds, 0)
        
        return {
          total: recordings.length,
          byStatus,
          byType,
          totalSize,
          totalDuration
        }
      },
      
      // 閲嶇疆鐘舵€?
      reset: () => set(initialState)
    }),
    {
      name: 'recording-store',
      partialize: (state) => ({
        filters: state.filters,
        pagination: state.pagination,
        watchProgress: Array.from(state.watchProgress.entries()),
        playbackState: {
          volume: state.playbackState.volume,
          playbackRate: state.playbackState.playbackRate,
          quality: state.playbackState.quality
        }
      }),
      onRehydrateStorage: () => (state) => {
        if (state) {
          // 鎭㈠ Map 瀵硅薄
          state.watchProgress = new Map(state.watchProgress as any)
          state.activeRecordings = new Map()
          state.shareInfo = new Map()
          state.selectedRecordings = new Set()
        }
      }
    }
  )
)

// 閫夋嫨鍣ㄥ嚱鏁?
export const useRecordingSelectors = () => {
  const store = useRecordingStore()
  
  return {
    // 鑾峰彇绛涢€夊悗鐨勫綍鍒跺垪琛?
    getFilteredRecordings: () => {
      const { recordings, filters } = store
      let filtered = [...recordings]
      
      if (filters.status) {
        filtered = filtered.filter(recording => recording.recording_status === filters.status)
      }
      
      if (filters.type) {
        filtered = filtered.filter(recording => recording.recording_type === filters.type)
      }
      
      if (filters.format) {
        filtered = filtered.filter(recording => recording.file_format === filters.format)
      }
      
      if (filters.meetingId) {
        filtered = filtered.filter(recording => recording.meeting_id === filters.meetingId)
      }
      
      if (filters.searchQuery) {
        const query = filters.searchQuery.toLowerCase()
        filtered = filtered.filter(recording => 
          recording.recording_name.toLowerCase().includes(query)
        )
      }
      
      if (filters.dateRange) {
        const [startDate, endDate] = filters.dateRange
        filtered = filtered.filter(recording => {
          const recordingDate = new Date(recording.created_at)
          return recordingDate >= startDate && recordingDate <= endDate
        })
      }
      
      return filtered
    },
    
    // 鑾峰彇鍒嗛〉鍚庣殑褰曞埗鍒楄〃
    getPaginatedRecordings: () => {
      const filtered = store.getFilteredRecordings?.() || []
      const { page, pageSize } = store.pagination
      const startIndex = (page - 1) * pageSize
      const endIndex = startIndex + pageSize
      
      return {
        recordings: filtered.slice(startIndex, endIndex),
        total: filtered.length,
        hasMore: endIndex < filtered.length
      }
    },
    
    // 鑾峰彇浼氳鐨勫綍鍒跺垪琛?
    getMeetingRecordings: (meetingId: number) => {
      return store.recordings.filter(recording => recording.meeting_id === meetingId)
    },
    
    // 鑾峰彇娲昏穬褰曞埗
    getActiveRecording: (meetingId: number) => {
      return store.activeRecordings.get(meetingId) || null
    },
    
    // 鑾峰彇褰曞埗鐨勮鐪嬭繘搴?
    getWatchProgress: (recordingId: number) => {
      return store.watchProgress.get(recordingId) || null
    },
    
    // 鑾峰彇褰曞埗鐨勫垎浜俊鎭?
    getShareInfo: (recordingId: number) => {
      return store.shareInfo.get(recordingId) || null
    },
    
    // 鑾峰彇姝ｅ湪褰曞埗鐨勪細璁?
    getRecordingMeetings: () => {
      return Array.from(store.activeRecordings.entries())
        .filter(([_, recording]) => recording.recording_status === 'RECORDING')
        .map(([meetingId, recording]) => ({ meetingId, recording }))
    },
    
    // 鑾峰彇澶勭悊涓殑褰曞埗
    getProcessingRecordings: () => {
      return store.recordings.filter(recording => 
        recording.recording_status === 'PROCESSING'
      )
    },
    
    // 鑾峰彇宸插畬鎴愮殑褰曞埗
    getCompletedRecordings: () => {
      return store.recordings.filter(recording => 
        recording.recording_status === 'COMPLETED'
      )
    },
    
    // 鑾峰彇澶辫触鐨勫綍鍒?
    getFailedRecordings: () => {
      return store.recordings.filter(recording => 
        recording.recording_status === 'FAILED'
      )
    },
    
    // 妫€鏌ユ槸鍚︽湁閫変腑鐨勫綍鍒?
    hasSelectedRecordings: () => {
      return store.selectedRecordings.size > 0
    },
    
    // 鑾峰彇閫変腑鐨勫綍鍒?
    getSelectedRecordings: () => {
      return store.recordings.filter(recording => 
        store.selectedRecordings.has(recording.id)
      )
    },
    
    // 璁＄畻鎬诲瓨鍌ㄤ娇鐢ㄩ噺
    getTotalStorageUsed: () => {
      return store.recordings.reduce((total, recording) => 
        total + recording.file_size, 0
      )
    },
    
    // 鑾峰彇鏈€杩戠殑褰曞埗
    getRecentRecordings: (limit: number = 5) => {
      return [...store.recordings]
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
        .slice(0, limit)
    }
  }
}

// 褰曞埗鐘舵€佸伐鍏峰嚱鏁?
export const recordingUtils = {
  // 鏍煎紡鍖栨枃浠跺ぇ灏?
  formatFileSize: (bytes: number): string => {
    if (bytes === 0) return '0 B'
    
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  },
  
  // 鏍煎紡鍖栧綍鍒舵椂闀?
  formatDuration: (seconds: number): string => {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    const secs = Math.floor(seconds % 60)
    
    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`
  },
  
  // 鑾峰彇褰曞埗鐘舵€佹樉绀烘枃鏈?
  getStatusText: (status: RecordingStatus): string => {
    const statusMap = {
      'RECORDING': '录制中',
      'PROCESSING': '处理中',
      'COMPLETED': '已完成',
      'FAILED': '失败',
      'DELETED': '已删除'
    }
    return statusMap[status] || status
  },
  
  // 鑾峰彇褰曞埗绫诲瀷鏄剧ず鏂囨湰
  getTypeText: (type: RecordingType): string => {
    const typeMap = {
      'FULL_MEETING': '完整会议',
      'SCREEN_SHARE': '屏幕共享',
      'AUDIO_ONLY': '仅音频',
      'HIGHLIGHTS': '精彩片段'
    }
    return typeMap[type] || type
  },
  
  // 妫€鏌ュ綍鍒舵槸鍚﹀彲浠ユ挱鏀?
  canPlay: (recording: MeetingRecording): boolean => {
    return recording.recording_status === 'COMPLETED' && !!recording.file_path
  },
  
  // 妫€鏌ュ綍鍒舵槸鍚﹀彲浠ヤ笅杞?
  canDownload: (recording: MeetingRecording): boolean => {
    return recording.recording_status === 'COMPLETED' && !!recording.file_path
  },
  
  // 妫€鏌ュ綍鍒舵槸鍚﹀彲浠ュ垎浜?
  canShare: (recording: MeetingRecording): boolean => {
    return recording.recording_status === 'COMPLETED'
  },
  
  // 璁＄畻瑙傜湅杩涘害鐧惧垎姣?
  calculateWatchPercentage: (currentTime: number, duration: number): number => {
    if (duration === 0) return 0
    return Math.min(100, Math.max(0, (currentTime / duration) * 100))
  }
}
