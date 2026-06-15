import React from 'react'
import { Link, Navigate, RouteObject } from 'react-router-dom'
import { AuthGuard } from '@/components/auth/AuthGuard'
import { apiClient } from '@/services/api/client'

const LoadingFallback = () => (
  <div className="flex min-h-screen items-center justify-center">
    <div className="h-8 w-8 animate-spin rounded-full border-b-2 border-blue-600" />
  </div>
)

const withSuspense = (Component: React.LazyExoticComponent<React.ComponentType<any>>) => (
  <React.Suspense fallback={<LoadingFallback />}>
    <Component />
  </React.Suspense>
)

const ModuleGuard = ({ module, children }: { module: string; children: React.ReactNode }) => {
  const [allowed, setAllowed] = React.useState<boolean | null>(null)

  React.useEffect(() => {
    let cancelled = false

    apiClient
      .get('/dashboard/access')
      .then((response) => {
        if (cancelled) return
        const payload = response.data?.data || response.data
        setAllowed(Boolean(payload?.modules?.[module]))
      })
      .catch(() => {
        if (!cancelled) setAllowed(false)
      })

    return () => {
      cancelled = true
    }
  }, [module])

  if (allowed === null) return <LoadingFallback />

  if (!allowed) {
    return (
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-6 text-amber-800">
        <h1 className="text-lg font-semibold">无权访问</h1>
        <p className="mt-2 text-sm">当前账号没有访问该模块的权限，请联系管理员分配角色或权限。</p>
        <Link to="/" className="mt-4 inline-flex text-sm font-medium text-amber-900 underline">
          返回仪表盘
        </Link>
      </div>
    )
  }

  return <>{children}</>
}

const withModule = (module: string, Component: React.LazyExoticComponent<React.ComponentType<any>>) => (
  <ModuleGuard module={module}>{withSuspense(Component)}</ModuleGuard>
)

const NotFound = () => (
  <div className="flex min-h-screen items-center justify-center text-gray-500">页面未找到</div>
)

const Layout = React.lazy(() => import('@/components/layout'))
const Login = React.lazy(() => import('@/pages/Login'))
const ForgotPassword = React.lazy(() => import('@/pages/auth/ForgotPassword'))
const ResetPassword = React.lazy(() => import('@/pages/auth/ResetPassword'))
const Dashboard = React.lazy(() => import('@/pages/Dashboard'))
const Users = React.lazy(() => import('@/pages/Users'))
const Roles = React.lazy(() => import('@/pages/Roles'))
const Settings = React.lazy(() => import('@/pages/Settings'))
const Statistics = React.lazy(() => import('@/pages/Statistics'))
const Profile = React.lazy(() => import('@/pages/Profile'))
const ConfigManagement = React.lazy(() => import('@/pages/ConfigManagement'))
const ConfigGroupManagement = React.lazy(() => import('@/pages/ConfigGroupManagement'))
const AuditManagement = React.lazy(() => import('@/pages/AuditManagement'))
const EightRoleManagement = React.lazy(() => import('@/pages/EightRoleManagement'))
const AIAssistant = React.lazy(() => import('@/pages/AIAssistant'))
const Projects = React.lazy(() => import('@/pages/Projects'))
const TaskManagement = React.lazy(() => import('@/pages/TaskManagement'))
const RequirementsManagement = React.lazy(() => import('@/pages/RequirementsManagement'))
const RiskManagement = React.lazy(() => import('@/pages/RiskManagement'))

const MeetingList = React.lazy(() => import('@/pages/Meetings/MeetingList'))
const CreateMeeting = React.lazy(() => import('@/pages/Meetings/CreateMeeting'))
const EditMeeting = React.lazy(() => import('@/pages/Meetings/EditMeeting'))
const MeetingDetail = React.lazy(() => import('@/pages/Meetings/MeetingDetail'))
const MeetingRoom = React.lazy(() => import('@/pages/Meetings/MeetingRoom'))
const AnalyticsDashboard = React.lazy(() => import('@/pages/Meetings/MeetingAnalytics/AnalyticsDashboard'))
const ParticipationAnalysis = React.lazy(() => import('@/pages/Meetings/MeetingAnalytics/ParticipationAnalysis'))
const MeetingSummary = React.lazy(() => import('@/pages/Meetings/MeetingAnalytics/MeetingSummary'))
const MeetingMinutes = React.lazy(() => import('@/pages/Meetings/MeetingAnalytics/MeetingMinutes'))
const ActionItems = React.lazy(() => import('@/pages/Meetings/MeetingAnalytics/ActionItems'))
const ReportGenerator = React.lazy(() => import('@/pages/Meetings/MeetingAnalytics/ReportGenerator'))
const MeetingComparison = React.lazy(() => import('@/pages/Meetings/MeetingAnalytics/MeetingComparison'))
const RecordingList = React.lazy(() => import('@/pages/Meetings/MeetingRecords/RecordingList'))
const RecordingDetail = React.lazy(() => import('@/pages/Meetings/MeetingRecords/RecordingDetail'))
const RecordingPlayer = React.lazy(() => import('@/pages/Meetings/MeetingRecords/RecordingPlayer'))

const TestManager = React.lazy(() => import('@/pages/TestManager'))
const TestPlanList = React.lazy(() => import('@/pages/TestManager/TestPlan/TestPlanList'))
const TestPlanCreate = React.lazy(() => import('@/pages/TestManager/TestPlan/TestPlanCreate'))
const TestPlanDetail = React.lazy(() => import('@/pages/TestManager/TestPlan/TestPlanDetail'))
const TestPlanEdit = React.lazy(() => import('@/pages/TestManager/TestPlan/TestPlanEdit'))
const TestCaseList = React.lazy(() => import('@/pages/TestManager/TestCase/TestCaseList'))
const TestCaseCreate = React.lazy(() => import('@/pages/TestManager/TestCase/TestCaseCreate'))
const TestCaseEdit = React.lazy(() => import('@/pages/TestManager/TestCase/TestCaseEdit'))
const TestCaseDetail = React.lazy(() => import('@/pages/TestManager/TestCase/TestCaseDetail'))
const ExecutionDashboard = React.lazy(() => import('@/pages/TestManager/Execution/ExecutionDashboard'))
const ExecutionDetail = React.lazy(() => import('@/pages/TestManager/Execution/ExecutionDetail'))
const ManualExecution = React.lazy(() => import('@/pages/TestManager/Execution/ManualExecution'))
const AutomationExecution = React.lazy(() => import('@/pages/TestManager/Execution/AutomationExecution'))
const DefectList = React.lazy(() => import('@/pages/TestManager/Defect/DefectList'))
const DefectAnalytics = React.lazy(() => import('@/pages/TestManager/Defect/DefectAnalytics'))
const ReportDashboard = React.lazy(() => import('@/pages/TestManager/Report/ReportDashboard'))
const ReportGenerate = React.lazy(() => import('@/pages/TestManager/Report/ReportGenerate'))
const PerformanceTest = React.lazy(() => import('@/pages/TestManager/SpecialTest/PerformanceTest'))
const SecurityTest = React.lazy(() => import('@/pages/TestManager/SpecialTest/SecurityTest'))

const AllureReports = React.lazy(() => import('@/pages/AllureReports'))
const Reports = React.lazy(() => import('@/pages/Reports'))
const AutoRecovery = React.lazy(() => import('@/pages/AutoRecovery'))

export const routes: RouteObject[] = [
  {
    path: '/login',
    element: withSuspense(Login),
  },
  {
    path: '/auth/login',
    element: <Navigate to="/login" replace />,
  },
  {
    path: '/auth/forgot-password',
    element: withSuspense(ForgotPassword),
  },
  {
    path: '/auth/reset-password',
    element: withSuspense(ResetPassword),
  },
  {
    path: '/',
    element: (
      <AuthGuard>
        <React.Suspense fallback={<LoadingFallback />}>
          <Layout />
        </React.Suspense>
      </AuthGuard>
    ),
    children: [
      { index: true, element: withSuspense(Dashboard) },
      { path: 'users', element: withModule('users', Users) },
      { path: 'roles', element: withModule('roles', Roles) },
      { path: 'settings', element: withModule('settings', Settings) },
      { path: 'statistics', element: withModule('reports', Statistics) },
      { path: 'profile', element: withSuspense(Profile) },
      { path: 'config', element: withModule('settings', ConfigManagement) },
      { path: 'config/groups', element: withModule('settings', ConfigGroupManagement) },
      { path: 'config/audits', element: withModule('settings', AuditManagement) },
      { path: 'roles/eight', element: withModule('roles', EightRoleManagement) },
      { path: 'ai-assistant', element: withSuspense(AIAssistant) },
      { path: 'projects', element: withModule('projects', Projects) },
      { path: 'tasks', element: withModule('tasks', TaskManagement) },
      { path: 'requirements', element: withModule('requirements', RequirementsManagement) },
      { path: 'risks', element: withModule('projects', RiskManagement) },

      { path: 'meetings', element: withModule('meetings', MeetingList) },
      { path: 'meetings/create', element: withModule('meetings', CreateMeeting) },
      { path: 'meetings/analytics/comparison', element: withModule('meetings', MeetingComparison) },
      { path: 'meetings/recordings', element: withModule('meetings', RecordingList) },
      { path: 'meetings/recordings/:recordingId', element: withModule('meetings', RecordingDetail) },
      { path: 'meetings/recordings/:recordingId/player', element: withModule('meetings', RecordingPlayer) },
      { path: 'meetings/room/:meetingId', element: withModule('meetings', MeetingRoom) },
      { path: 'meetings/join/:meetingCode', element: withModule('meetings', MeetingRoom) },
      { path: 'meetings/:id/edit', element: withModule('meetings', EditMeeting) },
      { path: 'meetings/:id/analytics', element: withModule('meetings', AnalyticsDashboard) },
      { path: 'meetings/:id/analytics/participation', element: withModule('meetings', ParticipationAnalysis) },
      { path: 'meetings/:id/analytics/summary', element: withModule('meetings', MeetingSummary) },
      { path: 'meetings/:id/analytics/minutes', element: withModule('meetings', MeetingMinutes) },
      { path: 'meetings/:id/analytics/actions', element: withModule('meetings', ActionItems) },
      { path: 'meetings/:id/analytics/reports', element: withModule('meetings', ReportGenerator) },
      { path: 'meetings/:id/recordings', element: withModule('meetings', RecordingList) },
      { path: 'meetings/:id', element: withModule('meetings', MeetingDetail) },

      { path: 'test-manager', element: withModule('testing', TestManager) },
      { path: 'test-manager/test-plans', element: withModule('testing', TestPlanList) },
      { path: 'test-manager/test-plans/create', element: withModule('testing', TestPlanCreate) },
      { path: 'test-manager/test-plans/:id/edit', element: withModule('testing', TestPlanEdit) },
      { path: 'test-manager/test-plans/:id', element: withModule('testing', TestPlanDetail) },
      { path: 'test-manager/test-cases', element: withModule('testing', TestCaseList) },
      { path: 'test-manager/test-cases/create', element: withModule('testing', TestCaseCreate) },
      { path: 'test-manager/test-cases/:id/edit', element: withModule('testing', TestCaseEdit) },
      { path: 'test-manager/test-cases/:id', element: withModule('testing', TestCaseDetail) },
      { path: 'test-manager/executions', element: withModule('testing', ExecutionDashboard) },
      { path: 'test-manager/executions/:executionId', element: withModule('testing', ExecutionDetail) },
      { path: 'test-manager/executions/manual', element: withModule('testing', ManualExecution) },
      { path: 'test-manager/executions/manual/:testCaseId', element: withModule('testing', ManualExecution) },
      { path: 'test-manager/executions/automation', element: withModule('testing', AutomationExecution) },
      { path: 'test-manager/defects', element: withModule('defects', DefectList) },
      { path: 'test-manager/defects/analytics', element: withModule('defects', DefectAnalytics) },
      { path: 'test-manager/reports', element: withModule('reports', ReportDashboard) },
      { path: 'test-manager/reports/generate', element: withModule('reports', ReportGenerate) },
      { path: 'test-manager/performance', element: withModule('testing', PerformanceTest) },
      { path: 'test-manager/security', element: withModule('testing', SecurityTest) },

      { path: 'allure-reports', element: withModule('reports', AllureReports) },
      { path: 'reports', element: withModule('reports', Reports) },
      { path: 'auto-recovery', element: withModule('testing', AutoRecovery) },
    ],
  },
  {
    path: '*',
    element: <NotFound />,
  },
]
