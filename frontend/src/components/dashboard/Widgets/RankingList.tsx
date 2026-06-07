import React, { useMemo } from 'react';
import { Badge } from '@/components/ui/Badge';
import { Trophy, Medal, Award } from 'lucide-react';

interface RankingListProps {
  config: {
    title?: string;
    sortBy?: string;
    limit?: number;
  };
  data?: any;
}

const RankingList: React.FC<RankingListProps> = ({ config, data }) => {
  const { limit = 5 } = config;

  const rankings = useMemo(() => {
    if (data && Array.isArray(data)) {
      return data.slice(0, limit);
    }

    // Generate sample ranking data
    return [
      { name: '张三', value: 95, unit: '分', change: '+5' },
      { name: '李四', value: 88, unit: '分', change: '+2' },
      { name: '王五', value: 82, unit: '分', change: '-1' },
      { name: '赵六', value: 79, unit: '分', change: '+3' },
      { name: '钱七', value: 75, unit: '分', change: '0' }
    ].slice(0, limit);
  }, [data, limit]);

  const getRankIcon = (index: number) => {
    switch (index) {
      case 0:
        return <Trophy className="h-4 w-4 text-yellow-500" />;
      case 1:
        return <Medal className="h-4 w-4 text-gray-400" />;
      case 2:
        return <Award className="h-4 w-4 text-orange-500" />;
      default:
        return <span className="text-sm font-bold text-gray-500">#{index + 1}</span>;
    }
  };

  return (
    <div className="h-full">
      <div className="space-y-2">
        {rankings.map((item, index) => (
          <div key={index} className="flex items-center justify-between p-2 hover:bg-gray-50 rounded">
            <div className="flex items-center space-x-3">
              {getRankIcon(index)}
              <span className="text-sm font-medium">{item.name}</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="text-sm font-bold">{item.value}{item.unit}</span>
              {item.change && (
                <Badge 
                  variant="outline" 
                  className={`text-xs ${
                    item.change.startsWith('+') ? 'text-green-600' : 
                    item.change.startsWith('-') ? 'text-red-600' : 'text-gray-600'
                  }`}
                >
                  {item.change}
                </Badge>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default RankingList;