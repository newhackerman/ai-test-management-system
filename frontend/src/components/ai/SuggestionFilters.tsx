/**
 * 建议过滤器组件
 * 
 * 功能特性：
 * - 状态筛选
 * - 类型筛选
 * - 优先级筛选
 * - 日期范围筛选
 * - 搜索功能
 * - 快速过滤预设
 */
import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Label } from '../ui/Label';
import { Checkbox } from '../ui/Checkbox';
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/Select';
import { 
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '../ui/Popover';
import { Calendar } from '../ui/Calendar';
import { 
  Search, 
  Filter, 
  X, 
  Calendar as CalendarIcon,
  RotateCcw
} from 'lucide-react';
import { 
  SuggestionFilters as FilterType, 
  SuggestionStatus, 
  SuggestionType, 
  SuggestionPriority 
} from '../../types/ai-assistant';
import { cn } from '../../lib/utils';
import { format } from 'date-fns';
import { zhCN } from 'date-fns/locale';

interface SuggestionFiltersProps {
  filters: FilterType;
  onFiltersChange: (filters: FilterType) => void;
  className?: string;
}

const statusOptions = [
  { value: SuggestionStatus.PENDING, label: '待处理', color: 'text-yellow-600' },
  { value: SuggestionStatus.ACCEPTED, label: '已接受', color: 'text-green-600' },
  { value: SuggestionStatus.REJECTED, label: '已拒绝', color: 'text-red-600' },
  { value: SuggestionStatus.IMPLEMENTED, label: '已实施', color: 'text-blue-600' },
  { value: SuggestionStatus.CANCELLED, label: '已取消', color: 'text-gray-600' }
];

const typeOptions = [
  { value: SuggestionType.OPTIMIZATION, label: '优化建议', color: 'text-purple-600' },
  { value: SuggestionType.IMPROVEMENT, label: '改进建议', color: 'text-green-600' },
  { value: SuggestionType.RISK_MITIGATION, label: '风险缓解', color: 'text-red-600' },
  { value: SuggestionType.QUALITY_ENHANCEMENT, label: '质量提升', color: 'text-blue-600' },
  { value: SuggestionType.PROCESS_IMPROVEMENT, label: '流程改进', color: 'text-indigo-600' }
];

const priorityOptions = [
  { value: SuggestionPriority.LOW, label: '低', color: 'text-gray-600' },
  { value: SuggestionPriority.MEDIUM, label: '中', color: 'text-blue-600' },
  { value: SuggestionPriority.HIGH, label: '高', color: 'text-orange-600' },
  { value: SuggestionPriority.CRITICAL, label: '紧急', color: 'text-red-600' }
];

const quickFilters = [
  {
    name: '待处理',
    filters: { status: [SuggestionStatus.PENDING] }
  },
  {
    name: '高优先级',
    filters: { priority: [SuggestionPriority.HIGH, SuggestionPriority.CRITICAL] }
  },
  {
    name: '已实施',
    filters: { status: [SuggestionStatus.IMPLEMENTED] }
  },
  {
    name: '最近7天',
    filters: { 
      date_from: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
    }
  }
];

export function SuggestionFilters({ 
  filters, 
  onFiltersChange, 
  className 
}: SuggestionFiltersProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [searchText, setSearchText] = useState(filters.search_text || '');
  const [dateFromOpen, setDateFromOpen] = useState(false);
  const [dateToOpen, setDateToOpen] = useState(false);

  // 搜索防抖
  useEffect(() => {
    const timer = setTimeout(() => {
      if (searchText !== filters.search_text) {
        onFiltersChange({
          ...filters,
          search_text: searchText || undefined
        });
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [searchText, filters, onFiltersChange]);

  const handleStatusChange = (status: SuggestionStatus, checked: boolean) => {
    const currentStatus = filters.status || [];
    const newStatus = checked
      ? [...currentStatus, status]
      : currentStatus.filter(s => s !== status);
    
    onFiltersChange({
      ...filters,
      status: newStatus.length > 0 ? newStatus : undefined
    });
  };

  const handleTypeChange = (type: SuggestionType, checked: boolean) => {
    const currentTypes = filters.type || [];
    const newTypes = checked
      ? [...currentTypes, type]
      : currentTypes.filter(t => t !== type);
    
    onFiltersChange({
      ...filters,
      type: newTypes.length > 0 ? newTypes : undefined
    });
  };

  const handlePriorityChange = (priority: SuggestionPriority, checked: boolean) => {
    const currentPriorities = filters.priority || [];
    const newPriorities = checked
      ? [...currentPriorities, priority]
      : currentPriorities.filter(p => p !== priority);
    
    onFiltersChange({
      ...filters,
      priority: newPriorities.length > 0 ? newPriorities : undefined
    });
  };

  const handleDateFromChange = (date: Date | undefined) => {
    onFiltersChange({
      ...filters,
      date_from: date ? date.toISOString().split('T')[0] : undefined
    });
    setDateFromOpen(false);
  };

  const handleDateToChange = (date: Date | undefined) => {
    onFiltersChange({
      ...filters,
      date_to: date ? date.toISOString().split('T')[0] : undefined
    });
    setDateToOpen(false);
  };

  const handleQuickFilter = (quickFilter: typeof quickFilters[0]) => {
    onFiltersChange({
      ...filters,
      ...quickFilter.filters
    });
  };

  const clearFilters = () => {
    setSearchText('');
    onFiltersChange({});
  };

  const hasActiveFilters = Object.keys(filters).some(key => {
    const value = filters[key as keyof FilterType];
    return value !== undefined && value !== null && 
           (Array.isArray(value) ? value.length > 0 : true);
  });

  const activeFilterCount = Object.keys(filters).filter(key => {
    const value = filters[key as keyof FilterType];
    return value !== undefined && value !== null && 
           (Array.isArray(value) ? value.length > 0 : true);
  }).length;

  return (
    <Card className={className}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold flex items-center gap-2">
            <Filter className="w-5 h-5" />
            筛选条件
            {activeFilterCount > 0 && (
              <span className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded-full">
                {activeFilterCount}
              </span>
            )}
          </CardTitle>
          
          <div className="flex items-center gap-2">
            {hasActiveFilters && (
              <Button
                variant="ghost"
                size="sm"
                onClick={clearFilters}
                className="text-gray-500 hover:text-gray-700"
              >
                <RotateCcw className="w-4 h-4 mr-1" />
                清空
              </Button>
            )}
            
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsExpanded(!isExpanded)}
            >
              {isExpanded ? '收起' : '展开'}
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* 搜索框 */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
          <Input
            placeholder="搜索建议标题或描述..."
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            className="pl-10"
          />
          {searchText && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSearchText('')}
              className="absolute right-1 top-1/2 transform -translate-y-1/2 h-6 w-6 p-0"
            >
              <X className="w-4 h-4" />
            </Button>
          )}
        </div>

        {/* 快速筛选 */}
        <div>
          <Label className="text-sm font-medium text-gray-700 mb-2 block">
            快速筛选
          </Label>
          <div className="flex flex-wrap gap-2">
            {quickFilters.map((quickFilter) => (
              <Button
                key={quickFilter.name}
                variant="outline"
                size="sm"
                onClick={() => handleQuickFilter(quickFilter)}
                className="text-xs"
              >
                {quickFilter.name}
              </Button>
            ))}
          </div>
        </div>

        {/* 展开的筛选选项 */}
        {isExpanded && (
          <div className="space-y-4 border-t pt-4">
            {/* 状态筛选 */}
            <div>
              <Label className="text-sm font-medium text-gray-700 mb-2 block">
                状态
              </Label>
              <div className="grid grid-cols-2 gap-2">
                {statusOptions.map((option) => (
                  <div key={option.value} className="flex items-center space-x-2">
                    <Checkbox
                      id={`status-${option.value}`}
                      checked={filters.status?.includes(option.value) || false}
                      onCheckedChange={(checked) => 
                        handleStatusChange(option.value, checked as boolean)
                      }
                    />
                    <Label
                      htmlFor={`status-${option.value}`}
                      className={cn("text-sm cursor-pointer", option.color)}
                    >
                      {option.label}
                    </Label>
                  </div>
                ))}
              </div>
            </div>

            {/* 类型筛选 */}
            <div>
              <Label className="text-sm font-medium text-gray-700 mb-2 block">
                类型
              </Label>
              <div className="grid grid-cols-2 gap-2">
                {typeOptions.map((option) => (
                  <div key={option.value} className="flex items-center space-x-2">
                    <Checkbox
                      id={`type-${option.value}`}
                      checked={filters.type?.includes(option.value) || false}
                      onCheckedChange={(checked) => 
                        handleTypeChange(option.value, checked as boolean)
                      }
                    />
                    <Label
                      htmlFor={`type-${option.value}`}
                      className={cn("text-sm cursor-pointer", option.color)}
                    >
                      {option.label}
                    </Label>
                  </div>
                ))}
              </div>
            </div>

            {/* 优先级筛选 */}
            <div>
              <Label className="text-sm font-medium text-gray-700 mb-2 block">
                优先级
              </Label>
              <div className="grid grid-cols-2 gap-2">
                {priorityOptions.map((option) => (
                  <div key={option.value} className="flex items-center space-x-2">
                    <Checkbox
                      id={`priority-${option.value}`}
                      checked={filters.priority?.includes(option.value) || false}
                      onCheckedChange={(checked) => 
                        handlePriorityChange(option.value, checked as boolean)
                      }
                    />
                    <Label
                      htmlFor={`priority-${option.value}`}
                      className={cn("text-sm cursor-pointer", option.color)}
                    >
                      {option.label}
                    </Label>
                  </div>
                ))}
              </div>
            </div>

            {/* 日期范围筛选 */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-sm font-medium text-gray-700 mb-2 block">
                  开始日期
                </Label>
                <Popover open={dateFromOpen} onOpenChange={setDateFromOpen}>
                  <PopoverTrigger asChild>
                    <Button
                      variant="outline"
                      className={cn(
                        "w-full justify-start text-left font-normal",
                        !filters.date_from && "text-muted-foreground"
                      )}
                    >
                      <CalendarIcon className="mr-2 h-4 w-4" />
                      {filters.date_from ? (
                        format(new Date(filters.date_from), "PPP", { locale: zhCN })
                      ) : (
                        "选择日期"
                      )}
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-auto p-0" align="start">
                    <Calendar
                      mode="single"
                      selected={filters.date_from ? new Date(filters.date_from) : undefined}
                      onSelect={handleDateFromChange}
                      initialFocus
                    />
                  </PopoverContent>
                </Popover>
              </div>

              <div>
                <Label className="text-sm font-medium text-gray-700 mb-2 block">
                  结束日期
                </Label>
                <Popover open={dateToOpen} onOpenChange={setDateToOpen}>
                  <PopoverTrigger asChild>
                    <Button
                      variant="outline"
                      className={cn(
                        "w-full justify-start text-left font-normal",
                        !filters.date_to && "text-muted-foreground"
                      )}
                    >
                      <CalendarIcon className="mr-2 h-4 w-4" />
                      {filters.date_to ? (
                        format(new Date(filters.date_to), "PPP", { locale: zhCN })
                      ) : (
                        "选择日期"
                      )}
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-auto p-0" align="start">
                    <Calendar
                      mode="single"
                      selected={filters.date_to ? new Date(filters.date_to) : undefined}
                      onSelect={handleDateToChange}
                      initialFocus
                    />
                  </PopoverContent>
                </Popover>
              </div>
            </div>

            {/* 其他筛选选项 */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-sm font-medium text-gray-700 mb-2 block">
                  项目ID
                </Label>
                <Input
                  type="number"
                  placeholder="输入项目ID"
                  value={filters.project_id || ''}
                  onChange={(e) => onFiltersChange({
                    ...filters,
                    project_id: e.target.value ? parseInt(e.target.value) : undefined
                  })}
                />
              </div>

              <div>
                <Label className="text-sm font-medium text-gray-700 mb-2 block">
                  最低评分
                </Label>
                <Select
                  value={filters.min_rating?.toString() || ''}
                  onValueChange={(value) => onFiltersChange({
                    ...filters,
                    min_rating: value ? parseInt(value) : undefined
                  })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="选择最低评分" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">不限</SelectItem>
                    <SelectItem value="1">1星及以上</SelectItem>
                    <SelectItem value="2">2星及以上</SelectItem>
                    <SelectItem value="3">3星及以上</SelectItem>
                    <SelectItem value="4">4星及以上</SelectItem>
                    <SelectItem value="5">5星</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* 布尔筛选选项 */}
            <div className="space-y-2">
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="has-feedback"
                  checked={filters.has_feedback || false}
                  onCheckedChange={(checked) => onFiltersChange({
                    ...filters,
                    has_feedback: checked as boolean || undefined
                  })}
                />
                <Label htmlFor="has-feedback" className="text-sm cursor-pointer">
                  有用户反馈
                </Label>
              </div>

              <div className="flex items-center space-x-2">
                <Checkbox
                  id="implemented"
                  checked={filters.implemented || false}
                  onCheckedChange={(checked) => onFiltersChange({
                    ...filters,
                    implemented: checked as boolean || undefined
                  })}
                />
                <Label htmlFor="implemented" className="text-sm cursor-pointer">
                  已实施
                </Label>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}