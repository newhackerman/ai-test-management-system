/**
 * AI模型配置管理页面
 */
import React from 'react';
import { AIModelConfigManager } from '../components/ai/AIModelConfigManager';

const AIModelConfiguration: React.FC = () => {
  return (
    <div className="container mx-auto py-6">
      <AIModelConfigManager />
    </div>
  );
};

export default AIModelConfiguration;