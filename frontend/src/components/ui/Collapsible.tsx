/**
 * Collapsible 组件
 * 
 * 提供可折叠内容的组件，支持展开和收起功能
 */

import React, { createContext, useContext, useState } from 'react';
import { cn } from '@/lib/utils';

// Collapsible Context
interface CollapsibleContextType {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const CollapsibleContext = createContext<CollapsibleContextType | undefined>(undefined);

const useCollapsible = () => {
  const context = useContext(CollapsibleContext);
  if (!context) {
    throw new Error('useCollapsible must be used within a Collapsible');
  }
  return context;
};

// Collapsible Root Component
interface CollapsibleProps {
  children: React.ReactNode;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  defaultOpen?: boolean;
  disabled?: boolean;
  className?: string;
}

const Collapsible = React.forwardRef<HTMLDivElement, CollapsibleProps>(
  ({ children, open: controlledOpen, onOpenChange, defaultOpen = false, disabled = false, className, ...props }, ref) => {
    const [internalOpen, setInternalOpen] = useState(defaultOpen);
    
    const isControlled = controlledOpen !== undefined;
    const open = isControlled ? controlledOpen : internalOpen;
    
    const handleOpenChange = (newOpen: boolean) => {
      if (disabled) return;
      
      if (isControlled) {
        onOpenChange?.(newOpen);
      } else {
        setInternalOpen(newOpen);
        onOpenChange?.(newOpen);
      }
    };

    return (
      <CollapsibleContext.Provider value={{ open, onOpenChange: handleOpenChange }}>
        <div
          ref={ref}
          className={cn('', className)}
          data-state={open ? 'open' : 'closed'}
          data-disabled={disabled ? '' : undefined}
          {...props}
        >
          {children}
        </div>
      </CollapsibleContext.Provider>
    );
  }
);

Collapsible.displayName = 'Collapsible';

// Collapsible Trigger Component
interface CollapsibleTriggerProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  children: React.ReactNode;
  asChild?: boolean;
}

const CollapsibleTrigger = React.forwardRef<HTMLButtonElement, CollapsibleTriggerProps>(
  ({ children, asChild = false, className, onClick, ...props }, ref) => {
    const { open, onOpenChange } = useCollapsible();

    const handleClick = (event: React.MouseEvent<HTMLButtonElement>) => {
      onClick?.(event);
      onOpenChange(!open);
    };

    if (asChild) {
      // 如果 asChild 为 true，则将 props 传递给子元素
      return React.cloneElement(children as React.ReactElement, {
        onClick: handleClick,
        'data-state': open ? 'open' : 'closed',
        'aria-expanded': open,
        ...props
      });
    }

    return (
      <button
        ref={ref}
        type="button"
        className={cn(
          'flex w-full items-center justify-between py-4 font-medium transition-all hover:underline [&[data-state=open]>svg]:rotate-180',
          className
        )}
        data-state={open ? 'open' : 'closed'}
        aria-expanded={open}
        onClick={handleClick}
        {...props}
      >
        {children}
      </button>
    );
  }
);

CollapsibleTrigger.displayName = 'CollapsibleTrigger';

// Collapsible Content Component
interface CollapsibleContentProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  forceMount?: boolean;
}

const CollapsibleContent = React.forwardRef<HTMLDivElement, CollapsibleContentProps>(
  ({ children, className, forceMount = false, ...props }, ref) => {
    const { open } = useCollapsible();
    const [isPresent, setIsPresent] = useState(open || forceMount);

    React.useEffect(() => {
      if (open) {
        setIsPresent(true);
      } else {
        // 延迟隐藏以允许动画完成
        const timer = setTimeout(() => setIsPresent(false), 200);
        return () => clearTimeout(timer);
      }
    }, [open]);

    if (!isPresent && !forceMount) {
      return null;
    }

    return (
      <div
        ref={ref}
        className={cn(
          'overflow-hidden text-sm transition-all',
          open ? 'animate-collapsible-down' : 'animate-collapsible-up',
          className
        )}
        data-state={open ? 'open' : 'closed'}
        {...props}
      >
        <div className={open ? 'pb-4 pt-0' : ''}>
          {children}
        </div>
      </div>
    );
  }
);

CollapsibleContent.displayName = 'CollapsibleContent';

export { Collapsible, CollapsibleTrigger, CollapsibleContent };