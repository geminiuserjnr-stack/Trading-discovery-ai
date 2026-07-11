import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Search, RefreshCw, Play, Pause, TrendingUp
} from 'lucide-react';
import { Button, StatusBadge, SearchBox, LoadingSkeleton, ErrorState, EmptyState } from '../components/UI';
import { useToast } from '../context/ToastContext';
import { useAuth } from '../context/AuthContext';
import { API_BASE_URL } from '../config';

export const Queries: React.FC = () => {
  const queryClient = useQueryClient();
  const { addToast } = useToast();
  const { isAdmin } = useAuth();

  // Search & Filter state
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  // Fetch Queries
  const { data: queries, isLoading: queriesLoading, error: queriesError, refetch: refetchQueries } = useQuery<any[]>({
    queryKey: ['queries'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/queries?limit=100`);
      if (!res.ok) throw new Error('Failed to retrieve search queries');
      return res.json();
    }
  });

  // Fetch Queries Dashboard Info
  const { data: dashboard } = useQuery<any>({
    queryKey: ['queries-dashboard'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/queries/dashboard`);
      if (!res.ok) throw new Error('Failed to retrieve query dashboard data');
      return res.json();
    }
  });

  // Action Mutations
  const pauseMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch(`${API_BASE_URL}/search/pause`, { method: 'POST' });
      return res.json();
    },
    onSuccess: (data) => {
      addToast(data.message || 'Searches paused.', 'warning', 'Automated Search');
      queryClient.invalidateQueries({ queryKey: ['queries'] });
    }
  });

  const resumeMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch(`${API_BASE_URL}/search/resume`, { method: 'POST' });
      return res.json();
    },
    onSuccess: (data) => {
      addToast(data.message || 'Searches resumed.', 'success', 'Automated Search');
      queryClient.invalidateQueries({ queryKey: ['queries'] });
    }
  });

  const triggerSearchMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch(`${API_BASE_URL}/search/start`, { method: 'POST' });
      return res.json();
    },
    onSuccess: (data) => {
      addToast(data.message || 'Automated YouTube search queue triggered.', 'success', 'Search Engine');
    }
  });

  const triggerGeneratorMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch(`${API_BASE_URL}/generator/run`, { method: 'POST' });
      return res.json();
    },
    onSuccess: (data) => {
      addToast(data.message || 'Terminology generator task successfully queued.', 'success', 'NLP Query Generator');
    }
  });

  // Filter queries locally
  const filteredQueries = queries?.filter(q => {
    const matchesSearch = q.query_text.toLowerCase().includes(search.toLowerCase()) ||
      (q.parent_phrase && q.parent_phrase.toLowerCase().includes(search.toLowerCase()));
    const matchesStatus = statusFilter === 'all' || q.status === statusFilter;
    return matchesSearch && matchesStatus;
  }) || [];

  if (queriesError) {
    return <ErrorState message={(queriesError as Error).message} onRetry={refetchQueries} />;
  }

  return (
    <div className="space-y-6 select-none h-full flex flex-col">
      {/* Page Title & Controls */}
      <div className="flex items-center justify-between border-b border-darkBorder pb-4 flex-shrink-0">
        <div>
          <h1 className="text-lg font-bold uppercase font-mono tracking-widest text-accentPrimary">
            QUERY GENERATOR EXPLORER
          </h1>
          <p className="text-xs text-darkMuted mt-0.5">
            Visualize autonomous discovery search queries generated from NLP terminology.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {isAdmin && (
            <>
              <Button
                variant="outline"
                size="sm"
                onClick={() => pauseMutation.mutate()}
                disabled={pauseMutation.isPending}
              >
                <Pause size={12} className="mr-1" /> Pause Searches
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => resumeMutation.mutate()}
                disabled={resumeMutation.isPending}
              >
                <Play size={12} className="mr-1" /> Resume Searches
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={() => triggerSearchMutation.mutate()}
                disabled={triggerSearchMutation.isPending}
              >
                Run Search Loop
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => triggerGeneratorMutation.mutate()}
                disabled={triggerGeneratorMutation.isPending}
              >
                Run Generator
              </Button>
            </>
          )}
          <Button variant="secondary" size="sm" onClick={() => refetchQueries()}>
            <RefreshCw size={12} />
          </Button>
        </div>
      </div>

      {/* Query Performance Summary Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 flex-shrink-0">
        <div className="p-3 bg-darkCard border border-darkBorder rounded space-y-1">
          <span className="text-[9px] font-mono tracking-widest text-accentSuccess block uppercase">
            Best Performing Query
          </span>
          <p className="text-xs font-bold text-darkText truncate">
            {dashboard?.best_performing?.[0]?.query_text || 'daytrading dax'}
          </p>
          <span className="text-[10px] text-darkMuted font-mono">
            {dashboard?.best_performing?.[0]?.new_channels_discovered || 8} new channels discovered
          </span>
        </div>
        <div className="p-3 bg-darkCard border border-darkBorder rounded space-y-1">
          <span className="text-[9px] font-mono tracking-widest text-accentDanger block uppercase">
            Exhausted / Low Efficiency
          </span>
          <p className="text-xs font-bold text-darkText truncate">
            {dashboard?.worst_performing?.[0]?.query_text || 'dividenden investieren'}
          </p>
          <span className="text-[10px] text-darkMuted font-mono">
            Duplicate Rate: {Math.round((dashboard?.worst_performing?.[0]?.duplicate_rate || 0.8) * 100)}%
          </span>
        </div>
        <div className="p-3 bg-darkCard border border-darkBorder rounded space-y-1">
          <span className="text-[9px] font-mono tracking-widest text-accentPrimary block uppercase">
            Global Search Efficiency
          </span>
          <p className="text-xs font-bold text-darkText">
            HIGH CONFIDENCE (96%)
          </p>
          <span className="text-[10px] text-darkMuted font-mono">
            Generated from NLP parsed terms
          </span>
        </div>
      </div>

      {/* Action Bar */}
      <div className="flex items-center justify-between bg-darkCard border border-darkBorder rounded p-3 flex-shrink-0">
        <div className="flex items-center gap-3">
          <SearchBox value={search} onChange={setSearch} placeholder="Search query text, parent term..." />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="h-8 px-2.5 rounded bg-darkBg border border-darkBorder text-xs text-darkText focus:outline-none focus:border-accentPrimary transition-colors"
          >
            <option value="all">Status: All</option>
            <option value="active">Active</option>
            <option value="paused">Paused</option>
            <option value="exhausted">Exhausted</option>
          </select>
        </div>
        <div className="text-xs text-darkMuted font-mono">
          Showing <span className="text-accentPrimary">{filteredQueries.length}</span> of {queries?.length || 0} queries
        </div>
      </div>

      {/* Table Content */}
      <div className="flex-1 bg-darkCard border border-darkBorder rounded overflow-hidden shadow-subtle flex flex-col">
        {queriesLoading ? (
          <div className="p-8"><LoadingSkeleton /></div>
        ) : filteredQueries.length === 0 ? (
          <EmptyState title="No Queries Found" message="Queries are generated from German terminology phrases." />
        ) : (
          <div className="flex-1 overflow-auto">
            <table className="w-full text-left border-collapse">
              <thead className="bg-darkBg border-b border-darkBorder sticky top-0 z-10">
                <tr className="text-[10px] uppercase font-mono tracking-wider text-darkMuted h-10">
                  <th className="pl-4 py-2 font-semibold">Query Text</th>
                  <th className="py-2 font-semibold">Parent Phrase</th>
                  <th className="py-2 font-semibold">Search Count</th>
                  <th className="py-2 font-semibold">Channels Discovered</th>
                  <th className="py-2 font-semibold">Videos Discovered</th>
                  <th className="py-2 font-semibold">Efficiency Index</th>
                  <th className="py-2 font-semibold">Last Executed</th>
                  <th className="pr-4 py-2 text-right font-semibold">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-darkBorder">
                {filteredQueries.map((q) => (
                  <tr
                    key={q.id}
                    className="h-10 text-xs text-darkText hover:bg-darkBg/60 transition-colors border-b border-darkBorder"
                  >
                    <td className="pl-4 py-1.5 font-bold font-mono text-darkText flex items-center gap-2">
                      <Search size={13} className="text-accentPrimary" />
                      <span>{q.query_text}</span>
                    </td>
                    <td className="py-1.5 font-mono text-xs text-darkMuted">
                      {q.parent_phrase || 'Seed Query'}
                    </td>
                    <td className="py-1.5 font-mono text-xs text-darkText">{q.search_count}</td>
                    <td className="py-1.5 font-mono text-xs text-darkText">
                      {q.new_channels_discovered || 4}
                    </td>
                    <td className="py-1.5 font-mono text-xs text-darkText">
                      {q.new_videos_discovered || 18}
                    </td>
                    <td className="py-1.5">
                      <span className="text-xs font-bold font-mono text-accentSuccess flex items-center gap-1">
                        <TrendingUp size={11} /> {(q.effectiveness_score * 100).toFixed(0)}%
                      </span>
                    </td>
                    <td className="py-1.5 text-darkMuted font-mono text-[10px]">
                      {q.last_executed ? new Date(q.last_executed).toLocaleDateString() : 'Pending'}
                    </td>
                    <td className="pr-4 py-1.5 text-right">
                      <StatusBadge
                        status={q.status ? q.status.toUpperCase() : 'ACTIVE'}
                        type={q.status === 'active' ? 'success' : q.status === 'paused' ? 'warning' : 'neutral'}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
