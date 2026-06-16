import React, { useMemo } from 'react';
import { CheckCircle, AlertCircle, XCircle, Clock } from 'lucide-react';

interface StatusPanelProps {
  config: {
    title?: string;
    showServices?: boolean;
    autoRefresh?: boolean;
  };
  data?: any;
}

const StatusPanel: React.FC<StatusPanelProps> = ({ config, data }) => {
  const { showServices = true } = config;

  // Process status data
  const statusItems = useMemo(() => {
    if (data && Array.isArray(data)) {
      return data;
    }

    if (data && typeof data === 'object' && data.services) {
      return data.services;
    }

    // Generate sample status data
    return [
      { name: '数据库服务', status: 'healthy', uptime: '99.9%', responseTime: '12ms' },
      { name: 'API网关', status: 'healthy', uptime: '99.8%', responseTime: '45ms' },
      { name: '缓存服务', status: 'warning', uptime: '98.5%', responseTime: '8ms' },
      { name: '消息队列', status: 'healthy', uptime: '99.7%', responseTime: '23ms' },
      { name: '文件存储', status: 'error', uptime: '95.2%', responseTime: '156ms' }
    ];
  }, [data]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle className="h-4 w-4 text-green-500 dark:text-green-400" />;
      case 'warning':
        return <AlertCircle className="h-4 w-4 text-yellow-500" />;
      case 'error':
        return <XCircle className="h-4 w-4 text-red-500 dark:text-red-400" />;
      case 'pending':
        return <Clock className="h-4 w-4 text-blue-500 dark:text-blue-400" />;
      default:
        return <AlertCircle className="h-4 w-4 text-gray-400 dark:text-gray-500" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'bg-green-100 text-green-800';
      case 'warning':
        return 'bg-yellow-100 text-yellow-800';
      case 'error':
        return 'bg-red-100 text-red-800 dark:text-red-300 dark:bg-red-900/30';
      case 'pending':
        return 'bg-blue-100 text-blue-800 dark:text-blue-300 dark:bg-blue-900/30';
      default:
        return 'bg-gray-100 text-gray-800 dark:text-gray-200 dark:bg-gray-800';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'healthy':
        return '正常';
      case 'warning':
        return '警告';
      case 'error':
        return '错误';
      case 'pending':
        return '待定';
      default:
        return '未知';
    }
  };

  // Calculate overall health
  const overallHealth = useMemo(() => {
    const healthyCount = statusItems.filter(item => item.status === 'healthy').length;
    const totalCount = statusItems.length;
    const percentage = totalCount > 0 ? (healthyCount / totalCount) * 100 : 0;
    
    if (percentage >= 90) return { status: 'healthy', text: '系统健康' };
    if (percentage >= 70) return { status: 'warning', text: '部分异常' };
    return { status: 'error', text: '系统异常' };
  }, [statusItems]);

  return (
    <div className="h-full flex flex-col">
      {/* Overall Status */}
      <div className="flex items-center justify-between mb-4 p-3 bg-gray-50 rounded-lg dark:bg-gray-800/50">
        <div className="flex items-center space-x-2">
          {getStatusIcon(overallHealth.status)}
          <span className="font-medium text-gray-900 dark:text-gray-100">
            {overallHealth.text}
          </span>
        </div>
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(overallHealth.status)}`}>
          {statusItems.filter(item => item.status === 'healthy').length}/{statusItems.length} 正常
        </span>
      </div>

      {/* Service List */}
      <div className="flex-1 space-y-2 overflow-auto">
        {statusItems.map((item, index) => (
          <div key={index} className="flex items-center justify-between p-2 border border-gray-200 rounded-lg hover:bg-gray-50 dark:bg-gray-800/50 dark:hover:bg-gray-800 dark:border-gray-700">
            <div className="flex items-center space-x-3">
              {getStatusIcon(item.status)}
              <div>
                <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                  {item.name}
                </div>
                {item.responseTime && (
                  <div className="text-xs text-gray-500 dark:text-gray-400">
                    响应时间: {item.responseTime}
                  </div>
                )}
              </div>
            </div>
            
            <div className="text-right">
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(item.status)}`}>
                {getStatusText(item.status)}
              </span>
              {item.uptime && (
                <div className="text-xs text-gray-500 mt-1 dark:text-gray-400">
                  运行时间: {item.uptime}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Last Updated */}
      <div className="text-xs text-gray-500 text-center mt-3 pt-3 border-t dark:text-gray-400">
        最后更新: {new Date().toLocaleTimeString('zh-CN')}
      </div>
    </div>
  );
};

export default StatusPanel;