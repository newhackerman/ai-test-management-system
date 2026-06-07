import React from 'react'
import type { Project } from '@/types/project'
import { ProjectCard } from '../ProjectCard'

interface MemoizedProjectCardProps {
  project: Project
  onView?: (project: Project) => void
  onEdit?: (project: Project) => void
  onDelete?: (project: Project) => void
  onExport?: (project: Project) => void
  onDuplicate?: (project: Project) => void
  className?: string
}

export const MemoizedProjectCard = React.memo((props: MemoizedProjectCardProps) => (
  <ProjectCard {...props} />
))

MemoizedProjectCard.displayName = 'MemoizedProjectCard'

export default MemoizedProjectCard
