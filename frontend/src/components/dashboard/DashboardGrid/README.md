# DashboardGrid Component

A powerful, responsive drag-and-drop grid layout component for dashboard widgets with advanced features like collision detection, layout compaction, and responsive breakpoints.

## Features

- ✅ **Drag and Drop**: Full drag-and-drop support using `@hello-pangea/dnd`
- ✅ **Responsive Design**: Automatic breakpoint detection and responsive column adjustment
- ✅ **Collision Detection**: Advanced collision detection with automatic layout compaction
- ✅ **Resize Handles**: Interactive resize handles for widgets in edit mode
- ✅ **Layout Constraints**: Configurable minimum/maximum sizes and grid boundaries
- ✅ **Visual Feedback**: Drag preview, grid background, and smooth animations
- ✅ **Touch Support**: Full touch device support for mobile and tablet
- ✅ **Accessibility**: ARIA labels, keyboard navigation, and high contrast support
- ✅ **Performance**: Optimized rendering with ResizeObserver and efficient updates

## Usage

```tsx
import DashboardGrid from '@/components/dashboard/DashboardGrid';
import { Widget } from '@/hooks/dashboard/useDashboard';

const widgets: Widget[] = [
  {
    id: 'widget-1',
    type: 'stat_card',
    title: 'Total Users',
    config: { refreshInterval: 30 },
    position: { x: 0, y: 0, w: 4, h: 3 }
  },
  {
    id: 'widget-2',
    type: 'line_chart',
    title: 'Revenue Trend',
    config: { refreshInterval: 60 },
    position: { x: 4, y: 0, w: 8, h: 4 }
  }
];

function MyDashboard() {
  const [editMode, setEditMode] = useState(false);
  const [realtimeData, setRealtimeData] = useState({});

  const handleLayoutChange = (layout: any) => {
    console.log('Layout changed:', layout);
    // Save layout to backend
  };

  const handleRemoveWidget = (widgetId: string) => {
    console.log('Remove widget:', widgetId);
    // Remove widget logic
  };

  const handleUpdateWidget = (widgetId: string, updates: Partial<Widget>) => {
    console.log('Update widget:', widgetId, updates);
    // Update widget logic
  };

  return (
    <DashboardGrid
      widgets={widgets}
      editMode={editMode}
      onLayoutChange={handleLayoutChange}
      onRemoveWidget={handleRemoveWidget}
      onUpdateWidget={handleUpdateWidget}
      realtimeData={realtimeData}
      cols={12}
      rowHeight={60}
      margin={[16, 16]}
      className="my-dashboard"
    />
  );
}
```

## Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `widgets` | `Widget[]` | `[]` | Array of widget objects to display |
| `editMode` | `boolean` | `false` | Enable/disable edit mode with drag-and-drop |
| `onLayoutChange` | `(layout: any) => void` | - | Callback when layout changes |
| `onRemoveWidget` | `(widgetId: string) => void` | - | Callback when widget is removed |
| `onUpdateWidget` | `(widgetId: string, updates: Partial<Widget>) => void` | - | Callback when widget is updated |
| `realtimeData` | `Record<string, any>` | `{}` | Real-time data for widgets |
| `cols` | `number` | `12` | Number of columns in the grid |
| `rowHeight` | `number` | `60` | Height of each row in pixels |
| `margin` | `[number, number]` | `[16, 16]` | Margin between widgets [x, y] |
| `className` | `string` | `''` | Additional CSS class name |

## Widget Interface

```typescript
interface Widget {
  id: string;                    // Unique identifier
  type: string;                  // Widget type (stat_card, line_chart, etc.)
  title: string;                 // Display title
  config: any;                   // Widget-specific configuration
  position: {                    // Grid position and size
    x: number;                   // Column position (0-based)
    y: number;                   // Row position (0-based)
    w: number;                   // Width in columns
    h: number;                   // Height in rows
  };
  data?: any;                    // Widget data
}
```

## Responsive Breakpoints

The component automatically adjusts the number of columns based on container width:

| Breakpoint | Width | Columns |
|------------|-------|---------|
| `xs` | < 640px | 1 |
| `sm` | 640px - 768px | 2 |
| `md` | 768px - 1024px | 4 |
| `lg` | 1024px - 1280px | 6 |
| `xl` | ≥ 1280px | 12 |

## Layout Algorithm

### Collision Detection
The component uses a sophisticated collision detection algorithm that:
1. Checks for overlapping widgets when dragging or resizing
2. Finds the next available position if collision occurs
3. Prevents widgets from going outside grid boundaries

### Layout Compaction
After drag operations, the layout is automatically compacted:
1. Widgets are sorted by position (top-to-bottom, left-to-right)
2. Each widget is moved to the highest available position
3. Gaps are filled automatically while maintaining relative positions

### Responsive Adaptation
When breakpoints change:
1. Widget widths are clamped to fit new column count
2. Widget positions are adjusted to prevent overflow
3. Layout is recompacted for optimal space usage

## Styling

The component includes comprehensive CSS with support for:

- **Dark Mode**: Automatic dark mode support via CSS classes
- **Animations**: Smooth transitions for drag, resize, and layout changes
- **Touch Devices**: Larger touch targets and optimized interactions
- **High Contrast**: Support for high contrast accessibility mode
- **Reduced Motion**: Respects user's motion preferences

### CSS Classes

```css
.dashboard-grid-container     /* Main container */
.dashboard-grid-item         /* Individual widget container */
.dashboard-grid-item.dragging /* Widget being dragged */
.drag-preview               /* Drag preview overlay */
.resize-handle             /* Resize handle */
.grid-background          /* Grid background pattern */
```

## Performance Optimizations

1. **ResizeObserver**: Efficient container size monitoring
2. **Memoization**: Optimized calculations with useMemo and useCallback
3. **Virtualization**: Only renders visible widgets (planned)
4. **Debounced Updates**: Throttled layout change notifications
5. **Efficient Collision Detection**: Optimized algorithms for large grids

## Accessibility

- **ARIA Labels**: Proper labeling for screen readers
- **Keyboard Navigation**: Full keyboard support for drag and resize
- **Focus Management**: Proper focus handling during interactions
- **High Contrast**: Support for high contrast mode
- **Reduced Motion**: Respects prefers-reduced-motion setting

## Browser Support

- **Chrome**: 88+
- **Firefox**: 85+
- **Safari**: 14+
- **Edge**: 88+
- **Mobile**: iOS Safari 14+, Chrome Mobile 88+

## Development

### Running Tests

```bash
npm test -- --run GridLayout
```

### Building

The component is built with TypeScript and includes full type definitions.

### Contributing

1. Follow the existing code style
2. Add tests for new features
3. Update documentation
4. Ensure accessibility compliance

## Examples

### Basic Grid

```tsx
<DashboardGrid
  widgets={widgets}
  editMode={false}
  onLayoutChange={() => {}}
  onRemoveWidget={() => {}}
  onUpdateWidget={() => {}}
/>
```

### Editable Grid with Custom Styling

```tsx
<DashboardGrid
  widgets={widgets}
  editMode={true}
  onLayoutChange={handleLayoutChange}
  onRemoveWidget={handleRemoveWidget}
  onUpdateWidget={handleUpdateWidget}
  cols={16}
  rowHeight={80}
  margin={[20, 20]}
  className="custom-dashboard"
/>
```

### Mobile-Optimized Grid

```tsx
<DashboardGrid
  widgets={widgets}
  editMode={false}
  onLayoutChange={handleLayoutChange}
  onRemoveWidget={handleRemoveWidget}
  onUpdateWidget={handleUpdateWidget}
  cols={2}
  rowHeight={120}
  margin={[12, 12]}
  className="mobile-dashboard"
/>
```

## Troubleshooting

### Common Issues

1. **Widgets not dragging**: Ensure `editMode` is `true`
2. **Layout not saving**: Check `onLayoutChange` callback implementation
3. **Responsive issues**: Verify container has proper width constraints
4. **Performance issues**: Consider reducing widget count or implementing virtualization

### Debug Mode

Set `NODE_ENV=development` to see the breakpoint indicator and additional debug information.