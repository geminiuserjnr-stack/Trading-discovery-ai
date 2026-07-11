import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Radio, Play, Pause, Layers, Search, Hash, Cpu, AlertCircle, Sparkles } from 'lucide-react';
import { Button, StatusBadge, LoadingSkeleton } from '../components/UI';
import { API_BASE_URL } from '../config';

interface FeedEvent {
  id: string;
  time: string;
  type: 'channel_discovered' | 'query_generated' | 'transcript_collected' | 'phrase_extracted' | 'scheduler_completed' | 'info';
  title: string;
  message: string;
}

export const DiscoveryFeed: React.FC = () => {
  const [isLive, setIsLive] = useState(true);

  // Fetch real database discovery feed events
  const { data: eventsData, isLoading, refetch } = useQuery<FeedEvent[]>({
    queryKey: ['discovery-feed-events'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/discoveries/feed?limit=50`);
      if (!res.ok) throw new Error('Failed to retrieve live discovery feed');
      return res.json();
    },
    refetchInterval: isLive ? 4000 : undefined // Auto-poll every 4s for dynamic look in UI
  });

  if (isLoading) {
    return (
      <div className="space-y-6 select-none h-full flex flex-col p-4">
        <LoadingSkeleton />
      </div>
    );
  }

  const events = eventsData || [];

  const handleClear = () => {
    // Real clear not available, let's trigger reload
    refetch();
  };

  const getEventIcon = (type: string) => {
    switch (type) {
      case 'channel_discovered':
        return <Layers className="text-accentSuccess" size={14} />;
      case 'query_generated':
        return <Search className="text-accentPrimary" size={14} />;
      case 'transcript_collected':
        return <Cpu className="text-accentPrimary" size={14} />;
      case 'phrase_extracted':
        return <Hash className="text-accentWarning" size={14} />;
      case 'scheduler_completed':
        return <Sparkles className="text-accentSuccess" size={14} />;
      default:
        return <AlertCircle className="text-darkMuted" size={14} />;
    }
  };

  return (
    <div className="space-y-6 select-none h-full flex flex-col">
      {/* Page Title & Controls */}
      <div className="flex items-center justify-between border-b border-darkBorder pb-4 flex-shrink-0">
        <div>
          <h1 className="text-lg font-bold uppercase font-mono tracking-widest text-accentPrimary flex items-center gap-2">
            <Radio className="animate-pulse" size={18} /> DISCOVERY ACTIVITY STREAM
          </h1>
          <p className="text-xs text-darkMuted mt-0.5">
            Near real-time log of raw trading community discovery events.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant={isLive ? 'outline' : 'primary'}
            size="sm"
            onClick={() => setIsLive(!isLive)}
          >
            {isLive ? <Pause size={12} className="mr-1" /> : <Play size={12} className="mr-1" />}
            {isLive ? 'Pause Stream' : 'Go Live'}
          </Button>
          <Button variant="secondary" size="sm" onClick={handleClear}>
            Clear History
          </Button>
        </div>
      </div>

      {/* Live Stream Panel */}
      <div className="flex-1 bg-darkCard border border-darkBorder rounded p-4 flex flex-col justify-between shadow-subtle overflow-hidden">
        <div className="flex items-center justify-between border-b border-darkBorder pb-2 mb-4">
          <span className="text-[10px] uppercase font-mono tracking-widest text-darkMuted">Activity Log</span>
          <StatusBadge status={isLive ? "LIVE UPDATES ACTIVE" : "STREAM PAUSED"} type={isLive ? "success" : "warning"} />
        </div>

        {/* Scrollable Timeline Stream */}
        <div className="flex-1 overflow-y-auto pr-2 space-y-4">
          {events.map((evt) => (
            <div
              key={evt.id}
              className="flex items-start gap-4 p-3 rounded bg-darkBg border border-darkBorder/40 hover:border-darkBorder transition-all duration-200"
            >
              {/* Event Time */}
              <div className="text-[11px] font-mono text-darkMuted tracking-tight mt-0.5 w-10 flex-shrink-0">
                {evt.time}
              </div>

              {/* Icon Indicator */}
              <div className="p-1.5 rounded bg-darkCard border border-darkBorder flex-shrink-0">
                {getEventIcon(evt.type)}
              </div>

              {/* Event Text */}
              <div className="flex-1">
                <h4 className="text-xs font-bold uppercase tracking-wider text-darkText font-mono flex items-center gap-1.5">
                  {evt.title}
                  <span className="text-[9px] lowercase font-normal text-darkMuted">({evt.type.replace('_', ' ')})</span>
                </h4>
                <p className="text-xs text-darkMuted mt-1 bg-darkCard/40 px-2 py-1.5 rounded border border-darkBorder/10 font-mono text-darkText leading-relaxed">
                  {evt.message}
                </p>
              </div>
            </div>
          ))}

          {events.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center py-20 text-center">
              <Radio className="text-darkMuted mb-2 animate-pulse" size={24} />
              <p className="text-xs text-darkMuted">No live events captured in this stream session.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
