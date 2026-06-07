import React, { useState, useCallback, useMemo, useRef, useEffect } from 'react';
import { DragDropContext, Droppable, Draggable, DropResult } from '@hello-pangea/dnd';
import GridItem from './GridItem';
import ResizeHandle from './ResizeHandle';
import { Widget } from '@/hooks/dashboard/useDashboard';
import './DashboardGrid.css';

interface GridLayoutProps {
  widgets: Widget[];
  editMode: boolean;
  onLayoutChange: (layout: any) => void;
  onRemoveWidget: (widgetId: string) => void;
  onUpdateWidget: (widgetId: string, updates: Partial<Widget>) => void;
  realtimeData?: any;
  cols?: number;
  rowHeight?: number;
  margin?: [number, number];
  className?: string;
}

interface GridPosition {
  x: number;
  y: number;
  w: number;
  h: number;
}

const DashboardGrid: React.FC<GridLayoutProps> = ({
  widgets,
  editMode,
  onLayoutChange,
  onRemoveWidget,
  onUpdateWidget,
  realtimeData = {},
  cols = 12,
  rowHeight = 60,
  margin = [16, 16],
  className = ''
}) => {
  const [draggedItem, setDraggedItem] = useState<string | null>(null);
  const [resizingItem, setResizingItem] = useState<string | null>(null);
  const [gridWidth, setGridWidth] = useState(1200);
  const [isDragging, setIsDragging] = useState(false);
  const [dragPreview, setDragPreview] = useState<{ x: number; y: number; w: number; h: number } | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [breakpoint, setBreakpoint] = useState<'xs' | 'sm' | 'md' | 'lg' | 'xl'>('lg');

  // Responsive breakpoints
  const breakpoints = useMemo(() => ({
    xs: { cols: 1, width: 480 },
    sm: { cols: 2, width: 640 },
    md: { cols: 4, width: 768 },
    lg: { cols: 6, width: 1024 },
    xl: { cols: 12, width: 1280 }
  }), []);

  // Get responsive columns
  const responsiveCols = useMemo(() => {
    return breakpoints[breakpoint].cols;
  }, [breakpoint, breakpoints]);

  // Calculate grid item dimensions
  const colWidth = useMemo(() => {
    return (gridWidth - margin[0] * (responsiveCols - 1)) / responsiveCols;
  }, [gridWidth, responsiveCols, margin]);

  // Convert widgets to grid layout format with responsive adjustments
  const layoutItems = useMemo(() => {
    return widgets.map(widget => {
      // Adjust widget size for smaller screens
      const adjustedW = Math.min(widget.position.w, responsiveCols);
      const adjustedX = Math.min(widget.position.x, responsiveCols - adjustedW);
      
      return {
        i: widget.id,
        x: adjustedX,
        y: widget.position.y,
        w: adjustedW,
        h: widget.position.h,
        minW: breakpoint === 'xs' ? 1 : 2,
        minH: 2,
        maxW: responsiveCols,
        maxH: 12
      };
    });
  }, [widgets, responsiveCols, breakpoint]);

  // Handle drag start
  const handleDragStart = useCallback((start: any) => {
    if (!editMode) return;
    
    setIsDragging(true);
    setDraggedItem(start.draggableId);
    
    const widget = widgets.find(w => w.id === start.draggableId);
    if (widget) {
      setDragPreview({
        x: widget.position.x,
        y: widget.position.y,
        w: widget.position.w,
        h: widget.position.h
      });
    }
  }, [editMode, widgets]);

  // Handle drag update for visual feedback
  const handleDragUpdate = useCallback((update: any) => {
    if (!editMode || !update.destination) return;

    const { destination, draggableId } = update;
    const widget = widgets.find(w => w.id === draggableId);
    if (!widget) return;

    // Calculate new position based on mouse position
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;

    const mouseX = update.destination.x - rect.left;
    const mouseY = update.destination.y - rect.top;

    const newX = Math.floor(mouseX / (colWidth + margin[0]));
    const newY = Math.floor(mouseY / (rowHeight + margin[1]));

    const clampedX = Math.max(0, Math.min(newX, responsiveCols - widget.position.w));
    const clampedY = Math.max(0, newY);

    setDragPreview({
      x: clampedX,
      y: clampedY,
      w: widget.position.w,
      h: widget.position.h
    });
  }, [editMode, widgets, colWidth, rowHeight, margin, responsiveCols]);

  // Handle drag end
  const handleDragEnd = useCallback((result: DropResult) => {
    setIsDragging(false);
    setDragPreview(null);
    
    if (!result.destination || !editMode) {
      setDraggedItem(null);
      return;
    }

    const { draggableId } = result;
    const widget = widgets.find(w => w.id === draggableId);
    if (!widget || !dragPreview) {
      setDraggedItem(null);
      return;
    }

    // Use the preview position or calculate from destination
    let newPosition = dragPreview;

    // Check for collisions and adjust position
    const finalPosition = findAvailablePosition(
      newPosition,
      widgets.filter(w => w.id !== draggableId)
    );

    // Compact layout after move
    const compactedLayout = compactLayout(
      widgets.map(w => 
        w.id === draggableId 
          ? { ...w, position: finalPosition }
          : w
      )
    );

    // Update widget position
    const updatedWidget = compactedLayout.find(w => w.id === draggableId);
    if (updatedWidget) {
      onUpdateWidget(draggableId, {
        position: updatedWidget.position
      });

      // Update all widgets if layout was compacted
      compactedLayout.forEach(w => {
        if (w.id !== draggableId) {
          onUpdateWidget(w.id, { position: w.position });
        }
      });

      // Notify parent of layout change
      const newLayout = compactedLayout.map(w => ({
        i: w.id,
        x: w.position.x,
        y: w.position.y,
        w: w.position.w,
        h: w.position.h
      }));
      onLayoutChange(newLayout);
    }

    setDraggedItem(null);
  }, [editMode, widgets, dragPreview, onUpdateWidget, onLayoutChange]);

  // Find available position without collisions
  const findAvailablePosition = useCallback((
    targetPos: GridPosition, 
    existingWidgets: Widget[]
  ): GridPosition => {
    let { x, y, w, h } = targetPos;

    // Ensure position is within bounds
    x = Math.max(0, Math.min(x, responsiveCols - w));
    y = Math.max(0, y);

    // Check for collisions and find next available spot
    let attempts = 0;
    const maxAttempts = responsiveCols * 20; // Prevent infinite loops

    while (hasCollision({ x, y, w, h }, existingWidgets) && attempts < maxAttempts) {
      x++;
      if (x + w > responsiveCols) {
        x = 0;
        y++;
      }
      attempts++;
    }

    return { x, y, w, h };
  }, [responsiveCols]);

  // Compact layout by moving widgets up to fill gaps
  const compactLayout = useCallback((widgets: Widget[]): Widget[] => {
    const sortedWidgets = [...widgets].sort((a, b) => {
      if (a.position.y !== b.position.y) {
        return a.position.y - b.position.y;
      }
      return a.position.x - b.position.x;
    });

    const compacted: Widget[] = [];

    for (const widget of sortedWidgets) {
      let newY = 0;
      let newX = widget.position.x;

      // Find the highest available position
      while (newY < widget.position.y) {
        const testPosition = { x: newX, y: newY, w: widget.position.w, h: widget.position.h };
        
        if (!hasCollision(testPosition, compacted)) {
          break;
        }
        
        newY++;
      }

      // If we can't fit at the original x position, try to find another spot
      if (hasCollision({ x: newX, y: newY, w: widget.position.w, h: widget.position.h }, compacted)) {
        const availablePos = findAvailablePosition(
          { x: 0, y: newY, w: widget.position.w, h: widget.position.h },
          compacted
        );
        newX = availablePos.x;
        newY = availablePos.y;
      }

      compacted.push({
        ...widget,
        position: { x: newX, y: newY, w: widget.position.w, h: widget.position.h }
      });
    }

    return compacted;
  }, [findAvailablePosition]);

  // Check if position collides with existing widgets
  const hasCollision = useCallback((
    pos: GridPosition, 
    existingWidgets: Widget[]
  ): boolean => {
    return existingWidgets.some(widget => {
      const wp = widget.position;
      return !(
        pos.x >= wp.x + wp.w ||
        pos.x + pos.w <= wp.x ||
        pos.y >= wp.y + wp.h ||
        pos.y + pos.h <= wp.y
      );
    });
  }, []);

  // Handle widget resize
  const handleResize = useCallback((
    widgetId: string, 
    newSize: { w: number; h: number }
  ) => {
    if (!editMode) return;

    const widget = widgets.find(w => w.id === widgetId);
    if (!widget) return;

    const minW = breakpoint === 'xs' ? 1 : 2;
    const newPosition = {
      ...widget.position,
      w: Math.max(minW, Math.min(newSize.w, responsiveCols)),
      h: Math.max(2, newSize.h)
    };

    // Ensure the resized widget doesn't go out of bounds
    if (newPosition.x + newPosition.w > responsiveCols) {
      newPosition.x = Math.max(0, responsiveCols - newPosition.w);
    }

    // Check for collisions with other widgets
    const otherWidgets = widgets.filter(w => w.id !== widgetId);
    if (hasCollision(newPosition, otherWidgets)) {
      // Try to push other widgets down
      const updatedWidgets = widgets.map(w => 
        w.id === widgetId ? { ...w, position: newPosition } : w
      );
      const compactedLayout = compactLayout(updatedWidgets);
      
      // Update all affected widgets
      compactedLayout.forEach(w => {
        onUpdateWidget(w.id, { position: w.position });
      });

      // Notify parent of layout change
      const newLayout = compactedLayout.map(w => ({
        i: w.id,
        x: w.position.x,
        y: w.position.y,
        w: w.position.w,
        h: w.position.h
      }));
      onLayoutChange(newLayout);
    } else {
      onUpdateWidget(widgetId, { position: newPosition });

      // Notify parent of layout change
      const newLayout = layoutItems.map(item => 
        item.i === widgetId 
          ? { ...item, w: newPosition.w, h: newPosition.h, x: newPosition.x }
          : item
      );
      onLayoutChange(newLayout);
    }
  }, [editMode, widgets, responsiveCols, breakpoint, layoutItems, onUpdateWidget, onLayoutChange, compactLayout]);

  // Calculate widget style based on position
  const getWidgetStyle = useCallback((widget: Widget) => {
    const { x, y, w, h } = widget.position;
    
    return {
      position: 'absolute' as const,
      left: x * (colWidth + margin[0]),
      top: y * (rowHeight + margin[1]),
      width: w * colWidth + (w - 1) * margin[0],
      height: h * rowHeight + (h - 1) * margin[1],
      transition: draggedItem === widget.id || resizingItem === widget.id 
        ? 'none' 
        : 'all 0.2s ease-in-out'
    };
  }, [colWidth, rowHeight, margin, draggedItem, resizingItem]);

  // Calculate total grid height
  const gridHeight = useMemo(() => {
    if (widgets.length === 0) return 400;
    
    const maxY = Math.max(...widgets.map(w => w.position.y + w.position.h));
    return maxY * (rowHeight + margin[1]) + margin[1];
  }, [widgets, rowHeight, margin]);

  // Handle container resize and breakpoint detection
  useEffect(() => {
    const handleResize = () => {
      if (containerRef.current) {
        const width = containerRef.current.clientWidth;
        setGridWidth(width);

        // Determine breakpoint
        let newBreakpoint: 'xs' | 'sm' | 'md' | 'lg' | 'xl' = 'xs';
        if (width >= breakpoints.xl.width) {
          newBreakpoint = 'xl';
        } else if (width >= breakpoints.lg.width) {
          newBreakpoint = 'lg';
        } else if (width >= breakpoints.md.width) {
          newBreakpoint = 'md';
        } else if (width >= breakpoints.sm.width) {
          newBreakpoint = 'sm';
        }

        if (newBreakpoint !== breakpoint) {
          setBreakpoint(newBreakpoint);
          
          // Recompact layout for new breakpoint
          if (widgets.length > 0) {
            const compactedLayout = compactLayout(widgets);
            compactedLayout.forEach(w => {
              onUpdateWidget(w.id, { position: w.position });
            });
          }
        }
      }
    };

    handleResize();
    
    const resizeObserver = new ResizeObserver(handleResize);
    if (containerRef.current) {
      resizeObserver.observe(containerRef.current);
    }

    return () => {
      resizeObserver.disconnect();
    };
  }, [breakpoint, breakpoints, widgets, compactLayout, onUpdateWidget]);

  if (!editMode) {
    // Static layout for view mode
    return (
      <div 
        ref={containerRef}
        className={`dashboard-grid-container relative ${className}`}
        style={{ height: gridHeight, minHeight: 400 }}
      >
        {widgets.map(widget => (
          <div
            key={widget.id}
            style={getWidgetStyle(widget)}
            className="dashboard-grid-item transition-all duration-300 hover:shadow-lg"
          >
            <GridItem
              widget={widget}
              editMode={false}
              onRemove={() => {}}
              onUpdate={() => {}}
              realtimeData={realtimeData[widget.type]}
            />
          </div>
        ))}
        
        {/* Responsive indicator */}
        {process.env.NODE_ENV === 'development' && (
          <div className="absolute top-2 right-2 bg-black/70 text-white text-xs px-2 py-1 rounded">
            {breakpoint} ({responsiveCols} cols)
          </div>
        )}
      </div>
    );
  }

  // Draggable layout for edit mode
  return (
    <DragDropContext 
      onDragStart={handleDragStart}
      onDragUpdate={handleDragUpdate}
      onDragEnd={handleDragEnd}
    >
      <Droppable droppableId="dashboard-grid" direction="horizontal">
        {(provided, snapshot) => (
          <div
            ref={useCallback((el: HTMLDivElement | null) => {
              provided.innerRef(el);
              if (containerRef.current !== el) {
                containerRef.current = el;
              }
            }, [provided.innerRef])}
            {...provided.droppableProps}
            className={`dashboard-grid-container relative transition-colors duration-200 ${
              snapshot.isDraggingOver ? 'bg-blue-50 dark:bg-blue-900/20' : ''
            } ${className}`}
            style={{ height: gridHeight, minHeight: 400 }}
          >
            {/* Grid background */}
            {editMode && (
              <div className="absolute inset-0 pointer-events-none">
                <svg width="100%" height="100%" className="opacity-10 dark:opacity-5">
                  <defs>
                    <pattern
                      id="grid"
                      width={colWidth + margin[0]}
                      height={rowHeight + margin[1]}
                      patternUnits="userSpaceOnUse"
                    >
                      <path
                        d={`M ${colWidth + margin[0]} 0 L 0 0 0 ${rowHeight + margin[1]}`}
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1"
                        className="text-gray-300 dark:text-gray-600"
                      />
                    </pattern>
                  </defs>
                  <rect width="100%" height="100%" fill="url(#grid)" />
                </svg>
              </div>
            )}

            {/* Drag preview */}
            {editMode && isDragging && dragPreview && (
              <div
                className="absolute border-2 border-dashed border-blue-400 bg-blue-100/50 dark:bg-blue-900/30 rounded-lg pointer-events-none z-10"
                style={{
                  left: dragPreview.x * (colWidth + margin[0]),
                  top: dragPreview.y * (rowHeight + margin[1]),
                  width: dragPreview.w * colWidth + (dragPreview.w - 1) * margin[0],
                  height: dragPreview.h * rowHeight + (dragPreview.h - 1) * margin[1],
                  transition: 'all 0.2s ease-out'
                }}
              >
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-blue-600 dark:text-blue-400 font-medium text-sm">
                    {dragPreview.w} × {dragPreview.h}
                  </span>
                </div>
              </div>
            )}

            {widgets.map((widget, index) => (
              <Draggable
                key={widget.id}
                draggableId={widget.id}
                index={index}
                isDragDisabled={!editMode}
              >
                {(provided, snapshot) => (
                  <div
                    ref={provided.innerRef}
                    {...provided.draggableProps}
                    style={{
                      ...getWidgetStyle(widget),
                      ...provided.draggableProps.style,
                      zIndex: snapshot.isDragging ? 1000 : draggedItem === widget.id ? 10 : 1
                    }}
                    className={`dashboard-grid-item transition-all duration-200 ${
                      snapshot.isDragging 
                        ? 'shadow-2xl scale-105 rotate-1' 
                        : draggedItem === widget.id 
                          ? 'shadow-lg ring-2 ring-blue-300 dark:ring-blue-600' 
                          : 'shadow-sm hover:shadow-md'
                    } ${
                      editMode ? 'cursor-move' : 'cursor-default'
                    }`}
                    onMouseEnter={() => editMode && setDraggedItem(widget.id)}
                    onMouseLeave={() => setDraggedItem(null)}
                  >
                    <GridItem
                      widget={widget}
                      editMode={editMode}
                      onRemove={onRemoveWidget}
                      onUpdate={onUpdateWidget}
                      realtimeData={realtimeData[widget.type]}
                      dragHandleProps={provided.dragHandleProps}
                    />
                    
                    {/* Resize handle */}
                    {editMode && (
                      <ResizeHandle
                        onResize={(newSize: { w: number; h: number }) => handleResize(widget.id, newSize)}
                        onResizeStart={() => setResizingItem(widget.id)}
                        onResizeEnd={() => setResizingItem(null)}
                        currentSize={{
                          w: widget.position.w,
                          h: widget.position.h
                        }}
                        minSize={{ w: breakpoint === 'xs' ? 1 : 2, h: 2 }}
                        maxSize={{ w: responsiveCols, h: 12 }}
                        colWidth={colWidth}
                        rowHeight={rowHeight}
                      />
                    )}
                  </div>
                )}
              </Draggable>
            ))}
            
            {provided.placeholder}
          </div>
        )}
      </Droppable>
    </DragDropContext>
  );
};

export default DashboardGrid;