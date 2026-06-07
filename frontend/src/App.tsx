import React, { useEffect } from 'react'
import { useRoutes } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { useAuthStore } from '@/stores/auth'
import { routes } from '@/routes'

const App: React.FC = () => {
  const checkAuth = useAuthStore((state) => state.checkAuth)
  const routing = useRoutes(routes)

  useEffect(() => {
    checkAuth()
  }, [checkAuth])

  return (
    <div className="min-h-screen bg-background font-sans antialiased">
      {routing}
      <Toaster position="top-right" />
    </div>
  )
}

export default App
