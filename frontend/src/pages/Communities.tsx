import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Share2, ExternalLink, RefreshCw } from 'lucide-react';
import { StatusBadge, LoadingSkeleton, ErrorState, EmptyState, Button } from '../components/UI';
import { API_BASE_URL } from '../config';

export const Communities: React.FC = () => {
  // Fetch communities (verified Discord servers) from the backend
  const { data: communities, isLoading, error, refetch } = useQuery<any[]>({
    queryKey: ['communities'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/communities`);
      if (!res.ok) throw new Error('Failed to retrieve verified trading communities');
      return res.json();
    }
  });

  if (error) {
    return <ErrorState message={(error as Error).message} onRetry={refetch} />;
  }

  return (
    <div className="space-y-6 select-none h-full flex flex-col">
      <div className="flex items-center justify-between border-b border-darkBorder pb-4 flex-shrink-0">
        <div>
          <h1 className="text-lg font-bold uppercase font-mono tracking-widest text-accentPrimary">
            DISCOVERED DISCORD COMMUNITIES
          </h1>
          <p className="text-xs text-darkMuted mt-0.5">
            Visualize matched verified external Discord communities crawled from German trading channels.
          </p>
        </div>
        <Button variant="secondary" size="sm" onClick={() => refetch()}>
          <RefreshCw size={12} className="mr-1" /> Refresh
        </Button>
      </div>

      {isLoading ? (
        <div className="p-8"><LoadingSkeleton /></div>
      ) : !communities || communities.length === 0 ? (
        <EmptyState
          title="No Verified Communities Found"
          message="Run discovery crawls on German channels to extract and validate authentic Discord server invites."
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {communities.map((c, i) => (
            <div key={i} className="p-4 bg-darkCard border border-darkBorder rounded space-y-3 shadow-subtle flex flex-col justify-between">
              <div className="flex items-start justify-between">
                <div className="space-y-1">
                  <span className="text-[10px] uppercase font-mono tracking-wider text-accentPrimary flex items-center gap-1.5">
                    <Share2 size={12} /> {c.platform}
                  </span>
                  <h3 className="text-sm font-bold text-darkText font-mono uppercase tracking-wide">
                    {c.name}
                  </h3>
                  <p className="text-xs text-darkMuted">
                    Associated channel: <span className="text-darkText font-semibold">{c.channel}</span>
                  </p>
                </div>
                <StatusBadge status={c.active ? "VERIFIED" : "DISCOVERED"} type={c.active ? "success" : "neutral"} />
              </div>

              <div className="flex items-center justify-between pt-2 border-t border-darkBorder/40 flex-shrink-0">
                <div className="flex flex-col gap-0.5">
                  <span className="text-[9px] font-mono text-darkMuted">INTELLIGENCE SCORE</span>
                  <span className="text-xs font-bold font-mono text-accentSuccess">{c.score} / 100</span>
                </div>
                <a
                  href={c.url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs font-mono font-bold text-accentPrimary hover:underline flex items-center gap-1"
                >
                  Inspect Invite <ExternalLink size={12} />
                </a>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
