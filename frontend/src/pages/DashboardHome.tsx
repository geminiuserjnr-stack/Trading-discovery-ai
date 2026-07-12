import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Tv, Cpu, Calendar, Activity, Radio, Share2, Database, ShieldAlert, ExternalLink
} from 'lucide-react';
import { MetricCard, LoadingSkeleton, ErrorState, StatusBadge, Button } from '../components/UI';
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

  // Fetch real database discovery feed events
  const { data: feedData } = useQuery<any[]>({
    queryKey: ['dashboard-feed-events'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/discoveries/feed?limit=5`);
      if (!res.ok) throw new Error('Failed to retrieve live discovery feed');
      return res.json();
    },
    refetchInterval: 5000 // Poll every 5 seconds for real-time overview updates
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
  const newChannelsToday = stats?.new_channels_today ?? 0;
  const discordCommunitiesCount = stats?.discord_communities_count ?? 0;
  const discordCoveragePercentage = stats?.discord_coverage_percentage ?? 0.0;
  const apiQuotaRemaining = stats?.api_quota ?? 10000;

  return (
    <div className="space-y-6 select-none">
      {/* Page Title & Controls */}
      <div className="flex items-center justify-between border-b border-darkBorder pb-4">
        <div>
          <h1 className="text-lg font-bold uppercase font-mono tracking-widest text-accentPrimary">
            COMMUNITY DISCOVERY DASHBOARD
          </h1>
          <p className="text-xs text-darkMuted mt-0.5">
            Autonomous Discovery Engine for German Trading Communities
          </p>
        </div>
        <div className="flex gap-2">
          <StatusBadge status={`DATABASE: ${health?.database || 'OFFLINE'}`} type={health?.database === 'healthy' ? 'success' : 'danger'} />
          <StatusBadge status={`REDIS: ${health?.redis || 'OFFLINE'}`} type={health?.redis === 'healthy' ? 'success' : 'danger'} />
          <StatusBadge status={`CELERY: ${health?.celery || 'OFFLINE'}`} type={health?.celery === 'healthy' ? 'success' : 'danger'} />
        </div>
      </div>

      {/* Grid of 9 Refocused Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-3 gap-4">
        <MetricCard
          title="Total Channels Discovered"
          value={channelsCount}
          trend={{ text: "ACTIVE MONITORING", positive: true }}
          icon={Tv}
          onClick={() => navigate('/channels')}
          sparkline={[12, 14, 18, 24, 25, 30, channelsCount]}
        />
        <MetricCard
          title="New Channels Today"
          value={newChannelsToday}
          trend={{ text: "DISCOVERY STREAM", positive: true }}
          icon={Radio}
          onClick={() => navigate('/feed')}
        />
        <MetricCard
          title="Discord Communities Found"
          value={discordCommunitiesCount}
          trend={{ text: "VERIFIED INVITES", positive: true }}
          icon={Share2}
          onClick={() => navigate('/communities')}
          sparkline={[2, 4, 6, 8, 9, 12, discordCommunitiesCount]}
        />
        <MetricCard
          title="Discord Coverage %"
          value={`${discordCoveragePercentage.toFixed(1)}%`}
          trend={{ text: "CONVERSION COEFFICIENT", positive: true }}
          icon={ShieldAlert}
          onClick={() => navigate('/communities')}
        />
        <MetricCard
          title="API Quota Remaining"
          value={`${apiQuotaRemaining} / 10000`}
          trend={{ text: "DAILY ROTATION SAFE", positive: true }}
          icon={Activity}
          onClick={() => navigate('/monitoring')}
        />
        <MetricCard
          title="Worker Status"
          value={health?.celery === 'healthy' ? "ONLINE" : "OFFLINE"}
          trend={{ text: "Active task listeners", positive: health?.celery === 'healthy' }}
          icon={Cpu}
          onClick={() => navigate('/workers')}
        />
        <MetricCard
          title="Scheduler Status"
          value={stats?.scheduler_status ? stats.scheduler_status.toUpperCase() : "ACTIVE"}
          trend={{ text: "Beat triggers enabled", positive: true }}
          icon={Calendar}
          onClick={() => navigate('/scheduler')}
        />
        <MetricCard
          title="Database Status"
          value={health?.database === 'healthy' ? "HEALTHY" : "ERROR"}
          trend={{ text: "PostgreSQL relational node", positive: health?.database === 'healthy' }}
          icon={Database}
          onClick={() => navigate('/monitoring')}
        />
        <MetricCard
          title="Redis Status"
          value={health?.redis === 'healthy' ? "HEALTHY" : "ERROR"}
          trend={{ text: "Distributed broker cache", positive: health?.redis === 'healthy' }}
          icon={Cpu}
          onClick={() => navigate('/monitoring')}
        />
      </div>

      {/* Details Row: Latest Verified Discord Communities & Recent Queries */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
        {/* Latest Discord Communities */}
        <div className="bg-darkCard border border-darkBorder rounded p-4 flex flex-col justify-between shadow-subtle">
          <div className="flex items-center justify-between border-b border-darkBorder pb-2.5 mb-3">
            <h3 className="text-xs font-bold uppercase tracking-wider font-mono text-accentPrimary">
              Latest Discord Communities Found
            </h3>
            <span className="text-[10px] text-darkMuted font-mono uppercase">Verified Invites Only</span>
          </div>
          <div className="space-y-2.5 overflow-y-auto max-h-60">
            {stats?.latest_discords?.map((c: any) => (
              <div
                key={c.id}
                className="flex items-center justify-between p-2.5 rounded bg-darkBg border border-darkBorder/60 hover:border-darkBorder transition-colors"
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  {c.avatar ? (
                    <img src={c.avatar} alt="Avatar" className="w-6 h-6 rounded-full border border-darkBorder" />
                  ) : (
                    <div className="w-6 h-6 rounded-full bg-accentPrimary/10 border border-accentPrimary/30 flex items-center justify-center text-[10px] font-bold text-accentPrimary uppercase">
                      {c.channel_name.charAt(0)}
                    </div>
                  )}
                  <div className="flex flex-col min-w-0">
                    <a
                      href={`https://youtube.com/channel/${c.channel_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-darkText font-semibold hover:text-accentPrimary truncate hover:underline"
                    >
                      {c.channel_name}
                    </a>
                    <span className="text-[9px] text-darkMuted font-mono">
                      {c.detected_at ? new Date(c.detected_at).toLocaleDateString() : 'Just now'}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <StatusBadge status={c.discord_type.toUpperCase()} type={c.discord_type === 'paid' ? 'warning' : 'success'} />
                  <a
                    href={c.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-[11px] font-mono font-bold text-accentPrimary hover:underline px-2 py-1 bg-accentPrimary/10 border border-accentPrimary/25 rounded"
                  >
                    Join <ExternalLink size={10} />
                  </a>
                </div>
              </div>
            ))}
            {(!stats?.latest_discords || stats.latest_discords.length === 0) && (
              <p className="text-xs text-darkMuted text-center py-6 font-mono uppercase tracking-wide">No Discord communities discovered yet.</p>
            )}
          </div>
        </div>

        {/* Discovery Feed Live Data */}
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
            {feedData?.map((evt: any) => {
              const borderColors: Record<string, string> = {
                channel_discovered: 'border-accentSuccess',
                query_generated: 'border-accentPrimary',
                transcript_collected: 'border-accentPrimary',
                phrase_extracted: 'border-accentWarning',
              };
              const bColor = borderColors[evt.type] || 'border-darkMuted';
              return (
                <div key={evt.id} className={`text-xs flex gap-2 items-start border-l-2 ${bColor} pl-2 py-0.5`}>
                  <span className="text-[10px] font-mono text-darkMuted">{evt.time}</span>
                  <div>
                    <span className="text-darkMuted">{evt.title}</span> &rarr; <span className="text-darkText font-bold">{evt.message}</span>
                  </div>
                </div>
              );
            })}
            {(!feedData || feedData.length === 0) && (
              <p className="text-xs text-darkMuted text-center py-4">No active discoveries recorded.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
