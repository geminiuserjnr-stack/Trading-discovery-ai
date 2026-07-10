import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Terminal, RefreshCw, ChevronLeft, ChevronRight } from 'lucide-react';
import { Button, SearchBox, LoadingSkeleton } from '../components/UI';
import { API_BASE_URL } from '../config';

export const LogsViewer: React.FC = () => {
  const [search, setSearch] = useState('');
  const [level, setLevel] = useState<string>('all');
  const [moduleFilter, setModuleFilter] = useState<string>('all');
  const [page, setPage] = useState(0);
  const limit = 30;

  // Fetch structured logs from backend
  const { data: logsData, isLoading, refetch } = useQuery<any>({
    queryKey: ['system-logs', level, moduleFilter, search, page],
    queryFn: async () => {
      let url = `${API_BASE_URL}/logs?skip=${page * limit}&limit=${limit}`;
      if (level !== 'all') url += `&level=${level}`;
      if (moduleFilter !== 'all') url += `&module=${moduleFilter}`;
      if (search.trim()) url += `&search=${encodeURIComponent(search)}`;

      const res = await fetch(url);
      if (!res.ok) throw new Error('Failed to retrieve structured system logs');
      return res.json();
    }
  });

  const totalLogs = logsData?.total || 0;
  const logs = logsData?.logs || [];
  const maxPages = Math.ceil(totalLogs / limit);

  const getLogLevelStyle = (lvl: string) => {
    switch (lvl.toUpperCase()) {
      case 'ERROR':
        return 'text-accentDanger font-bold';
      case 'WARNING':
        return 'text-accentWarning font-bold';
      case 'INFO':
        return 'text-accentSuccess';
      default:
        return 'text-darkMuted';
    }
  };

  return (
    <div className="space-y-6 select-none h-full flex flex-col">
      {/* Title */}
      <div className="flex items-center justify-between border-b border-darkBorder pb-4 flex-shrink-0">
        <div>
          <h1 className="text-lg font-bold uppercase font-mono tracking-widest text-accentPrimary flex items-center gap-2">
            <Terminal size={18} /> SYSTEM EVENT LOGS
          </h1>
          <p className="text-xs text-darkMuted mt-0.5">
            Structured logs parsed dynamically from the database and discovery worker outputs.
          </p>
        </div>
        <Button variant="secondary" size="sm" onClick={() => refetch()}>
          <RefreshCw size={12} className="mr-1" /> Reload Logs
        </Button>
      </div>

      {/* Action Filters Bar */}
      <div className="flex items-center justify-between bg-darkCard border border-darkBorder rounded p-3 flex-shrink-0 flex-wrap gap-3">
        <div className="flex items-center gap-3 flex-wrap">
          <SearchBox value={search} onChange={(val) => { setSearch(val); setPage(0); }} placeholder="Full-text search logs..." />

          <select
            value={level}
            onChange={(e) => { setLevel(e.target.value); setPage(0); }}
            className="h-8 px-2.5 rounded bg-darkBg border border-darkBorder text-xs text-darkText focus:outline-none focus:border-accentPrimary transition-colors"
          >
            <option value="all">Level: All</option>
            <option value="info">Info</option>
            <option value="warning">Warning</option>
            <option value="error">Error</option>
          </select>

          <select
            value={moduleFilter}
            onChange={(e) => { setModuleFilter(e.target.value); setPage(0); }}
            className="h-8 px-2.5 rounded bg-darkBg border border-darkBorder text-xs text-darkText focus:outline-none focus:border-accentPrimary transition-colors"
          >
            <option value="all">Module: All</option>
            <option value="Scheduler">Scheduler</option>
            <option value="Worker">Worker</option>
            <option value="NLP">NLP</option>
            <option value="Database">Database</option>
            <option value="API">API</option>
          </select>
        </div>

        {/* Pagination indicator */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
            className="p-1 rounded hover:bg-darkBg text-darkMuted hover:text-darkText disabled:opacity-40 transition-colors focus:outline-none"
          >
            <ChevronLeft size={16} />
          </button>
          <span className="text-xs font-mono text-darkMuted">
            Page {page + 1} of {maxPages || 1}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(maxPages - 1, p + 1))}
            disabled={page >= maxPages - 1}
            className="p-1 rounded hover:bg-darkBg text-darkMuted hover:text-darkText disabled:opacity-40 transition-colors focus:outline-none"
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </div>

      {/* Terminal Output Console */}
      <div className="flex-1 bg-darkBg border border-darkBorder rounded overflow-hidden shadow-subtle p-3 font-mono flex flex-col">
        <div className="flex-1 overflow-y-auto space-y-2 pr-1 text-xs">
          {isLoading ? (
            <LoadingSkeleton />
          ) : logs.length === 0 ? (
            <p className="text-darkMuted text-center py-20 uppercase tracking-widest text-[10px]">No event logs match active query.</p>
          ) : (
            logs.map((log: any) => (
              <div
                key={log.id}
                className="flex items-start gap-3 p-1.5 hover:bg-darkCard/30 rounded border border-transparent hover:border-darkBorder/30 transition-colors leading-relaxed"
              >
                {/* Timestamp */}
                <span className="text-[10px] text-darkMuted w-36 flex-shrink-0 select-none">
                  {new Date(log.timestamp).toLocaleString()}
                </span>

                {/* Level badge */}
                <span className={`w-14 flex-shrink-0 text-left font-bold ${getLogLevelStyle(log.level)} uppercase tracking-wider text-[10px] select-none`}>
                  [{log.level}]
                </span>

                {/* Module */}
                <span className="text-accentPrimary w-20 flex-shrink-0 text-left font-semibold text-[10px] select-none uppercase truncate">
                  {log.module || 'SYSTEM'}
                </span>

                {/* Log message */}
                <span className="text-darkText flex-1 text-left break-all">
                  {log.message}
                </span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
