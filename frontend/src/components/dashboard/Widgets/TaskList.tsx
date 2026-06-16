import React, { useMemo } from 'react';
import { Badge } from '@/components/ui/Badge';
import { CheckCircle, Clock, AlertTriangle, User } from 'lucide-react';

interface TaskListProps {
  config: {
    title?: string;
    showPriority?: boolean;
    limit?: number;
  };
  data?: any;
}

const TaskList: React.FC<TaskListProps> = ({ config, data }) => {
  const {
    showPriority = true,
    limit = 10
  } = config;

  // Process task data
  const tasks = useMemo(() => {
    if (data && Array.isArray(data)) {
      return data.slice(0, limit);
    }

    if (data && typeof data === 'object' && data.tasks) {
      return data.tasks.slice(0, limit);
    }

    // Generate sample task data
    const sampleTasks = [
      {
        id: 1,
        title: '完成用户认证模块测试',
        priority: 'high',
        status: 'in_progress',
        assignee: '张三',
        dueDate: '2024-01-15',
        progress: 75
      },
      {
        id: 2,
        title: '修复登录页面样式问题',
        priority: 'medium',
        status: 'todo',
        assignee: '李四',
        dueDate: '2024-01-12',
        progress: 0
      },
      {
        id: 3,
        title: '优化数据库查询性能',
        priority: 'high',
        status: 'in_progress',
        assignee: '王五',
        dueDate: '2024-01-18',
        progress: 45
      },
      {
        id: 4,
        title: '编写API文档',
        priority: 'low',
        status: 'todo',
        assignee: '赵六',
        dueDate: '2024-01-20',
        progress: 0
      },
      {
        id: 5,
        title: '部署测试环境',
        priority: 'medium',
        status: 'completed',
        assignee: '钱七',
        dueDate: '2024-01-10',
        progress: 100
      }
    ];

    return sampleTasks.slice(0, limit);
  }, [data, limit]);

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'bg-red-100 text-red-800 dark:text-red-300 dark:bg-red-900/30';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'low':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800 dark:text-gray-200 dark:bg-gray-800';
    }
  };

  const getPriorityText = (priority: string) => {
    switch (priority) {
      case 'high':
        return '高';
      case 'medium':
        return '中';
      case 'low':
        return '低';
      default:
        return '未知';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'in_progress':
        return <Clock className="h-4 w-4 text-blue-500 dark:text-blue-400" />;
      case 'todo':
        return <AlertTriangle className="h-4 w-4 text-gray-400 dark:text-gray-500" />;
      default:
        return <Clock className="h-4 w-4 text-gray-400 dark:text-gray-500" />;
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'completed':
        return '已完成';
      case 'in_progress':
        return '进行中';
      case 'todo':
        return '待开始';
      default:
        return '未知';
    }
  };

  const isOverdue = (dueDate: string) => {
    return new Date(dueDate) < new Date() && new Date(dueDate).toDateString() !== new Date().toDateString();
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const today = new Date();
    const diffTime = date.getTime() - today.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays === 0) {
      return '今天';
    } else if (diffDays === 1) {
      return '明天';
    } else if (diffDays === -1) {
      return '昨天';
    } else if (diffDays > 0) {
      return `${diffDays}天后`;
    } else {
      return `逾期${Math.abs(diffDays)}天`;
    }
  };

  return (
    <div className="h-full flex flex-col">
      <div className="flex-1 space-y-3 overflow-auto">
        {tasks.map((task) => (
          <div key={task.id} className="p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors dark:bg-gray-800/50 dark:hover:bg-gray-800 dark:border-gray-700">
            <div className="flex items-start justify-between mb-2">
              <div className="flex items-start space-x-2 flex-1">
                {getStatusIcon(task.status)}
                <div className="flex-1 min-w-0">
                  <h4 className="text-sm font-medium text-gray-900 truncate dark:text-gray-100">
                    {task.title}
                  </h4>
                  <div className="flex items-center space-x-2 mt-1">
                    <div className="flex items-center space-x-1 text-xs text-gray-500 dark:text-gray-400">
                      <User className="h-3 w-3" />
                      <span>{task.assignee}</span>
                    </div>
                    <span className="text-gray-300">•</span>
                    <span className={`text-xs ${isOverdue(task.dueDate) ? 'text-red-600' : 'text-gray-500'}`}>
                      {formatDate(task.dueDate)}
                    </span>
                  </div>
                </div>
              </div>
              
              <div className="flex items-center space-x-2 ml-2">
                {showPriority && (
                  <Badge className={`text-xs ${getPriorityColor(task.priority)}`}>
                    {getPriorityText(task.priority)}
                  </Badge>
                )}
                <Badge variant="outline" className="text-xs">
                  {getStatusText(task.status)}
                </Badge>
              </div>
            </div>

            {/* Progress bar */}
            {task.progress > 0 && (
              <div className="mt-2">
                <div className="flex items-center justify-between text-xs text-gray-600 mb-1 dark:text-gray-400">
                  <span>进度</span>
                  <span>{task.progress}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-1.5">
                  <div
                    className="bg-blue-500 h-1.5 rounded-full transition-all duration-300"
                    style={{ width: `${task.progress}%` }}
                  />
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Summary */}
      <div className="mt-4 pt-3 border-t text-xs text-gray-500 text-center dark:text-gray-400">
        显示 {tasks.length} 个任务
        {tasks.length >= limit && ` (共 ${limit}+ 个)`}
      </div>
    </div>
  );
};

export default TaskList;