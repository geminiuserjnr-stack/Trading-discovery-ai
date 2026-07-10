import React, { useState, useEffect } from 'react';
import { Radio, Play, Pause, Layers, Search, Hash, Cpu, AlertCircle, Sparkles } from 'lucide-react';
import { Button, StatusBadge } from '../components/UI';

interface FeedEvent {
  id: string;
  time: string;
  type: 'channel_discovered' | 'query_generated' | 'transcript_collected' | 'phrase_extracted' | 'scheduler_completed' | 'info';
  title: string;
  message: string;
}

const INITIAL_EVENTS: FeedEvent[] = [
  { id: '1', time: '14:16', type: 'channel_discovered', title: 'New Discoveries', message: 'Discovered 3 new German trading channels: UC_scalping_de, UC_crypto_insider, UC_dax_live' },
  { id: '2', time: '14:12', type: 'phrase_extracted', title: 'Phrase Extracted', message: 'Liquiditäts Sweep' },
  { id: '3', time: '14:08', type: 'transcript_collected', title: 'Transcript Collected', message: 'Video: vid_tr_1 (DAX Live Trading)' },
  { id: '4', time: '14:05', type: 'query_generated', title: 'Generated Query', message: 'Orderflow Analyse ES' },
  { id: '5', time: '14:02', type: 'channel_discovered', title: 'Found Channel', message: 'Trader XYZ Deutschland' },
];

export const DiscoveryFeed: React.FC = () => {
  const [events, setEvents] = useState<FeedEvent[]>(INITIAL_EVENTS);
  const [isLive, setIsLive] = useState(true);

  useEffect(() => {
    if (!isLive) return;

    // Simulate realtime incoming WebSocket discovery events every 8 seconds
    const interval = setInterval(() => {
      const now = new Date();
      const timeStr = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;

      const generatedEvents: FeedEvent[] = [
        {
          id: Math.random().toString(),
          time: timeStr,
          type: 'channel_discovered',
          title: 'Found Channel',
          message: 'Börsen Elite (Austria/Germany community)'
        },
        {
          id: Math.random().toString(),
          time: timeStr,
          type: 'query_generated',
          title: 'Generated Query',
          message: 'Liquiditäts Sweep dax'
        },
        {
          id: Math.random().toString(),
          time: timeStr,
          type: 'phrase_extracted',
          title: 'Phrase Extracted',
          message: 'Fair Value Gap'
        },
        {
          id: Math.random().toString(),
          time: timeStr,
          type: 'transcript_collected',
          title: 'Transcript Collected',
          message: 'Video: vid_bo_1 (Ausbruchsstrategie)'
        },
        {
          id: Math.random().toString(),
          time: timeStr,
          type: 'scheduler_completed',
          title: 'Scheduler Run',
          message: 'recalculate_rankings succeeded in 1.1s'
        }
      ];

      const newEvent = generatedEvents[Math.floor(Math.random() * generatedEvents.length)];
      setEvents((prev) => [newEvent, ...prev.slice(0, 49)]); // Keep last 50 events
    }, 8000);

    return () => clearInterval(interval);
  }, [isLive]);

  const handleClear = () => {
    setEvents([]);
  };

  const getEventIcon = (type: FeedEvent['type']) => {
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
