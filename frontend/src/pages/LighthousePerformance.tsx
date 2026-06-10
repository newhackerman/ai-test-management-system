import React from 'react';
import { Activity, Gauge, Monitor, Smartphone } from 'lucide-react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Progress } from '@/components/ui/Progress';

export default function LighthousePerformance() {
  const metrics = [
    { label: 'Performance', value: 0, icon: <Gauge className="h-4 w-4" /> },
    { label: 'Accessibility', value: 0, icon: <Activity className="h-4 w-4" /> },
    { label: 'Desktop', value: 0, icon: <Monitor className="h-4 w-4" /> },
    { label: 'Mobile', value: 0, icon: <Smartphone className="h-4 w-4" /> },
  ];

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Lighthouse 性能</h1>
      </div>
      <div className="grid gap-4 md:grid-cols-4">
        {metrics.map((metric) => (
          <Card key={metric.label}>
            <CardHeader><CardTitle className="flex items-center gap-2 text-base">{metric.icon}{metric.label}</CardTitle></CardHeader>
            <CardContent className="space-y-2">
              <div className="text-2xl font-semibold">{metric.value}</div>
              <Progress value={metric.value} />
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
