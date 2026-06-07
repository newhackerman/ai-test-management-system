import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { 
  MeetingParticipant, 
  ParticipantRole, 
  InvitationStatus, 
  AttendanceStatus 
} from '@/types/meeting'

interface ParticipantState {
  // 参与者状态
  participants: MeetingParticipant[]
  currentParticipant: MeetingParticipant | null
  
  // 加载状态
  loading: boolean
  error: string | null
  
  // 筛选
  filters: {
    role?: ParticipantRole
    invitationStatus?: InvitationStatus
    attendanceStatus?: AttendanceStatus
    searchQuery?: string
  }
  
  // Actions
  setParticipants: (participants: MeetingParticipant[]) => void
  setCurrentParticipant: (participant: MeetingParticipant | null) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  setFilters: (filters: Partial<ParticipantState['filters']>) => void
  
  // 参与者操作
  addParticipant: (participant: MeetingParticipant) => void
  updateParticipant: (id: number, updates: Partial<MeetingParticipant>) => void
  removeParticipant: (id: number) => void
  
  // 批量操作
  updateParticipantRole: (participantIds: number[], role: ParticipantRole) => void
  updateParticipantPermissions: (participantId: number, permissions: {
    can_share_screen?: boolean
    can_use_chat?: boolean
    can_use_whiteboard?: boolean
    can_record?: boolean
  }) => void
  
  // 统计信息
  getParticipantStats: (meetingId: number) => {
    total: number
    byRole: Record<ParticipantRole, number>
    byStatus: Record<AttendanceStatus, number>
    activeCount: number
  }
  
  // 重置状态
  reset: () => void
}

const initialState = {
  participants: [],
  currentParticipant: null,
  loading: false,
  error: null,
  filters: {}
}

export const useParticipantStore = create<ParticipantState>()(
  persist(
    (set, get) => ({
      ...initialState,
      
      // Setters
      setParticipants: (participants) => set({ participants }),
      setCurrentParticipant: (participant) => set({ currentParticipant: participant }),
      setLoading: (loading) => set({ loading }),
      setError: (error) => set({ error }),
      setFilters: (filters) => set((state) => ({ 
        filters: { ...state.filters, ...filters } 
      })),
      
      // 参与者操作
      addParticipant: (participant) => set((state) => ({
        participants: [...state.participants, participant]
      })),
      
      updateParticipant: (id, updates) => set((state) => ({
        participants: state.participants.map(participant => 
          participant.id === id ? { ...participant, ...updates } : participant
        ),
        currentParticipant: state.currentParticipant?.id === id 
          ? { ...state.currentParticipant, ...updates }
          : state.currentParticipant
      })),
      
      removeParticipant: (id) => set((state) => ({
        participants: state.participants.filter(participant => participant.id !== id),
        currentParticipant: state.currentParticipant?.id === id 
          ? null 
          : state.currentParticipant
      })),
      
      // 批量操作
      updateParticipantRole: (participantIds, role) => set((state) => ({
        participants: state.participants.map(participant => 
          participantIds.includes(participant.id) 
            ? { ...participant, participant_role: role }
            : participant
        )
      })),
      
      updateParticipantPermissions: (participantId, permissions) => set((state) => ({
        participants: state.participants.map(participant => 
          participant.id === participantId 
            ? { ...participant, ...permissions }
            : participant
        )
      })),
      
      // 统计信息
      getParticipantStats: (meetingId) => {
        const { participants } = get()
        const meetingParticipants = participants.filter(p => p.meeting_id === meetingId)
        
        const byRole = meetingParticipants.reduce((acc, p) => {
          acc[p.participant_role] = (acc[p.participant_role] || 0) + 1
          return acc
        }, {} as Record<ParticipantRole, number>)
        
        const byStatus = meetingParticipants.reduce((acc, p) => {
          acc[p.attendance_status] = (acc[p.attendance_status] || 0) + 1
          return acc
        }, {} as Record<AttendanceStatus, number>)
        
        const activeCount = meetingParticipants.filter(p => 
          p.attendance_status === 'JOINED'
        ).length
        
        return {
          total: meetingParticipants.length,
          byRole,
          byStatus,
          activeCount
        }
      },
      
      // 重置状态
      reset: () => set(initialState)
    }),
    {
      name: 'participant-store',
      partialize: (state) => ({
        filters: state.filters
      })
    }
  )
)

// 选择器函数
export const useParticipantSelectors = () => {
  const store = useParticipantStore()
  
  return {
    // 获取会议的参与者列表
    getMeetingParticipants: (meetingId: number) => {
      return store.participants.filter(p => p.meeting_id === meetingId)
    },
    
    // 获取筛选后的参与者
    getFilteredParticipants: (meetingId: number) => {
      const { participants, filters } = store
      let filtered = participants.filter(p => p.meeting_id === meetingId)
      
      if (filters.role) {
        filtered = filtered.filter(p => p.participant_role === filters.role)
      }
      
      if (filters.invitationStatus) {
        filtered = filtered.filter(p => p.invitation_status === filters.invitationStatus)
      }
      
      if (filters.attendanceStatus) {
        filtered = filtered.filter(p => p.attendance_status === filters.attendanceStatus)
      }
      
      if (filters.searchQuery) {
        const query = filters.searchQuery.toLowerCase()
        filtered = filtered.filter(p => 
          p.user?.name?.toLowerCase().includes(query) ||
          p.user?.email?.toLowerCase().includes(query)
        )
      }
      
      return filtered
    },
    
    // 获取在线参与者
    getOnlineParticipants: (meetingId: number) => {
      return store.participants.filter(p => 
        p.meeting_id === meetingId && p.attendance_status === 'JOINED'
      )
    },
    
    // 获取主持人和演讲者
    getModerators: (meetingId: number) => {
      return store.participants.filter(p => 
        p.meeting_id === meetingId && 
        ['ORGANIZER', 'MODERATOR', 'PRESENTER'].includes(p.participant_role)
      )
    },
    
    // 检查用户权限
    getUserPermissions: (meetingId: number, userId: number) => {
      const participant = store.participants.find(p => 
        p.meeting_id === meetingId && p.user_id === userId
      )
      
      if (!participant) return null
      
      return {
        canShareScreen: participant.can_share_screen,
        canUseChat: participant.can_use_chat,
        canUseWhiteboard: participant.can_use_whiteboard,
        canRecord: participant.can_record,
        role: participant.participant_role,
        isOrganizer: participant.participant_role === 'ORGANIZER',
        isModerator: ['ORGANIZER', 'MODERATOR'].includes(participant.participant_role)
      }
    }
  }
}