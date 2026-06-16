// @ts-nocheck
import React, { useState, useRef, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { 
  MoreVertical, 
  Maximize2, 
  Share, 
  Download, 
  RefreshCw,
  TrendingUp,
  TrendingDown,
  Minus,
  AlertCircle,
  CheckCircle,
  Clock
} from 'lucide-react';
import { Widget } from '@/hooks/dashboard/useDashboard';
import { WidgetContent } from '../Widgets/WidgetContent';
import { useTouchGesture, touchFeedback } from '@/utils/touchGestures';
import { useResponsive } from '@/hooks/useResponsive';

interface MobileWidgetCardProps {
  widget: Widget;
  realtimeData?: any;
  isLoading?: boolean;
  onAction?: (action: string, widgetId: string) => void;
  onLongPress?: (widgetId: string) => void;
  className?: string;
  size?: 'small' | 'medium' | 'large';
  showActions?: boolean;
}

const MobileWidgetCard: React.FC<MobileWidgetCardProps> = ({
  widget,
  realtimeData,
  isLoading = false,
  onAction,
  onLongPress,
  className = '',
  size = 'medium',
  showActions = true
}) => {
  const [showActionMenu, setShowActionMenu] = useState(false);
  const [isPressed, setIsPressed] = useState(false);
  const cardRef = useRef<HTMLDivElement>(null);
  const { orientation } = useResponsive();
  const { handleTouchStart, handleTouchMove, handleTouchEnd } = useTouchGesture();

  // Handle touch gestures
  const handleGesture = useCallback((result: any) => {
    if (result.type === 'longPress') {
      onLongPress?.(widget.id);
      setShowActionMenu(true);
      touchFeedback.vibrate([50, 100, 50]);
    } else if (result.type === 'tap') {
      if (showActionMenu) {
        setShowActionMenu(false);
      }
    }
  }, [widget.id, onLongPress, showActionMenu]);

  const handleTouchStartCard = useCallback((e: React.TouchEvent) => {
    setIsPressed(true);
    handleTouchStart(e, handleGesture);
    touchFeedback.addTapEffect(cardRef.current!);
  }, [handleTouchStart, handleGesture]);

  const handleTouchMoveCard = useCallback((e: React.TouchEvent) => {
    handleTouchMove(e, handleGesture);
  }, [handleTouchMove, handleGesture]);

  const handleTouchEndCard = useCallback((e: React.TouchEvent) => {
    setIsPressed(false);
    handleTouchEnd(e, handleGesture);
  }, [handleTouchEnd, handleGesture]);

  // Get widget status indicator
  const getStatusIndicator = () => {
    if (isLoading) {
      return <Clock className="h-3 w-3 text-yellow-500 animate-pulse" />;
    }
    
    if (realtimeData?.error) {
      return <AlertCircle className="h-3 w-3 text-red-500 dark:text-red-400" />;
    }
    
    if (realtimeData?.status === 'success') {
      return <CheckCircle className="h-3 w-3 text-green-500 dark:text-green-400" />;
    }
    
    return null;
  };

  // Get trend indicator
  const getTrendIndicator = () => {
    if (!realtimeData?.trend) return null;
    
    const { direction, value } = realtimeData.trend;
    
    if (direction === 'up') {
      return (
        <div className="flex items-center text-green-600 text-xs dark:text-green-400">
          <TrendingUp className="h-3 w-3 mr-1" />
          <span>+{value}%</span>
        </div>
      );
    } else if (direction === 'down') {
      return (
        <div className="flex items-center text-red-600 text-xs dark:text-red-400">
          <TrendingDown className="h-3 w-3 mr-1" />
          <span>-{value}%</span>
        </div>
      );
    } else {
      return (
        <div className="flex items-center text-gray-600 text-xs dark:text-gray-400">
          <Minus className="h-3 w-3 mr-1" />
          <span>{value}%</span>
        </div>
      );
    }
  };

  // Get card height based on size and orientation
  const getCardHeight = () => {
    const baseHeights = {
      small: orientation === 'landscape' ? 'h-32' : 'h-40',
      medium: orientation === 'landscape' ? 'h-40' : 'h-48',
      large: orientation === 'landscape' ? 'h-48' : 'h-64'
    };
    return baseHeights[size];
  };

  return (
    <div className="relative">
      <Card 
        ref={cardRef}
        className={`
          mobile-card touch-optimized tap-feedback transition-all duration-200
          ${getCardHeight()}
          ${isPressed ? 'scale-95 shadow-lg' : 'scale-100'}
          ${orientation === 'landscape' ? 'landscape-compact' : ''}
          ${className}
        `}
        onTouchStart={handleTouchStartCard}
        onTouchMove={handleTouchMoveCard}
        onTouchEnd={handleTouchEndCard}
      >
        <CardHeader className="pb-2 mobile-card-header">
          <div className="flex justify-between items-start">
            <div className="flex-1 min-w-0">
              <CardTitle className="text-sm font-medium truncate">
                {widget.title}
              </CardTitle>
              <div className="flex items-center space-x-2 mt-1">
                {getStatusIndicator()}
                {getTrendIndicator()}
                {widget.category && (
                  <Badge variant="outline" className="text-xs px-1 py-0">
                    {widget.category}
                  </Badge>
                )}
              </div>
            </div>
            
            {showActions && (
              <Button
                variant="ghost"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  setShowActionMenu(!showActionMenu);
                  touchFeedback.vibrate(10);
                }}
                className="h-6 w-6 p-0 ml-2 touch-optimized"
              >
                <MoreVertical className="h-3 w-3" />
              </Button>
            )}
          </div>
        </CardHeader>
        
        <CardContent className="mobile-card-content flex-1 overflow-hidden">
          {isLoading ? (
            <div className="mobile-loading h-full">
              <div className="mobile-loading-spinner"></div>
              <p className="text-xs text-gray-500 mt-2 dark:text-gray-400">鍔犺浇涓?..</p>
            </div>
          ) : (
            <WidgetContent
              widget={widget}
              realtimeData={realtimeData}
            />
          )}
        </CardContent>
        
        {/* Last updated indicator */}
        {realtimeData?.lastUpdated && (
          <div className="absolute bottom-2 right-2 text-xs text-gray-400 dark:text-gray-500">
            {new Date(realtimeData.lastUpdated).toLocaleTimeString()}
          </div>
        )}
      </Card>

      {/* Action Menu */}
      {showActionMenu && (
        <div className="absolute top-full right-0 mt-1 bg-white rounded-lg shadow-lg border z-50 min-w-32 dark:bg-gray-800">
          <div className="py-1">
            <button
              onClick={() => {
                onAction?.('fullscreen', widget.id);
                setShowActionMenu(false);
              }}
              className="w-full px-3 py-2 text-left text-sm hover:bg-gray-50 flex items-center space-x-2 touch-optimized dark:bg-gray-800/50 dark:hover:bg-gray-800"
            >
              <Maximize2 className="h-3 w-3" />
              <span>鍏ㄥ睆</span>
            </button>
            
            <button
              onClick={() => {
                onAction?.('share', widget.id);
                setShowActionMenu(false);
              }}
              className="w-full px-3 py-2 text-left text-sm hover:bg-gray-50 flex items-center space-x-2 touch-optimized dark:bg-gray-800/50 dark:hover:bg-gray-800"
            >
              <Share className="h-3 w-3" />
              <span>鍒嗕韩</span>
            </button>
            
            <button
              onClick={() => {
                onAction?.('export', widget.id);
                setShowActionMenu(false);
              }}
              className="w-full px-3 py-2 text-left text-sm hover:bg-gray-50 flex items-center space-x-2 touch-optimized dark:bg-gray-800/50 dark:hover:bg-gray-800"
            >
              <Download className="h-3 w-3" />
              <span>瀵煎嚭</span>
            </button>
            
            <button
              onClick={() => {
                onAction?.('refresh', widget.id);
                setShowActionMenu(false);
              }}
              className="w-full px-3 py-2 text-left text-sm hover:bg-gray-50 flex items-center space-x-2 touch-optimized dark:bg-gray-800/50 dark:hover:bg-gray-800"
            >
              <RefreshCw className="h-3 w-3" />
              <span>鍒锋柊</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default MobileWidgetCard;