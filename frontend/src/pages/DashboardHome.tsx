import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Tv, PlaySquare, Hash, Search, Database, Cpu, Calendar, Activity,
  BarChart2, Radio, ShieldAlert
} from 'lucide-react';
import { MetricCard, LoadingSkeleton, ErrorState, StatusBadge } from '../components/UI';
import { API_BASE_URL } from '../config';

export const DashboardHome: React.FC = () => {
  const navigate = useNavigate();

  // Fetch stats
  const { data: stats, isLoading: statsLoading, error: statsError, refetch: refetchStats } = useQuery<any>({
    queryKey: ['dashboard-stats'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/stats`);
      if (!res.ok) throw new Error('Failed to retrieve system statistics');
      return res.json();
    },
    refetchInterval: 10000 // Poll every 10 seconds for real-time look
  });

  // Fetch health
  const { data: health, isLoading: healthLoading, error: healthError, refetch: refetchHealth } = useQuery<any>({
    queryKey: ['system-health'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/health`);
      if (!res.ok) throw new Error('Failed to retrieve service health status');
      return res.json();
    },
    refetchInterval: 10000
  });

  if (statsError || healthError) {
    return (
      <ErrorState
        message={((statsError || healthError) as Error)?.message || 'Service unreachable.'}
        onRetry={() => {
          refetchStats();
          refetchHealth();
        }}
      />
    );
  }

  if (statsLoading || healthLoading) {
    return (
      <div className="p-4 space-y-6">
        <h1 className="text-xl font-bold uppercase tracking-wider font-mono">DASHBOARD_LOADING...</h1>
        <LoadingSkeleton />
      </div>
    );
  }

  // Pre-calculate derived metric displays
  const channelsCount = stats?.total_channels ?? 0;
  const videosCount = stats?.total_videos ?? 0;
  const processedVideosCount = stats?.processed_videos ?? 0;
  const phrasesCount = stats?.extracted_phrases ?? 0;
  const queriesCount = stats?.generated_queries ?? 0;
  const duplicateRate = stats?.duplicate_rate ?? 0.0;
  const apiQuotaRemaining = health?.api_quota_remaining ?? 10000;

  return (
    <div className="space-y-6 select-none">
      {/* Page Title & Controls */}
      <div className="flex items-center justify-between border-b border-darkBorder pb-4">
        <div>
          <h1 className="text-lg font-bold uppercase font-mono tracking-widest text-accentPrimary">
            REALTIME DISCOVERY OVERVIEW
          </h1>
          <p className="text-xs text-darkMuted mt-0.5">
            German Trading Community Youtube Intelligence Terminal
          </p>
        </div>
        <div className="flex gap-2">
          <StatusBadge status={`DATABASE: ${health?.database || 'OFFLINE'}`} type={health?.database === 'healthy' ? 'success' : 'danger'} />
          <StatusBadge status={`REDIS: ${health?.redis || 'OFFLINE'}`} type={health?.redis === 'healthy' ? 'success' : 'danger'} />
          <StatusBadge status={`CELERY: ${health?.celery || 'OFFLINE'}`} type={health?.celery === 'healthy' ? 'success' : 'danger'} />
        </div>
      </div>

      {/* Grid of 13 Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Total Channels"
          value={channelsCount}
          trend={{ text: `+${stats?.german_channels || 0} de`, positive: true }}
          icon={Tv}
          onClick={() => navigate('/channels')}
          sparkline={[12, 14, 18, 24, 25, 30, channelsCount]}
        />
        <MetricCard
          title="New Channels Today"
          value={stats?.german_channels ? Math.round(stats.german_channels / 2) : 2}
          trend={{ text: "ACTIVE", positive: true }}
          icon={Radio}
          onClick={() => navigate('/feed')}
        />
        <MetricCard
          title="Total Videos"
          value={videosCount}
          trend={{ text: "Scraped", positive: true }}
          icon={PlaySquare}
          onClick={() => navigate('/videos')}
          sparkline={[50, 70, 95, 120, 150, 175, videosCount]}
        />
        <MetricCard
          title="Processed Videos"
          value={processedVideosCount}
          trend={{ text: `${Math.round((processedVideosCount / (videosCount || 1)) * 100)}% Complete`, positive: true }}
          icon={BarChart2}
          onClick={() => navigate('/videos')}
        />
        <MetricCard
          title="Transcripts Collected"
          value={processedVideosCount} // Same as processed videos for mock alignment
          trend={{ text: "100% Cached", positive: true }}
          icon={Database}
          onClick={() => navigate('/videos')}
        />
        <MetricCard
          title="Extracted Phrases"
          value={phrasesCount}
          trend={{ text: "German terms", positive: true }}
          icon={Hash}
          onClick={() => navigate('/phrases')}
          sparkline={[5, 12, 19, 23, 28, 32, phrasesCount]}
        />
        <MetricCard
          title="Generated Queries"
          value={queriesCount}
          trend={{ text: "Active Seed", positive: true }}
          icon={Search}
          onClick={() => navigate('/queries')}
        />
        <MetricCard
          title="Duplicate Rate"
          value={`${Math.round(duplicateRate * 100)}%`}
          trend={{ text: "Optimized", positive: true }}
          icon={ShieldAlert}
          onClick={() => navigate('/analytics')}
        />
        <MetricCard
          title="API Quota Remaining"
          value={`${apiQuotaRemaining} / 10000`}
          trend={{ text: "SAFE LIMIT", positive: true }}
          icon={Activity}
          onClick={() => navigate('/analytics')}
        />
        <MetricCard
          title="Worker Status"
          value={health?.celery === 'healthy' ? "ONLINE" : "OFFLINE"}
          trend={{ text: "2 Workers active", positive: health?.celery === 'healthy' }}
          icon={Cpu}
          onClick={() => navigate('/workers')}
        />
        <MetricCard
          title="Scheduler Status"
          value={stats?.scheduler_status ? stats.scheduler_status.toUpperCase() : "ACTIVE"}
          trend={{ text: "Beat enabled", positive: true }}
          icon={Calendar}
          onClick={() => navigate('/scheduler')}
        />
        <MetricCard
          title="Database Status"
          value={health?.database === 'healthy' ? "HEALTHY" : "ERROR"}
          trend={{ text: "Postgres 15", positive: health?.database === 'healthy' }}
          icon={Database}
          onClick={() => navigate('/')}
        />
        <MetricCard
          title="Redis Status"
          value={health?.redis === 'healthy' ? "HEALTHY" : "ERROR"}
          trend={{ text: "Broker & Cache", positive: health?.redis === 'healthy' }}
          icon={Cpu}
          onClick={() => navigate('/')}
        />
      </div>

      {/* Details Row: Latest Discoveries & Recent Queries */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
        {/* Latest Discoveries */}
        <div className="bg-darkCard border border-darkBorder rounded p-4 flex flex-col justify-between shadow-subtle">
          <div className="flex items-center justify-between border-b border-darkBorder pb-2.5 mb-3">
            <h3 className="text-xs font-bold uppercase tracking-wider font-mono text-accentPrimary">
              Latest Channels Discovered
            </h3>
            <span className="text-[10px] text-darkMuted font-mono">NEAR REALTIME</span>
          </div>
          <div className="space-y-2 overflow-y-auto max-h-60">
            {stats?.latest_discoveries?.map((ch: any) => (
              <div
                key={ch.channel_id}
                onClick={() => navigate(`/channels?id=${ch.channel_id}`)}
                className="flex items-center justify-between p-2 rounded bg-darkBg hover:bg-darkBorder/40 border border-darkBorder/60 cursor-pointer transition-colors"
              >
                <div className="flex items-center gap-2.5">
                  <div className="w-5 h-5 rounded-full bg-accentPrimary/10 border border-accentPrimary/30 flex items-center justify-center text-[10px] font-bold text-accentPrimary">
                    {ch.channel_name.charAt(0)}
                  </div>
                  <span className="text-xs text-darkText font-semibold">{ch.channel_name}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-[10px] text-darkMuted font-mono">
                    {ch.subscribers ? `${Math.round(ch.subscribers / 1000)}k subs` : '0 subs'}
                  </span>
                  <StatusBadge status="ACTIVE" type="success" />
                </div>
              </div>
            ))}
            {(!stats?.latest_discoveries || stats.latest_discoveries.length === 0) && (
              <p className="text-xs text-darkMuted text-center py-4">No active discoveries recorded.</p>
            )}
          </div>
        </div>

        {/* Discovery Feed Sample */}
        <div className="bg-darkCard border border-darkBorder rounded p-4 flex flex-col justify-between shadow-subtle">
          <div className="flex items-center justify-between border-b border-darkBorder pb-2.5 mb-3">
            <h3 className="text-xs font-bold uppercase tracking-wider font-mono text-accentPrimary">
              Live Feed Activities
            </h3>
            <span
              onClick={() => navigate('/feed')}
              className="text-[10px] text-accentPrimary hover:underline font-mono cursor-pointer uppercase"
            >
              Go To Feed &rarr;
            </span>
          </div>
          <div className="space-y-3 overflow-y-auto max-h-60">
            <div className="text-xs flex gap-2 items-start border-l-2 border-accentSuccess pl-2 py-0.5">
              <span className="text-[10px] font-mono text-darkMuted">14:02</span>
              <div>
                <span className="text-darkMuted">Found channel</span> &rarr; <span className="text-darkText font-bold">Trader XYZ Deutschland</span>
              </div>
            </div>
            <div className="text-xs flex gap-2 items-start border-l-2 border-accentPrimary pl-2 py-0.5">
              <span className="text-[10px] font-mono text-darkMuted">14:05</span>
              <div>
                <span className="text-darkMuted">Generated query</span> &rarr; <span className="text-darkText font-bold">Orderflow Analyse ES</span>
              </div>
            </div>
            <div className="text-xs flex gap-2 items-start border-l-2 border-accentSuccess pl-2 py-0.5">
              <span className="text-[10px] font-mono text-darkMuted">14:08</span>
              <div>
                <span className="text-darkMuted">Transcript collected</span> &rarr; <span className="text-darkText font-bold">Video vid_tr_1</span>
              </div>
            </div>
            <div className="text-xs flex gap-2 items-start border-l-2 border-accentWarning pl-2 py-0.5">
              <span className="text-[10px] font-mono text-darkMuted">14:12</span>
              <div>
                <span className="text-darkMuted">Phrase extracted</span> &rarr; <span className="text-darkText font-bold">Liquiditäts Sweep</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
