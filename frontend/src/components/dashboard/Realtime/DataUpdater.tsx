import React, { useEffect, useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useRealtimeContext } from './RealtimeProvider';

interface DataUpdaterProps {
  widgetId: string;
  children: React.ReactNode;
  animationType?: 'pulse' | 'glow' | 'shake' | 'bounce' | 'fade';
  animationDuration?: number;
  showUpdateIndicator?: boolean;
  onDataUpdate?: (data: any) => void;
}

export const DataUpdater: React.FC<DataUpdaterProps> = ({
  widgetId,
  children,
  animationType = 'pulse',
  animationDuration = 1000,
  showUpdateIndicator = true,
  onDataUpdate
}) => {
  const { realtimeData, dataUpdateAnimations } = useRealtimeContext();
  const [isUpdating, setIsUpdating] = useState(false);
  const [updateCount, setUpdateCount] = useState(0);
  const [lastUpdateTime, setLastUpdateTime] = useState<Date | null>(null);
  const previousDataRef = useRef<any>(null);

  // 检测数据更新
  useEffect(() => {
    const currentData = realtimeData[widgetId];
    const previousData = previousDataRef.current;

    if (currentData && JSON.stringify(currentData) !== JSON.stringify(previousData)) {
      setIsUpdating(true);
      setUpdateCount(prev => prev + 1);
      setLastUpdateTime(new Date());
      
      // 调用回调函数
      if (onDataUpdate) {
        onDataUpdate(currentData);
      }

      // 重置动画状态
      const timer = setTimeout(() => {
        setIsUpdating(false);
      }, animationDuration);

      previousDataRef.current = currentData;

      return () => clearTimeout(timer);
    }
  }, [realtimeData, widgetId, animationDuration, onDataUpdate]);

  // 监听全局动画状态
  useEffect(() => {
    const hasAnimation = dataUpdateAnimations.get(widgetId);
    if (hasAnimation) {
      setIsUpdating(true);
      const timer = setTimeout(() => {
        setIsUpdating(false);
      }, animationDuration);

      return () => clearTimeout(timer);
    }
  }, [dataUpdateAnimations, widgetId, animationDuration]);

  // 获取动画变体
  const getAnimationVariants = () => {
    switch (animationType) {
      case 'pulse':
        return {
          initial: { scale: 1 },
          animate: isUpdating ? { scale: [1, 1.05, 1] } : { scale: 1 },
          transition: { duration: animationDuration / 1000, ease: "easeInOut" }
        };
      
      case 'glow':
        return {
          initial: { boxShadow: '0 0 0 rgba(59, 130, 246, 0)' },
          animate: isUpdating 
            ? { boxShadow: ['0 0 0 rgba(59, 130, 246, 0)', '0 0 20px rgba(59, 130, 246, 0.5)', '0 0 0 rgba(59, 130, 246, 0)'] }
            : { boxShadow: '0 0 0 rgba(59, 130, 246, 0)' },
          transition: { duration: animationDuration / 1000, ease: "easeInOut" }
        };
      
      case 'shake':
        return {
          initial: { x: 0 },
          animate: isUpdating ? { x: [-2, 2, -2, 2, 0] } : { x: 0 },
          transition: { duration: animationDuration / 1000, ease: "easeInOut" }
        };
      
      case 'bounce':
        return {
          initial: { y: 0 },
          animate: isUpdating ? { y: [-5, 0, -3, 0] } : { y: 0 },
          transition: { duration: animationDuration / 1000, ease: "easeOut" }
        };
      
      case 'fade':
        return {
          initial: { opacity: 1 },
          animate: isUpdating ? { opacity: [1, 0.7, 1] } : { opacity: 1 },
          transition: { duration: animationDuration / 1000, ease: "easeInOut" }
        };
      
      default:
        return {
          initial: { scale: 1 },
          animate: { scale: 1 },
          transition: { duration: 0 }
        };
    }
  };

  const animationProps = getAnimationVariants();

  return (
    <div className="relative">
      <motion.div
        {...animationProps}
        className="relative"
      >
        {children}
        
        {/* 更新指示器 */}
        <AnimatePresence>
          {showUpdateIndicator && isUpdating && (
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              className="absolute top-2 right-2 z-10"
            >
              <div className="flex items-center space-x-1 bg-green-500 text-white px-2 py-1 rounded-full text-xs">
                <div className="w-2 h-2 bg-white rounded-full animate-pulse"></div>
                <span>更新中</span>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* 更新统计信息 */}
        {updateCount > 0 && (
          <div className="absolute bottom-2 left-2 text-xs text-gray-500 bg-white dark:bg-gray-800 px-2 py-1 rounded shadow-sm">
            <div>更新次数: {updateCount}</div>
            {lastUpdateTime && (
              <div>最后更新: {lastUpdateTime.toLocaleTimeString()}</div>
            )}
          </div>
        )}
      </motion.div>
    </div>
  );
};

// 高阶组件版本
export const withDataUpdater = <P extends object>(
  Component: React.ComponentType<P>,
  options: Omit<DataUpdaterProps, 'children' | 'widgetId'> = {}
) => {
  return React.forwardRef<any, P & { widgetId: string }>((props, ref) => {
    const { widgetId, ...componentProps } = props;
    
    return (
      <DataUpdater widgetId={widgetId} {...options}>
        <Component {...(componentProps as P)} ref={ref} />
      </DataUpdater>
    );
  });
};

// 数据更新钩子
export const useDataUpdater = (widgetId: string) => {
  const { realtimeData, dataUpdateAnimations } = useRealtimeContext();
  const [updateCount, setUpdateCount] = useState(0);
  const [lastUpdateTime, setLastUpdateTime] = useState<Date | null>(null);
  const [isUpdating, setIsUpdating] = useState(false);
  const previousDataRef = useRef<any>(null);

  useEffect(() => {
    const currentData = realtimeData[widgetId];
    const previousData = previousDataRef.current;

    if (currentData && JSON.stringify(currentData) !== JSON.stringify(previousData)) {
      setUpdateCount(prev => prev + 1);
      setLastUpdateTime(new Date());
      setIsUpdating(true);

      const timer = setTimeout(() => {
        setIsUpdating(false);
      }, 1000);

      previousDataRef.current = currentData;

      return () => clearTimeout(timer);
    }
  }, [realtimeData, widgetId]);

  useEffect(() => {
    const hasAnimation = dataUpdateAnimations.get(widgetId);
    if (hasAnimation) {
      setIsUpdating(true);
      const timer = setTimeout(() => {
        setIsUpdating(false);
      }, 1000);

      return () => clearTimeout(timer);
    }
  }, [dataUpdateAnimations, widgetId]);

  return {
    data: realtimeData[widgetId],
    isUpdating,
    updateCount,
    lastUpdateTime,
    hasNewData: updateCount > 0
  };
};

export default DataUpdater;