import React from 'react';

interface DataTableProps {
  config: {
    title?: string;
    pagination?: boolean;
    sortable?: boolean;
  };
  data?: any;
}

const DataTable: React.FC<DataTableProps> = ({ config, data }) => {
  return (
    <div className="h-full flex items-center justify-center text-gray-500 dark:text-gray-400">
      <div className="text-center">
        <div className="text-2xl mb-2">📊</div>
        <p className="text-sm">数据表格</p>
        <p className="text-xs text-gray-400 mt-1 dark:text-gray-500">开发中...</p>
      </div>
    </div>
  );
};

export default DataTable;