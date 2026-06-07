import React, { useState } from 'react';
import { MonitorUp } from 'lucide-react';

import { Button } from '@/components/ui/Button';

interface ScreenShareProps {
  onShareStart?: () => void;
  onShareStop?: () => void;
}

const ScreenShare: React.FC<ScreenShareProps> = ({ onShareStart, onShareStop }) => {
  const [sharing, setSharing] = useState(false);
  const toggle = () => {
    setSharing((prev) => {
      if (prev) onShareStop?.(); else onShareStart?.();
      return !prev;
    });
  };
  return <Button type="button" variant="outline" onClick={toggle}><MonitorUp className="mr-2 h-4 w-4" />{sharing ? '停止共享' : '屏幕共享'}</Button>;
};

export default ScreenShare;
