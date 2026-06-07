// @ts-nocheck
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { Meeting, MeetingParticipant, MeetingStatus, MeetingType } from '@/types/meeting'

interface MeetingState {
  // 浼氳鍒楄〃鐘舵€?
  meetings: Meeting[]
  currentMeeting: Meeting | null
  participants: MeetingParticipant[]
  
  // 鍔犺浇鐘舵€?
  loading: boolean
  error: string | null
  
  // 绛涢€夊拰鎼滅储
  filters: {
    status?: MeetingStatus
    type?: MeetingType
    dateRange?: [Date, Date]
    searchQuery?: string
  }
  
  // 鍒嗛〉
  pagination: {
    page: number
    pageSize: number
    total: number
  }
  
  // Actions
  setMeetings: (meetings: Meeting[]) => void
  setCurrentMeeting: (meeting: Meeting | null) => void
  setParticipants: (participants: MeetingParticipant[]) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  setFilters: (filters: Partial<MeetingState['filters']>) => void
  setPagination: (pagination: Partial<MeetingState['pagination']>) => void
  
  // 浼氳鎿嶄綔
  addMeeting: (meeting: Meeting) => void
  updateMeeting: (id: number, updates: Partial<Meeting>) => void
  removeMeeting: (id: number) => void
  
  // 鍙備笌鑰呮搷浣?
  addParticipant: (participant: MeetingParticipant) => void
  updateParticipant: (id: number, updates: Partial<MeetingParticipant>) => void
  removeParticipant: (id: number) => void
  
  // 閲嶇疆鐘舵€?
  reset: () => void
}

const initialState = {
  meetings: [],
  currentMeeting: null,
  participants: [],
  loading: false,
  error: null,
  filters: {},
  pagination: {
    page: 1,
    pageSize: 10,
    total: 0
  }
}

export const useMeetingStore = create<MeetingState>()(
  persist(
    (set, get) => ({
      ...initialState,
      
      // Setters
      setMeetings: (meetings) => set({ meetings }),
      setCurrentMeeting: (meeting) => set({ currentMeeting: meeting }),
      setParticipants: (participants) => set({ participants }),
      setLoading: (loading) => set({ loading }),
      setError: (error) => set({ error }),
      setFilters: (filters) => set((state) => ({ 
        filters: { ...state.filters, ...filters } 
      })),
      setPagination: (pagination) => set((state) => ({ 
        pagination: { ...state.pagination, ...pagination } 
      })),
      
      // 浼氳鎿嶄綔
      addMeeting: (meeting) => set((state) => ({
        meetings: [meeting, ...state.meetings],
        pagination: {
          ...state.pagination,
          total: state.pagination.total + 1
        }
      })),
      
      updateMeeting: (id, updates) => set((state) => ({
        meetings: state.meetings.map(meeting => 
          meeting.id === id ? { ...meeting, ...updates } : meeting
        ),
        currentMeeting: state.currentMeeting?.id === id 
          ? { ...state.currentMeeting, ...updates }
          : state.currentMeeting
      })),
      
      removeMeeting: (id) => set((state) => ({
        meetings: state.meetings.filter(meeting => meeting.id !== id),
        currentMeeting: state.currentMeeting?.id === id ? null : state.currentMeeting,
        pagination: {
          ...state.pagination,
          total: Math.max(0, state.pagination.total - 1)
        }
      })),
      
      // 鍙備笌鑰呮搷浣?
      addParticipant: (participant) => set((state) => ({
        participants: [...state.participants, participant]
      })),
      
      updateParticipant: (id, updates) => set((state) => ({
        participants: state.participants.map(participant => 
          participant.id === id ? { ...participant, ...updates } : participant
        )
      })),
      
      removeParticipant: (id) => set((state) => ({
        participants: state.participants.filter(participant => participant.id !== id)
      })),
      
      // 閲嶇疆鐘舵€?
      reset: () => set(initialState)
    }),
    {
      name: 'meeting-store',
      partialize: (state) => ({
        filters: state.filters,
        pagination: state.pagination
      })
    }
  )
)

// 閫夋嫨鍣ㄥ嚱鏁?
export const useMeetingSelectors = () => {
  const store = useMeetingStore()
  
  return {
    // 鑾峰彇绛涢€夊悗鐨勪細璁垪琛?
    getFilteredMeetings: () => {
      const { meetings, filters } = store
      let filtered = [...meetings]
      
      if (filters.status) {
        filtered = filtered.filter(meeting => meeting.status === filters.status)
      }
      
      if (filters.type) {
        filtered = filtered.filter(meeting => meeting.meeting_type === filters.type)
      }
      
      if (filters.searchQuery) {
        const query = filters.searchQuery.toLowerCase()
        filtered = filtered.filter(meeting => 
          meeting.title.toLowerCase().includes(query) ||
          meeting.description?.toLowerCase().includes(query)
        )
      }
      
      if (filters.dateRange) {
        const [startDate, endDate] = filters.dateRange
        filtered = filtered.filter(meeting => {
          const meetingDate = new Date(meeting.scheduled_start_time)
          return meetingDate >= startDate && meetingDate <= endDate
        })
      }
      
      return filtered
    },
    
    // 鑾峰彇鍒嗛〉鍚庣殑浼氳鍒楄〃
    getPaginatedMeetings: () => {
      const filtered = store.getFilteredMeetings?.() || []
      const { page, pageSize } = store.pagination
      const startIndex = (page - 1) * pageSize
      const endIndex = startIndex + pageSize
      
      return {
        meetings: filtered.slice(startIndex, endIndex),
        total: filtered.length,
        hasMore: endIndex < filtered.length
      }
    },
    
    // 鑾峰彇褰撳墠鐢ㄦ埛鐨勪細璁?
    getUserMeetings: (userId: number) => {
      return store.meetings.filter(meeting => 
        meeting.organizer_id === userId ||
        store.participants.some(p => p.user_id === userId && p.meeting_id === meeting.id)
      )
    },
    
    // 鑾峰彇鍗冲皢寮€濮嬬殑浼氳
    getUpcomingMeetings: () => {
      const now = new Date()
      return store.meetings
        .filter(meeting => 
          meeting.status === 'SCHEDULED' && 
          new Date(meeting.scheduled_start_time) > now
        )
        .sort((a, b) => 
          new Date(a.scheduled_start_time).getTime() - 
          new Date(b.scheduled_start_time).getTime()
        )
    },
    
    // 鑾峰彇杩涜涓殑浼氳
    getActiveMeetings: () => {
      return store.meetings.filter(meeting => meeting.status === 'IN_PROGRESS')
    }
  }
}