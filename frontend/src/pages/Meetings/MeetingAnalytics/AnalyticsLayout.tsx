import React, { useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { useAnalyticsStore } from '@/stores/meeting/analyticsStore'
import AnalyticsNavigation from './AnalyticsNavigation'
import { Alert, AlertDescription } from '@/components/ui/Alert'
import { Loader2, AlertCircle } from 'lucide-react'

interface AnalyticsLayoutProps {
  children: React.ReactNode
  title?: string
  actions?: React.ReactNode
}

const AnalyticsLayout: React.FC<AnalyticsLayoutProps> = ({
  children,
  title,
  actions
}) => {
  const { id: meetingId } = useParams<{ id: string }>()
  const {
    selectedMeetingId,
    setSelectedMeetingId,
    isLoading,
    error,
    setError,
    fetchAllAnalyticsData
  } = useAnalyticsStore()
  
  useEffect(() => {
    if (meetingId && meetingId !== selectedMeetingId?.toString()) {
      const numericMeetingId = parseInt(meetingId, 10)
      setSelectedMeetingId(numericMeetingId)
      
      // 鑾峰彇鍒嗘瀽鏁版嵁
      fetchAllAnalyticsData(numericMeetingId).catch((err) => {
        console.error('Failed to fetch analytics data:', err)
      })
    }
  }, [meetingId, selectedMeetingId, setSelectedMeetingId, fetchAllAnalyticsData])
  
  // 娓呴櫎閿欒
  const handleClearError = () => {
    setError(null)
  }
  
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-800/50">
      {/* 瀵艰埅鏍?*/}
      <AnalyticsNavigation />
      
      {/* 涓诲唴瀹瑰尯鍩?*/}
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* 椤甸潰澶撮儴 */}
        {(title || actions) && (
          <div className="mb-8">
            <div className="flex items-center justify-between">
              <div>
                {title && (
                  <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">{title}</h1>
                )}
              </div>
              {actions && (
                <div className="flex items-center space-x-4">
                  {actions}
                </div>
              )}
            </div>
          </div>
        )}
        
        {/* 閿欒鎻愮ず */}
        {error && (
          <Alert className="mb-6 border-red-200 bg-red-50">
            <AlertCircle className="h-4 w-4 text-red-600" />
            <AlertDescription className="text-red-800">
              {error}
              <button
                onClick={handleClearError}
                className="ml-2 text-red-600 hover:text-red-800 underline"
              >
                鍏抽棴
              </button>
            </AlertDescription>
          </Alert>
        )}
        
        {/* 鍔犺浇鐘舵€?*/}
        {isLoading && (
          <div className="flex items-center justify-center py-12">
            <div className="flex items-center space-x-3 text-gray-600 dark:text-gray-400">
              <Loader2 className="h-6 w-6 animate-spin" />
              <span>姝ｅ湪鍔犺浇鍒嗘瀽鏁版嵁...</span>
            </div>
          </div>
        )}
        
        {/* 椤甸潰鍐呭 */}
        {!isLoading && (
          <div className="space-y-6">
            {children}
          </div>
        )}
      </div>
    </div>
  )
}

export default AnalyticsLayout
