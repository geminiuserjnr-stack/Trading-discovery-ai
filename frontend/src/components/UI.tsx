import React from 'react';
import { AlertCircle, FolderOpen, RefreshCcw, Search } from 'lucide-react';

// Button Component
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'success' | 'outline';
  size?: 'xs' | 'sm' | 'md' | 'lg';
}
export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  className = '',
  ...props
}) => {
  const baseStyle = "font-mono font-bold uppercase tracking-wider rounded transition-colors focus:outline-none flex items-center justify-center gap-2";
  const variants = {
    primary: "bg-accentPrimary text-white hover:bg-accentPrimary/90",
    secondary: "bg-darkBorder text-darkText hover:bg-darkBorder/80",
    danger: "bg-accentDanger text-white hover:bg-accentDanger/90",
    success: "bg-accentSuccess text-white hover:bg-accentSuccess/90",
    outline: "border border-darkBorder hover:bg-darkBorder/40 text-darkText",
  };
  const sizes = {
    xs: "text-[10px] px-2 py-1",
    sm: "text-xs px-3 py-1.5",
    md: "text-xs px-4 py-2",
    lg: "text-sm px-6 py-2.5",
  };
  return (
    <button
      className={`${baseStyle} ${variants[variant]} ${sizes[size]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
};

// Metric Card Component
interface MetricCardProps {
  title: string;
  value: string | number;
  trend?: { text: string; positive: boolean };
  icon: React.ComponentType<any>;
  onClick?: () => void;
  sparkline?: number[];
}
export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  trend,
  icon: Icon,
  onClick,
  sparkline
}) => {
  return (
    <div
      onClick={onClick}
      className={`bg-darkCard border border-darkBorder rounded p-4 flex flex-col justify-between shadow-subtle ${
        onClick ? 'cursor-pointer hover:border-accentPrimary/50 transition-all' : ''
      }`}
    >
      <div className="flex items-start justify-between">
        <div className="flex flex-col gap-1">
          <span className="text-[10px] uppercase font-mono tracking-widest text-darkMuted">{title}</span>
          <span className="text-xl font-bold font-mono tracking-tight text-darkText">{value}</span>
        </div>
        <div className="p-2 rounded bg-darkBg border border-darkBorder/60 text-accentPrimary">
          <Icon size={16} />
        </div>
      </div>
      <div className="flex items-center justify-between mt-3">
        {trend ? (
          <span className={`text-[10px] font-semibold font-mono ${trend.positive ? 'text-accentSuccess' : 'text-accentDanger'}`}>
            {trend.text}
          </span>
        ) : (
          <span className="text-[10px] font-mono text-darkMuted">STABLE</span>
        )}
        {sparkline && (
          <div className="flex items-end gap-0.5 h-4">
            {sparkline.map((val, i) => (
              <div
                key={i}
                className="w-1 bg-accentPrimary/70 rounded-t"
                style={{ height: `${(val / Math.max(...sparkline)) * 100}%` }}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

// Status Badge Component
interface StatusBadgeProps {
  status: string;
  type?: 'primary' | 'success' | 'warning' | 'danger' | 'neutral';
}
export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, type = 'neutral' }) => {
  const styles = {
    primary: "border-accentPrimary text-accentPrimary bg-accentPrimary/5",
    success: "border-accentSuccess text-accentSuccess bg-accentSuccess/5",
    warning: "border-accentWarning text-accentWarning bg-accentWarning/5",
    danger: "border-accentDanger text-accentDanger bg-accentDanger/5",
    neutral: "border-darkBorder text-darkMuted bg-darkCard/50",
  };
  return (
    <span className={`text-[10px] uppercase font-mono tracking-wider px-2 py-0.5 rounded border ${styles[type]}`}>
      {status}
    </span>
  );
};

// Search Box Component
interface SearchBoxProps {
  value: string;
  onChange: (val: string) => void;
  placeholder?: string;
}
export const SearchBox: React.FC<SearchBoxProps> = ({ value, onChange, placeholder = "Search..." }) => {
  return (
    <div className="relative">
      <div className="absolute inset-y-0 left-3 flex items-center pointer-events-none text-darkMuted">
        <Search size={14} />
      </div>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="h-8 pl-9 pr-4 rounded bg-darkBg border border-darkBorder text-xs text-darkText placeholder-darkMuted focus:outline-none focus:border-accentPrimary transition-colors w-64"
      />
    </div>
  );
};

// Timeline Component
interface TimelineItem {
  event: string;
  detail: string;
  timestamp?: string;
}
export const Timeline: React.FC<{ items: TimelineItem[] }> = ({ items }) => {
  return (
    <div className="border-l border-darkBorder ml-3 space-y-4 py-2">
      {items.map((item, i) => (
        <div key={i} className="relative pl-6">
          <div className="absolute -left-[5px] top-1 w-2.5 h-2.5 rounded-full bg-accentPrimary border border-darkBg" />
          <div className="flex flex-col gap-0.5">
            <span className="text-xs font-bold text-darkText uppercase font-mono tracking-wider">{item.event}</span>
            <span className="text-xs text-darkMuted">{item.detail}</span>
            {item.timestamp && (
              <span className="text-[10px] font-mono text-darkMuted/60 mt-0.5">
                {new Date(item.timestamp).toLocaleString()}
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
};

// Loading Skeleton Component
export const LoadingSkeleton: React.FC = () => {
  return (
    <div className="animate-pulse space-y-4 w-full">
      <div className="h-4 bg-darkBorder rounded w-1/4"></div>
      <div className="space-y-2">
        <div className="h-10 bg-darkBorder rounded"></div>
        <div className="h-10 bg-darkBorder rounded w-5/6"></div>
        <div className="h-10 bg-darkBorder rounded w-2/3"></div>
      </div>
    </div>
  );
};

// Error State Component
interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
}
export const ErrorState: React.FC<ErrorStateProps> = ({ message, onRetry }) => {
  return (
    <div className="flex flex-col items-center justify-center p-8 bg-darkCard border border-accentDanger/30 rounded text-center max-w-md mx-auto my-12">
      <AlertCircle className="text-accentDanger mb-3" size={32} />
      <h3 className="text-sm font-bold uppercase tracking-wider text-darkText mb-1">Retrieval Error</h3>
      <p className="text-xs text-darkMuted mb-4">{message}</p>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          <RefreshCcw size={12} className="mr-1" /> Retry Request
        </Button>
      )}
    </div>
  );
};

// Empty State Component
interface EmptyStateProps {
  message?: string;
  title?: string;
}
export const EmptyState: React.FC<EmptyStateProps> = ({
  title = "No Data Found",
  message = "No matching records met the active criteria."
}) => {
  return (
    <div className="flex flex-col items-center justify-center p-12 bg-darkCard border border-darkBorder rounded text-center my-6">
      <FolderOpen className="text-darkMuted mb-3" size={32} />
      <h3 className="text-xs font-bold uppercase tracking-wider text-darkText mb-1">{title}</h3>
      <p className="text-xs text-darkMuted max-w-xs">{message}</p>
    </div>
  );
};

// Details Drawer Panel Component
interface DrawerProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}
export const Drawer: React.FC<DrawerProps> = ({ isOpen, onClose, title, children }) => {
  if (!isOpen) return null;
  return (
    <div className="fixed inset-y-0 right-0 w-[550px] bg-darkCard border-l border-darkBorder shadow-subtle z-50 flex flex-col transition-all duration-300">
      <div className="flex items-center justify-between h-14 px-4 border-b border-darkBorder flex-shrink-0">
        <span className="text-xs font-bold uppercase font-mono tracking-widest text-accentPrimary">{title}</span>
        <button
          onClick={onClose}
          className="text-darkMuted hover:text-darkText text-lg focus:outline-none"
        >
          &times;
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {children}
      </div>
    </div>
  );
};
