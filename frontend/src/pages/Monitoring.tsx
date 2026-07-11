import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Activity, Database, Key, Server, Cpu, Settings as SettingsIcon } from 'lucide-react';
import { StatusBadge, LoadingSkeleton, ErrorState } from '../components/UI';
import { API_BASE_URL } from '../config';

export const Monitoring: React.FC = () => {
  // Fetch dynamic system health status
  const { data: health, isLoading: healthLoading, error: healthError } = useQuery<any>({
    queryKey: ['monitoring-health'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/health`);
      if (!res.ok) throw new Error('Failed to retrieve core health metrics');
      return res.json();
    }
  });

  // Fetch quota consumption logs
  const { data: quotaLogs, isLoading: quotaLoading } = useQuery<any[]>({
    queryKey: ['monitoring-quota'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/stats/quota`);
      if (!res.ok) throw new Error('Failed to retrieve quota telemetry');
      return res.json();
    }
  });

  // Fetch dynamic discovery parameters
  const { data: settings, isLoading: settingsLoading } = useQuery<any>({
    queryKey: ['monitoring-settings'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/settings`);
      if (!res.ok) throw new Error('Failed to retrieve active parameters');
      return res.json();
    }
  });

  if (healthError) {
    return <ErrorState message={(healthError as Error).message} />;
  }

  const latestQuota = quotaLogs?.[0] || {
    daily_quota_consumed: 0,
    remaining_quota_estimate: 10000,
    requests_made: 0,
    failed_requests: 0
  };

  return (
    <div className="space-y-6 select-none h-full flex flex-col">
      {/* Title */}
      <div className="flex items-center justify-between border-b border-darkBorder pb-4 flex-shrink-0">
        <div>
          <h1 className="text-lg font-bold uppercase font-mono tracking-widest text-accentPrimary flex items-center gap-2">
            <Activity size={18} /> CRITICAL TELEMETRY MONITORING
          </h1>
          <p className="text-xs text-darkMuted mt-0.5">
            Active tracking of database query latency, broker connections, API rate counters, and system parameters.
          </p>
        </div>
      </div>

      {healthLoading || quotaLoading || settingsLoading ? (
        <div className="p-8"><LoadingSkeleton /></div>
      ) : (
        <div className="space-y-6">
          {/* Services Health Grid */}
          <div className="bg-darkCard border border-darkBorder rounded p-4 shadow-subtle space-y-4">
            <h3 className="text-xs font-bold uppercase font-mono tracking-wider text-accentPrimary border-b border-darkBorder pb-2">
              Backing Services Operational Status
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-3 bg-darkBg border border-darkBorder rounded flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <Database size={16} className="text-accentPrimary" />
                  <span className="text-xs font-mono font-semibold text-darkText">PostgreSQL Health:</span>
                </div>
                <StatusBadge status={health?.database?.toUpperCase() || "OFFLINE"} type={health?.database === "healthy" ? "success" : "danger"} />
              </div>

              <div className="p-3 bg-darkBg border border-darkBorder rounded flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <Server size={16} className="text-accentPrimary" />
                  <span className="text-xs font-mono font-semibold text-darkText">Redis Broker Health:</span>
                </div>
                <StatusBadge status={health?.redis?.toUpperCase() || "OFFLINE"} type={health?.redis === "healthy" ? "success" : "danger"} />
              </div>

              <div className="p-3 bg-darkBg border border-darkBorder rounded flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <Cpu size={16} className="text-accentPrimary" />
                  <span className="text-xs font-mono font-semibold text-darkText">Celery Ingest Queue:</span>
                </div>
                <StatusBadge status={health?.celery?.toUpperCase() || "OFFLINE"} type={health?.celery === "healthy" ? "success" : "danger"} />
              </div>
            </div>
          </div>

          {/* YouTube API Telemetry */}
          <div className="bg-darkCard border border-darkBorder rounded p-4 shadow-subtle space-y-4">
            <h3 className="text-xs font-bold uppercase font-mono tracking-wider text-accentPrimary border-b border-darkBorder pb-2">
              YouTube Data API Quota Usage (Today)
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="p-3 bg-darkBg border border-darkBorder rounded space-y-1">
                <span className="text-[9px] font-mono text-darkMuted uppercase">Daily Limit</span>
                <span className="text-base font-bold font-mono text-darkText block">10,000 units</span>
              </div>
              <div className="p-3 bg-darkBg border border-darkBorder rounded space-y-1">
                <span className="text-[9px] font-mono text-darkMuted uppercase">Quota Consumed</span>
                <span className="text-base font-bold font-mono text-accentWarning block">{latestQuota.daily_quota_consumed} units</span>
              </div>
              <div className="p-3 bg-darkBg border border-darkBorder rounded space-y-1">
                <span className="text-[9px] font-mono text-darkMuted uppercase">Requests Dispatched</span>
                <span className="text-base font-bold font-mono text-accentPrimary block">{latestQuota.requests_made} calls</span>
              </div>
              <div className="p-3 bg-darkBg border border-darkBorder rounded space-y-1">
                <span className="text-[9px] font-mono text-darkMuted uppercase">Failed Requests</span>
                <span className={`text-base font-bold font-mono block ${latestQuota.failed_requests > 0 ? 'text-accentDanger' : 'text-accentSuccess'}`}>
                  {latestQuota.failed_requests} errors
                </span>
              </div>
            </div>
          </div>

          {/* Pipeline Active Config */}
          <div className="bg-darkCard border border-darkBorder rounded p-4 shadow-subtle space-y-4">
            <h3 className="text-xs font-bold uppercase font-mono tracking-wider text-accentPrimary border-b border-darkBorder pb-2">
              Active Discovery Engine Parameters
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-3 bg-darkBg border border-darkBorder rounded flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <SettingsIcon size={14} className="text-accentPrimary" />
                  <span className="text-xs font-mono text-darkMuted uppercase">Max Crawl Depth:</span>
                </div>
                <span className="text-xs font-mono font-bold text-darkText">{settings?.max_search_depth || 3}</span>
              </div>

              <div className="p-3 bg-darkBg border border-darkBorder rounded flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Key size={14} className="text-accentPrimary" />
                  <span className="text-xs font-mono text-darkMuted uppercase">Quota Alert Limit:</span>
                </div>
                <span className="text-xs font-mono font-bold text-darkText">{settings?.api_quota_limit || 10000}</span>
              </div>

              <div className="p-3 bg-darkBg border border-darkBorder rounded flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Cpu size={14} className="text-accentPrimary" />
                  <span className="text-xs font-mono text-darkMuted uppercase">Thread Pool Load:</span>
                </div>
                <span className="text-xs font-mono font-bold text-darkText">{settings?.worker_concurrency || 4} threads</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
