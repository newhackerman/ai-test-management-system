# AI Test Management System - Developer Documentation

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Development Setup](#development-setup)
3. [API Documentation](#api-documentation)
4. [Database Schema](#database-schema)
5. [Frontend Development](#frontend-development)
6. [Backend Development](#backend-development)
7. [Testing](#testing)
8. [Deployment](#deployment)
9. [Contributing](#contributing)
10. [Troubleshooting](#troubleshooting)

## Architecture Overview

### System Architecture

The AI Test Management System follows a modern microservices architecture:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend API   │    │   Database      │
│   (React)       │◄──►│   (FastAPI)     │◄──►│   (MySQL)       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   CDN/Static    │    │   Redis Cache   │    │   File Storage  │
│   Assets        │    │   (Session)     │    │   (Uploads)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Technology Stack

**Frontend:**
- React 18+ with TypeScript
- Vite for build tooling
- Tailwind CSS for styling
- Radix UI for components
- React Query for data fetching
- Zustand for state management

**Backend:**
- FastAPI (Python 3.11+)
- SQLAlchemy ORM
- Alembic for migrations
- Redis for caching
- JWT for authentication
- Pydantic for validation

**Database:**
- MySQL 8.0+
- Redis 7.0+

**Infrastructure:**
- Docker & Docker Compose
- Kubernetes (production)
- Nginx (reverse proxy)
- GitHub Actions (CI/CD)

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- Git

### Quick Start

1. **Clone Repository**
```bash
git clone https://github.com/your-org/ai-test-management.git
cd ai-test-management
```

2. **Backend Setup**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your configuration
```

3. **Frontend Setup**
```bash
cd frontend
npm install
cp .env.example .env.local
# Edit .env.local with your configuration
```

4. **Database Setup**
```bash
cd backend
docker-compose up -d mysql redis
alembic upgrade head
python init_database.py
```

5. **Start Development Servers**
```bash
# Terminal 1 - Backend
cd backend
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 - Frontend
cd frontend
npm run dev
```

### Environment Variables

**Backend (.env):**
```env
DATABASE_URL=mysql+asyncmy://user:password@localhost:3306/ai_test_db
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key
DEBUG=true
LOG_LEVEL=debug
```

**Frontend (.env.local):**
```env
VITE_API_BASE_URL=http://localhost:8000
VITE_APP_VERSION=1.0.0
```#
# API Documentation

### Authentication

The API uses JWT Bearer token authentication:

```bash
# Login to get tokens
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin@example.com", "password": "password"}'

# Use token in subsequent requests
curl -X GET http://localhost:8000/api/v1/projects \
  -H "Authorization: Bearer <your-access-token>"
```

### API Endpoints

#### Projects API

**List Projects**
```http
GET /api/v1/projects
Query Parameters:
- page: int (default: 1)
- size: int (default: 20)
- status: string (optional)
- project_type: string (optional)
- search: string (optional)
```

**Create Project**
```http
POST /api/v1/projects
Content-Type: application/json

{
  "project_name": "Test Project",
  "description": "Project description",
  "project_type": "FUNCTIONAL",
  "priority": "HIGH",
  "project_manager_id": 1,
  "planned_start_date": "2024-01-15",
  "planned_end_date": "2024-03-15"
}
```

**Get Project**
```http
GET /api/v1/projects/{project_id}
```

**Update Project**
```http
PUT /api/v1/projects/{project_id}
Content-Type: application/json

{
  "project_name": "Updated Project Name",
  "priority": "URGENT"
}
```

#### Tasks API

**List Project Tasks**
```http
GET /api/v1/projects/{project_id}/tasks
Query Parameters:
- page: int (default: 1)
- size: int (default: 20)
- status: string (optional)
- assignee_id: int (optional)
```

**Create Task**
```http
POST /api/v1/projects/{project_id}/tasks
Content-Type: application/json

{
  "task_name": "Design test cases",
  "description": "Create comprehensive test cases",
  "task_type": "TEST_DESIGN",
  "priority": "HIGH",
  "assignee_id": 2,
  "estimated_hours": 8.0
}
```

### Error Handling

The API returns consistent error responses:

```json
{
  "error": "Validation Error",
  "message": "Input validation failed",
  "details": {
    "field_errors": {
      "project_name": ["This field is required"]
    }
  },
  "timestamp": "2024-01-20T14:45:00Z"
}
```

Common HTTP status codes:
- 200: Success
- 201: Created
- 400: Bad Request
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found
- 422: Validation Error
- 500: Internal Server Error

## Database Schema

### Core Tables

#### Projects Table
```sql
CREATE TABLE projects (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    project_code VARCHAR(50) NOT NULL UNIQUE,
    project_name VARCHAR(200) NOT NULL,
    description TEXT,
    project_type ENUM('FUNCTIONAL','PERFORMANCE','SECURITY','AUTOMATION','INTEGRATION'),
    priority ENUM('LOW','MEDIUM','HIGH','URGENT') DEFAULT 'MEDIUM',
    status ENUM('PLANNING','IN_PROGRESS','ON_HOLD','COMPLETED','CANCELLED','ARCHIVED'),
    project_manager_id BIGINT NOT NULL,
    planned_start_date DATE,
    planned_end_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

#### Tasks Table
```sql
CREATE TABLE project_tasks (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    project_id BIGINT NOT NULL,
    task_code VARCHAR(50),
    task_name VARCHAR(200) NOT NULL,
    description TEXT,
    task_type ENUM('REQUIREMENT_ANALYSIS','TEST_DESIGN','TEST_EXECUTION','AUTOMATION_DEVELOPMENT'),
    priority ENUM('LOW','MEDIUM','HIGH','URGENT') DEFAULT 'MEDIUM',
    status ENUM('TODO','ASSIGNED','IN_PROGRESS','ON_HOLD','BLOCKED','PENDING_REVIEW','COMPLETED','CANCELLED'),
    assignee_id BIGINT,
    estimated_hours DECIMAL(6,2),
    actual_hours DECIMAL(6,2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);
```

### Migrations

Use Alembic for database migrations:

```bash
# Create new migration
alembic revision --autogenerate -m "Add new table"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## Frontend Development

### Project Structure

```
frontend/src/
├── components/          # Reusable UI components
│   ├── ui/             # Base UI components
│   └── projects/       # Project-specific components
├── pages/              # Page components
├── hooks/              # Custom React hooks
├── services/           # API service functions
├── stores/             # State management
├── utils/              # Utility functions
├── types/              # TypeScript type definitions
└── styles/             # Global styles
```

### Component Development

**Creating a New Component**

```typescript
// components/projects/ProjectCard.tsx
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Project } from '@/types/project';

interface ProjectCardProps {
  project: Project;
  onClick?: (project: Project) => void;
}

export const ProjectCard: React.FC<ProjectCardProps> = ({ project, onClick }) => {
  return (
    <Card 
      className="cursor-pointer hover:shadow-md transition-shadow"
      onClick={() => onClick?.(project)}
    >
      <CardHeader>
        <CardTitle className="flex justify-between items-center">
          {project.project_name}
          <Badge variant={project.priority === 'HIGH' ? 'destructive' : 'default'}>
            {project.priority}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-gray-600 mb-2">{project.description}</p>
        <div className="flex justify-between text-xs text-gray-500">
          <span>Progress: {project.progress_percentage}%</span>
          <span>Status: {project.status}</span>
        </div>
      </CardContent>
    </Card>
  );
};
```

### State Management

**Using Zustand Store**

```typescript
// stores/projectStore.ts
import { create } from 'zustand';
import { Project } from '@/types/project';
import { projectService } from '@/services/projectService';

interface ProjectState {
  projects: Project[];
  currentProject: Project | null;
  loading: boolean;
  error: string | null;
  
  fetchProjects: () => Promise<void>;
  setCurrentProject: (project: Project) => void;
  updateProject: (id: number, updates: Partial<Project>) => Promise<void>;
}

export const useProjectStore = create<ProjectState>((set, get) => ({
  projects: [],
  currentProject: null,
  loading: false,
  error: null,

  fetchProjects: async () => {
    set({ loading: true, error: null });
    try {
      const projects = await projectService.getProjects();
      set({ projects, loading: false });
    } catch (error) {
      set({ error: error.message, loading: false });
    }
  },

  setCurrentProject: (project) => {
    set({ currentProject: project });
  },

  updateProject: async (id, updates) => {
    try {
      const updatedProject = await projectService.updateProject(id, updates);
      set(state => ({
        projects: state.projects.map(p => p.id === id ? updatedProject : p),
        currentProject: state.currentProject?.id === id ? updatedProject : state.currentProject
      }));
    } catch (error) {
      set({ error: error.message });
    }
  }
}));
```

### API Integration

**Service Layer**

```typescript
// services/projectService.ts
import { api } from './api';
import { Project, CreateProjectRequest, UpdateProjectRequest } from '@/types/project';

export const projectService = {
  async getProjects(params?: {
    page?: number;
    size?: number;
    status?: string;
    search?: string;
  }): Promise<{ items: Project[]; total: number; page: number; pages: number }> {
    const response = await api.get('/projects', { params });
    return response.data;
  },

  async getProject(id: number): Promise<Project> {
    const response = await api.get(`/projects/${id}`);
    return response.data;
  },

  async createProject(data: CreateProjectRequest): Promise<Project> {
    const response = await api.post('/projects', data);
    return response.data;
  },

  async updateProject(id: number, data: UpdateProjectRequest): Promise<Project> {
    const response = await api.put(`/projects/${id}`, data);
    return response.data;
  },

  async deleteProject(id: number): Promise<void> {
    await api.delete(`/projects/${id}`);
  }
};
```

## Backend Development

### Project Structure

```
backend/src/
├── api/                # API route handlers
│   └── v1/            # API version 1
├── models/            # SQLAlchemy models
├── services/          # Business logic services
├── utils/             # Utility functions
├── core/              # Core configuration
├── migrations/        # Database migrations
└── tests/             # Test files
```

### Creating API Endpoints

**Route Handler**

```python
# api/v1/projects.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from src.core.database import get_db
from src.services.project_service import ProjectService
from src.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from src.core.auth import get_current_user
from src.models.user import User

router = APIRouter(prefix="/projects", tags=["projects"])

@router.get("/", response_model=dict)
async def list_projects(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List projects with pagination and filtering."""
    project_service = ProjectService(db)
    
    result = await project_service.list_projects(
        page=page,
        size=size,
        status=status,
        search=search,
        user_id=current_user.id
    )
    
    return result

@router.post("/", response_model=ProjectResponse, status_code=201)
async def create_project(
    project_data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new project."""
    project_service = ProjectService(db)
    
    project = await project_service.create_project(
        project_data=project_data,
        creator_id=current_user.id
    )
    
    return project
```

### Service Layer

```python
# services/project_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional, Dict, Any
from datetime import datetime

from src.models.project import Project
from src.models.project_member import ProjectMember
from src.schemas.project import ProjectCreate, ProjectUpdate
from src.core.exceptions import NotFoundError, ValidationError

class ProjectService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_projects(
        self,
        page: int = 1,
        size: int = 20,
        status: Optional[str] = None,
        search: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """List projects with pagination and filtering."""
        
        query = select(Project).where(Project.deleted_at.is_(None))
        
        # Apply filters
        if status:
            query = query.where(Project.status == status)
        
        if search:
            query = query.where(
                Project.project_name.contains(search) |
                Project.description.contains(search)
            )
        
        if user_id:
            # Filter by user's projects
            query = query.join(ProjectMember).where(
                ProjectMember.user_id == user_id
            )
        
        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query)
        
        # Apply pagination
        offset = (page - 1) * size
        query = query.offset(offset).limit(size)
        
        # Execute query
        result = await self.db.execute(query)
        projects = result.scalars().all()
        
        return {
            "items": projects,
            "total": total,
            "page": page,
            "size": size,
            "pages": (total + size - 1) // size
        }

    async def create_project(
        self,
        project_data: ProjectCreate,
        creator_id: int
    ) -> Project:
        """Create a new project."""
        
        # Validate project data
        await self._validate_project_data(project_data)
        
        # Generate project code
        project_code = await self._generate_project_code()
        
        # Create project
        project = Project(
            project_code=project_code,
            project_name=project_data.project_name,
            description=project_data.description,
            project_type=project_data.project_type,
            priority=project_data.priority,
            project_manager_id=project_data.project_manager_id,
            planned_start_date=project_data.planned_start_date,
            planned_end_date=project_data.planned_end_date,
            budget=project_data.budget,
            created_by=creator_id
        )
        
        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)
        
        return project

    async def _validate_project_data(self, project_data: ProjectCreate):
        """Validate project creation data."""
        
        # Check if project name is unique
        existing = await self.db.scalar(
            select(Project).where(
                and_(
                    Project.project_name == project_data.project_name,
                    Project.deleted_at.is_(None)
                )
            )
        )
        
        if existing:
            raise ValidationError("Project name already exists")
        
        # Validate date range
        if project_data.planned_start_date >= project_data.planned_end_date:
            raise ValidationError("Start date must be before end date")

    async def _generate_project_code(self) -> str:
        """Generate unique project code."""
        today = datetime.now().strftime("%Y%m%d")
        
        # Count projects created today
        count = await self.db.scalar(
            select(func.count()).where(
                Project.project_code.like(f"PROJ-{today}-%")
            )
        )
        
        return f"PROJ-{today}-{count + 1:03d}"
```

### Database Models

```python
# models/project.py
from sqlalchemy import Column, BigInteger, String, Text, Enum, DECIMAL, Date, DateTime, JSON, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

class Project(Base):
    __tablename__ = 'projects'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    project_code = Column(String(50), unique=True, nullable=False)
    project_name = Column(String(200), nullable=False)
    description = Column(Text)
    
    # Enums
    project_type = Column(Enum('FUNCTIONAL', 'PERFORMANCE', 'SECURITY', 'AUTOMATION', 'INTEGRATION'), nullable=False)
    priority = Column(Enum('LOW', 'MEDIUM', 'HIGH', 'URGENT'), default='MEDIUM')
    status = Column(Enum('PLANNING', 'IN_PROGRESS', 'ON_HOLD', 'COMPLETED', 'CANCELLED', 'ARCHIVED'), default='PLANNING')
    
    # Dates
    planned_start_date = Column(Date)
    planned_end_date = Column(Date)
    actual_start_date = Column(Date)
    actual_end_date = Column(Date)
    
    # Management
    project_manager_id = Column(BigInteger, nullable=False)
    budget = Column(DECIMAL(15, 2))
    progress_percentage = Column(DECIMAL(5, 2), default=0.00)
    
    # Metadata
    tags = Column(JSON)
    created_by = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime)
```

## Testing

### Backend Testing

**Unit Tests**

```python
# tests/test_project_service.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import date

from src.services.project_service import ProjectService
from src.schemas.project import ProjectCreate
from src.core.exceptions import ValidationError

@pytest.fixture
def mock_db():
    return AsyncMock()

@pytest.fixture
def project_service(mock_db):
    return ProjectService(mock_db)

@pytest.mark.asyncio
async def test_create_project_success(project_service, mock_db):
    """Test successful project creation."""
    
    # Arrange
    project_data = ProjectCreate(
        project_name="Test Project",
        description="Test Description",
        project_type="FUNCTIONAL",
        priority="HIGH",
        project_manager_id=1,
        planned_start_date=date(2024, 1, 15),
        planned_end_date=date(2024, 3, 15)
    )
    
    mock_db.scalar.return_value = None  # No existing project
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    
    # Act
    result = await project_service.create_project(project_data, creator_id=1)
    
    # Assert
    assert result.project_name == "Test Project"
    assert result.project_type == "FUNCTIONAL"
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()

@pytest.mark.asyncio
async def test_create_project_duplicate_name(project_service, mock_db):
    """Test project creation with duplicate name."""
    
    # Arrange
    project_data = ProjectCreate(
        project_name="Existing Project",
        project_type="FUNCTIONAL",
        project_manager_id=1,
        planned_start_date=date(2024, 1, 15),
        planned_end_date=date(2024, 3, 15)
    )
    
    mock_db.scalar.return_value = MagicMock()  # Existing project
    
    # Act & Assert
    with pytest.raises(ValidationError, match="Project name already exists"):
        await project_service.create_project(project_data, creator_id=1)
```

**Integration Tests**

```python
# tests/test_project_api.py
import pytest
from httpx import AsyncClient
from fastapi import status

@pytest.mark.asyncio
async def test_create_project_api(client: AsyncClient, auth_headers):
    """Test project creation API endpoint."""
    
    project_data = {
        "project_name": "API Test Project",
        "description": "Test project via API",
        "project_type": "FUNCTIONAL",
        "priority": "HIGH",
        "project_manager_id": 1,
        "planned_start_date": "2024-01-15",
        "planned_end_date": "2024-03-15"
    }
    
    response = await client.post(
        "/api/v1/projects",
        json=project_data,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["project_name"] == "API Test Project"
    assert data["project_type"] == "FUNCTIONAL"
    assert "project_code" in data
```

### Frontend Testing

**Component Tests**

```typescript
// components/__tests__/ProjectCard.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { ProjectCard } from '../ProjectCard';
import { Project } from '@/types/project';

const mockProject: Project = {
  id: 1,
  project_code: 'PROJ-20240101-001',
  project_name: 'Test Project',
  description: 'Test Description',
  project_type: 'FUNCTIONAL',
  priority: 'HIGH',
  status: 'IN_PROGRESS',
  progress_percentage: 75.5,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z'
};

describe('ProjectCard', () => {
  it('renders project information correctly', () => {
    render(<ProjectCard project={mockProject} />);
    
    expect(screen.getByText('Test Project')).toBeInTheDocument();
    expect(screen.getByText('Test Description')).toBeInTheDocument();
    expect(screen.getByText('HIGH')).toBeInTheDocument();
    expect(screen.getByText('Progress: 75.5%')).toBeInTheDocument();
  });

  it('calls onClick when card is clicked', () => {
    const mockOnClick = jest.fn();
    render(<ProjectCard project={mockProject} onClick={mockOnClick} />);
    
    fireEvent.click(screen.getByText('Test Project'));
    
    expect(mockOnClick).toHaveBeenCalledWith(mockProject);
  });
});
```

### Running Tests

**Backend Tests**
```bash
cd backend
pytest tests/ -v --cov=src --cov-report=html
```

**Frontend Tests**
```bash
cd frontend
npm run test
npm run test:coverage
```

## Deployment

### Docker Deployment

compose 文件在 `backend/docker-compose.yml`，以下命令在 `backend/` 目录下执行
（或在根目录加 `-f backend/docker-compose.yml`）：

**Development**
```bash
docker compose --profile development up -d
```

**Production**
```bash
docker compose --profile production up -d
```
注意：`--profile production` 需要 `backend/nginx/` 配置文件，该目录目前不存在，
见[部署指南](../deployment/README.md)里的已知缺口。也可以用根目录的
`./deploy.sh dev|test|prod`，它会自动处理 compose 文件路径与健康检查。

### Kubernetes Deployment

```bash
# Apply all configurations
kubectl apply -f k8s/

# Or use the deployment script
./scripts/k8s-deploy.sh production
```

### Environment-specific Configurations

**Staging**
- Use staging database
- Enable debug logging
- Reduced resource limits

**Production**
- Production database with backups
- Error logging only
- Full resource allocation
- SSL certificates
- Monitoring enabled

## Contributing

### Development Workflow

1. **Fork Repository**
2. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make Changes**
   - Follow coding standards
   - Add tests for new features
   - Update documentation

4. **Run Tests**
   ```bash
   # Backend
   cd backend && pytest
   
   # Frontend
   cd frontend && npm test
   ```

5. **Submit Pull Request**
   - Clear description
   - Link to related issues
   - Include screenshots if UI changes

### Code Standards

**Python (Backend)**
- Follow PEP 8
- Use type hints
- Document functions with docstrings
- Maximum line length: 88 characters

**TypeScript (Frontend)**
- Use TypeScript strict mode
- Follow React best practices
- Use functional components with hooks
- Consistent naming conventions

### Commit Messages

Follow conventional commits format:
```
type(scope): description

feat(projects): add project creation API
fix(auth): resolve token expiration issue
docs(api): update authentication documentation
```

## Troubleshooting

### Common Development Issues

**Database Connection Issues**
```bash
# Check if MySQL is running
docker-compose ps mysql

# Check database logs
docker-compose logs mysql

# Reset database
docker-compose down -v
docker-compose up -d mysql
```

**Frontend Build Issues**
```bash
# Clear node modules and reinstall
rm -rf node_modules package-lock.json
npm install

# Clear Vite cache
rm -rf node_modules/.vite
```

**API Authentication Issues**
```bash
# Check JWT token validity
python -c "
import jwt
token = 'your-token-here'
print(jwt.decode(token, options={'verify_signature': False}))
"
```

### Performance Optimization

**Database Optimization**
- Add appropriate indexes
- Use database connection pooling
- Implement query caching
- Monitor slow queries

**Frontend Optimization**
- Implement code splitting
- Use React.memo for expensive components
- Optimize bundle size
- Enable gzip compression

**API Optimization**
- Implement response caching
- Use async/await properly
- Add request rate limiting
- Monitor API performance

---

For more detailed information, see the individual documentation files in the `/docs` directory.