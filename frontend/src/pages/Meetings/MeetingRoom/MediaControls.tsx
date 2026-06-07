import React, { useState } from 'react';
import { Mic, MicOff, Video, VideoOff } from 'lucide-react';

import { Button } from '@/components/ui/Button';

const MediaControls: React.FC = () => {
  const [audio, setAudio] = useState(true);
  const [video, setVideo] = useState(true);
  return (
    <div className="flex gap-2">
      <Button type="button" variant="outline" onClick={() => setAudio((prev) => !prev)}>{audio ? <Mic className="h-4 w-4" /> : <MicOff className="h-4 w-4" />}</Button>
      <Button type="button" variant="outline" onClick={() => setVideo((prev) => !prev)}>{video ? <Video className="h-4 w-4" /> : <VideoOff className="h-4 w-4" />}</Button>
    </div>
  );
};

export default MediaControls;
