# API Examples

This document provides practical examples of using the AI Test Management System API.

## Authentication Examples

### Login and Get Token

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin@example.com",
    "password": "password123"
  }'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### Refresh Token

```bash
curl -X POST "http://localhost:8000/api/v1/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'
```

## Project Management Examples

### Create a New Project

```bash
curl -X POST "http://localhost:8000/api/v1/projects" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "E-commerce Testing Project",
    "description": "Comprehensive testing of the new e-commerce platform including web and mobile applications",
    "project_type": "FUNCTIONAL",
    "priority": "HIGH",
    "project_manager_id": 1,
    "planned_start_date": "2024-02-01",
    "planned_end_date": "2024-04-30",
    "budget": 75000.00,
    "tags": ["web", "mobile", "api", "e-commerce"]
  }'
```

Response:
```json
{
  "id": 1,
  "project_code": "PROJ-20240201-001",
  "project_name": "E-commerce Testing Project",
  "description": "Comprehensive testing of the new e-commerce platform including web and mobile applications",
  "project_type": "FUNCTIONAL",
  "priority": "HIGH",
  "status": "PLANNING",
  "health_score": 100,
  "risk_level": "LOW",
  "planned_start_date": "2024-02-01",
  "planned_end_date": "2024-04-30",
  "project_manager_id": 1,
  "budget": 75000.00,
  "actual_cost": 0.00,
  "progress_percentage": 0.00,
  "task_count": 0,
  "completed_task_count": 0,
  "tags": ["web", "mobile", "api", "e-commerce"],
  "created_at": "2024-01-20T10:30:00Z",
  "updated_at": "2024-01-20T10:30:00Z"
}
```

### List Projects with Filtering

```bash
# Get all active projects
curl -X GET "http://localhost:8000/api/v1/projects?status=IN_PROGRESS&page=1&size=10" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Search projects by name
curl -X GET "http://localhost:8000/api/v1/projects?search=e-commerce&sort_by=created_at&sort_order=desc" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Filter by project type and priority
curl -X GET "http://localhost:8000/api/v1/projects?project_type=FUNCTIONAL&priority=HIGH" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Response:
```json
{
  "items": [
    {
      "id": 1,
      "project_code": "PROJ-20240201-001",
      "project_name": "E-commerce Testing Project",
      "status": "IN_PROGRESS",
      "priority": "HIGH",
      "progress_percentage": 45.5,
      "created_at": "2024-01-20T10:30:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "size": 10,
  "pages": 1
}
```

### Update Project Status

```bash
curl -X PUT "http://localhost:8000/api/v1/projects/1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "IN_PROGRESS",
    "priority": "URGENT"
  }'
```

### Get Project Progress

```bash
curl -X GET "http://localhost:8000/api/v1/projects/1/progress" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Response:
```json
{
  "project_id": 1,
  "overall_progress": 65.5,
  "time_progress": {
    "progress_rate": 70.0,
    "days_elapsed": 35,
    "total_days": 50,
    "remaining_days": 15,
    "deviation": -0.05
  },
  "task_progress": {
    "progress_rate": 64.0,
    "total_tasks": 25,
    "completed_tasks": 16,
    "in_progress_tasks": 5,
    "blocked_tasks": 1
  },
  "quality_progress": {
    "progress_rate": 80.0,
    "test_coverage": 85.5,
    "pass_rate": 93.3,
    "defect_density": 0.05
  },
  "milestone_progress": {
    "progress_rate": 50.0,
    "total_milestones": 4,
    "completed_milestones": 2,
    "overdue_milestones": 0
  },
  "calculated_at": "2024-01-20T14:45:00Z"
}
```

## Task Management Examples

### Create a Task

```bash
curl -X POST "http://localhost:8000/api/v1/projects/1/tasks" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task_name": "Design user login test cases",
    "description": "Create comprehensive test cases for user authentication including positive and negative scenarios",
    "task_type": "TEST_DESIGN",
    "priority": "HIGH",
    "assignee_id": 2,
    "planned_start_date": "2024-02-05",
    "planned_end_date": "2024-02-07",
    "estimated_hours": 16.0,
    "acceptance_criteria": "All login scenarios covered with detailed test steps, expected results, and test data requirements",
    "dependencies": [1, 3]
  }'
```

Response:
```json
{
  "id": 10,
  "project_id": 1,
  "task_code": "TASK-010",
  "task_name": "Design user login test cases",
  "description": "Create comprehensive test cases for user authentication including positive and negative scenarios",
  "task_type": "TEST_DESIGN",
  "priority": "HIGH",
  "status": "ASSIGNED",
  "assignee_id": 2,
  "planned_start_date": "2024-02-05",
  "planned_end_date": "2024-02-07",
  "estimated_hours": 16.0,
  "actual_hours": 0.0,
  "acceptance_criteria": "All login scenarios covered with detailed test steps, expected results, and test data requirements",
  "created_at": "2024-01-20T15:30:00Z",
  "updated_at": "2024-01-20T15:30:00Z"
}
```

### List Project Tasks

```bash
# Get all tasks for a project
curl -X GET "http://localhost:8000/api/v1/projects/1/tasks" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Filter tasks by status and assignee
curl -X GET "http://localhost:8000/api/v1/projects/1/tasks?status=IN_PROGRESS&assignee_id=2" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Get tasks by type
curl -X GET "http://localhost:8000/api/v1/projects/1/tasks?task_type=TEST_EXECUTION&page=1&size=20" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Update Task Status

```bash
curl -X PUT "http://localhost:8000/api/v1/tasks/10" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "IN_PROGRESS",
    "actual_hours": 4.5,
    "remaining_hours": 11.5
  }'
```

### Log Work Time

```bash
curl -X POST "http://localhost:8000/api/v1/tasks/10/work-logs" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "work_date": "2024-02-05",
    "hours_worked": 4.5,
    "work_type": "TEST_DESIGN",
    "description": "Created test cases for valid login scenarios including username/email login, password validation, and remember me functionality",
    "achievements": "Completed 15 test cases covering positive login flows",
    "issues_encountered": "Need clarification on password complexity requirements"
  }'
```

## Team Management Examples

### Add Team Member to Project

```bash
curl -X POST "http://localhost:8000/api/v1/projects/1/members" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 5,
    "role_in_project": "TESTER",
    "allocation_percentage": 80.0,
    "join_date": "2024-02-01",
    "skills": ["manual-testing", "automation", "api-testing"],
    "responsibilities": "Execute test cases, report defects, maintain test documentation"
  }'
```

### Get Team Workload Analysis

```bash
curl -X GET "http://localhost:8000/api/v1/projects/1/team/workload" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Response:
```json
{
  "project_id": 1,
  "total_members": 6,
  "total_capacity": 240.0,
  "total_workload": 180.5,
  "utilization_rate": 0.75,
  "member_workloads": [
    {
      "user_id": 2,
      "user_name": "John Doe",
      "role": "TESTER",
      "capacity": 40.0,
      "current_workload": 35.5,
      "utilization_rate": 0.89,
      "active_tasks": 3,
      "overdue_tasks": 0
    }
  ],
  "overloaded_members": [],
  "underloaded_members": [
    {
      "user_id": 4,
      "utilization_rate": 0.45
    }
  ],
  "analyzed_at": "2024-01-20T16:00:00Z"
}
```

## Statistics and Reporting Examples

### Get Project Statistics

```bash
curl -X GET "http://localhost:8000/api/v1/projects/1/statistics" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Response:
```json
{
  "project_id": 1,
  "summary": {
    "total_tasks": 25,
    "completed_tasks": 16,
    "completion_rate": 0.64,
    "total_hours_estimated": 200.0,
    "total_hours_actual": 145.5,
    "efficiency_rate": 1.37
  },
  "progress_by_type": {
    "REQUIREMENT_ANALYSIS": {"completed": 3, "total": 3, "rate": 1.0},
    "TEST_DESIGN": {"completed": 8, "total": 10, "rate": 0.8},
    "TEST_EXECUTION": {"completed": 5, "total": 12, "rate": 0.42}
  },
  "team_performance": {
    "average_task_completion_time": 2.5,
    "quality_score": 0.92,
    "collaboration_score": 0.85
  },
  "quality_metrics": {
    "test_coverage": 0.855,
    "defect_density": 0.05,
    "pass_rate": 0.933
  },
  "calculated_at": "2024-01-20T16:15:00Z"
}
```

### Generate Project Report

```bash
curl -X POST "http://localhost:8000/api/v1/projects/1/reports" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "report_type": "PROGRESS_SUMMARY",
    "format": "PDF",
    "include_charts": true,
    "date_range": {
      "start_date": "2024-02-01",
      "end_date": "2024-02-29"
    }
  }'
```

Response:
```json
{
  "report_id": "RPT-20240220-001",
  "status": "GENERATING",
  "download_url": null,
  "estimated_completion": "2024-02-20T10:35:00Z"
}
```

### Check Report Status

```bash
curl -X GET "http://localhost:8000/api/v1/reports/RPT-20240220-001" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Response:
```json
{
  "report_id": "RPT-20240220-001",
  "status": "COMPLETED",
  "download_url": "https://api.example.com/reports/RPT-20240220-001/download",
  "generated_at": "2024-02-20T10:33:45Z",
  "expires_at": "2024-02-27T10:33:45Z"
}
```

## Error Handling Examples

### Validation Error Response

Request:
```bash
curl -X POST "http://localhost:8000/api/v1/projects" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "",
    "planned_start_date": "2024-03-01",
    "planned_end_date": "2024-02-01"
  }'
```

Response (422 Unprocessable Entity):
```json
{
  "error": "Validation Error",
  "message": "Input validation failed",
  "details": {
    "field_errors": {
      "project_name": ["This field is required and cannot be empty"],
      "project_type": ["This field is required"],
      "project_manager_id": ["This field is required"],
      "planned_end_date": ["End date must be after start date"]
    }
  },
  "timestamp": "2024-01-20T16:45:00Z"
}
```

### Authentication Error Response

Request without token:
```bash
curl -X GET "http://localhost:8000/api/v1/projects"
```

Response (401 Unauthorized):
```json
{
  "error": "Unauthorized",
  "message": "Authentication required",
  "timestamp": "2024-01-20T16:50:00Z"
}
```

### Resource Not Found Response

Request:
```bash
curl -X GET "http://localhost:8000/api/v1/projects/999" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Response (404 Not Found):
```json
{
  "error": "Not Found",
  "message": "Project with ID 999 not found",
  "timestamp": "2024-01-20T16:55:00Z"
}
```

## Batch Operations Examples

### Bulk Task Creation

```bash
curl -X POST "http://localhost:8000/api/v1/projects/1/tasks/bulk" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tasks": [
      {
        "task_name": "Setup test environment",
        "task_type": "ENVIRONMENT_SETUP",
        "priority": "HIGH",
        "estimated_hours": 8.0
      },
      {
        "task_name": "Create API test cases",
        "task_type": "TEST_DESIGN",
        "priority": "MEDIUM",
        "estimated_hours": 12.0
      },
      {
        "task_name": "Execute smoke tests",
        "task_type": "TEST_EXECUTION",
        "priority": "HIGH",
        "estimated_hours": 4.0
      }
    ]
  }'
```

### Bulk Status Update

```bash
curl -X PUT "http://localhost:8000/api/v1/tasks/bulk-update" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task_ids": [10, 11, 12],
    "updates": {
      "status": "IN_PROGRESS",
      "assignee_id": 2
    }
  }'
```

## WebSocket Examples

### Real-time Project Updates

```javascript
// JavaScript WebSocket client example
const ws = new WebSocket('ws://localhost:8000/ws/projects/1');

ws.onopen = function(event) {
    console.log('Connected to project updates');
    
    // Authenticate
    ws.send(JSON.stringify({
        type: 'auth',
        token: 'YOUR_ACCESS_TOKEN'
    }));
};

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    
    switch(data.type) {
        case 'task_updated':
            console.log('Task updated:', data.task);
            break;
        case 'progress_updated':
            console.log('Progress updated:', data.progress);
            break;
        case 'team_member_added':
            console.log('New team member:', data.member);
            break;
    }
};

ws.onerror = function(error) {
    console.error('WebSocket error:', error);
};
```

## Rate Limiting

The API implements rate limiting to ensure fair usage:

- **Standard users**: 1000 requests per hour
- **Premium users**: 5000 requests per hour
- **Admin users**: 10000 requests per hour

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1642694400
```

When rate limit is exceeded (429 Too Many Requests):
```json
{
  "error": "Rate Limit Exceeded",
  "message": "Too many requests. Please try again later.",
  "retry_after": 3600,
  "timestamp": "2024-01-20T17:00:00Z"
}
```

## Pagination

All list endpoints support pagination:

```bash
# Standard pagination
curl -X GET "http://localhost:8000/api/v1/projects?page=2&size=25" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Cursor-based pagination (for large datasets)
curl -X GET "http://localhost:8000/api/v1/projects?cursor=eyJpZCI6MTAwfQ&size=50" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Response includes pagination metadata:
```json
{
  "items": [...],
  "total": 150,
  "page": 2,
  "size": 25,
  "pages": 6,
  "has_next": true,
  "has_prev": true,
  "next_cursor": "eyJpZCI6MTI1fQ"
}
```