import React, { useEffect, useRef, useState } from 'react';

import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { useMeetingRoomStore } from '@/stores/meeting/meetingRoomStore';

interface Stroke {
  id: string;
  points: Array<[number, number]>;
}

const Whiteboard: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const drawingRef = useRef<Stroke | null>(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const whiteboardData = useMeetingRoomStore((s) => s.whiteboardData);
  const whiteboardConnected = useMeetingRoomStore((s) => s.whiteboardConnected);
  const connectWhiteboard = useMeetingRoomStore((s) => s.connectWhiteboard);
  const syncWhiteboardEvent = useMeetingRoomStore((s) => s.syncWhiteboardEvent);

  const strokes: Stroke[] = (whiteboardData?.strokes ?? []) as Stroke[];

  useEffect(() => {
    void connectWhiteboard();
  }, [connectWhiteboard]);

  // 重绘画布
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.lineWidth = 2;
    ctx.strokeStyle = '#2563eb';
    ctx.lineCap = 'round';
    for (const stroke of strokes) {
      if (stroke.points.length < 2) continue;
      ctx.beginPath();
      ctx.moveTo(stroke.points[0][0], stroke.points[0][1]);
      for (const [x, y] of stroke.points.slice(1)) ctx.lineTo(x, y);
      ctx.stroke();
    }
    // 正在画的一笔也画出来
    if (drawingRef.current && drawingRef.current.points.length >= 2) {
      const pts = drawingRef.current.points;
      ctx.beginPath();
      ctx.moveTo(pts[0][0], pts[0][1]);
      for (const [x, y] of pts.slice(1)) ctx.lineTo(x, y);
      ctx.stroke();
    }
  }, [strokes, isDrawing]);

  const pointOf = (e: React.PointerEvent<HTMLCanvasElement>): [number, number] => {
    const rect = canvasRef.current!.getBoundingClientRect();
    return [e.clientX - rect.left, e.clientY - rect.top];
  };

  const onPointerDown = (e: React.PointerEvent<HTMLCanvasElement>) => {
    drawingRef.current = { id: `s-${Date.now()}`, points: [pointOf(e)] };
    setIsDrawing(true);
  };

  const onPointerMove = (e: React.PointerEvent<HTMLCanvasElement>) => {
    if (!drawingRef.current) return;
    drawingRef.current.points.push(pointOf(e));
    setIsDrawing((v) => !v ? true : v);
    // 直接在画布上补画，避免等状态刷新
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    const pts = drawingRef.current.points;
    if (ctx && pts.length >= 2) {
      ctx.lineWidth = 2;
      ctx.strokeStyle = '#2563eb';
      ctx.lineCap = 'round';
      ctx.beginPath();
      ctx.moveTo(pts[pts.length - 2][0], pts[pts.length - 2][1]);
      ctx.lineTo(pts[pts.length - 1][0], pts[pts.length - 1][1]);
      ctx.stroke();
    }
  };

  const onPointerUp = () => {
    if (!drawingRef.current) return;
    const stroke = drawingRef.current;
    drawingRef.current = null;
    setIsDrawing(false);
    if (stroke.points.length >= 2) {
      syncWhiteboardEvent({ action_type: 'draw', data: stroke });
    }
  };

  const clear = () => {
    syncWhiteboardEvent({ action_type: 'clear', data: {} });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between text-base">
          <span>白板{whiteboardConnected ? '' : '（未连接）'}</span>
          <Button type="button" size="sm" variant="outline" onClick={clear}>清空</Button>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <canvas
          ref={canvasRef}
          width={640}
          height={320}
          className="h-64 w-full cursor-crosshair touch-none rounded-md border bg-white"
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerLeave={onPointerUp}
        />
        <div className="mt-2 text-xs text-muted-foreground">
          在画布上拖动绘制，松开即同步到后端（{strokes.length} 笔）。白板状态只存后端进程内存，重启即丢。
        </div>
      </CardContent>
    </Card>
  );
};

export default Whiteboard;
