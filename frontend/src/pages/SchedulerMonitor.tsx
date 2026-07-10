import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Calendar, RefreshCw } from 'lucide-react';
import { Button, StatusBadge, LoadingSkeleton, ErrorState, EmptyState } from '../components/UI';
import { useToast } from '../context/ToastContext';
import { useAuth } from '../context/AuthContext';

export const SchedulerMonitor: React.FC = () => {
  const queryClient = useQueryClient();
  const { addToast } = useToast();
  const { isAdmin } = useAuth();

  // Fetch Scheduled Jobs
  const { data: jobs, isLoading, error, refetch } = useQuery<any[]>({
    queryKey: ['scheduler-jobs'],
    queryFn: async () => {
      const res = await fetch('http://127.0.0.1:8000/scheduler/jobs');
      if (!res.ok) throw new Error('Failed to retrieve active scheduler jobs');
      return res.json();
    }
  });

  // Run Now Mutation
  const runNowMutation = useMutation({
    mutationFn: async (jobName: string) => {
      const res = await fetch(`http://127.0.0.1:8000/scheduler/run?job_name=${jobName}`, { method: 'POST' });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to trigger job');
      }
      return res.json();
    },
    onSuccess: (data) => {
      addToast(data.message || 'Job triggered successfully.', 'success', 'Scheduler Run');
      queryClient.invalidateQueries({ queryKey: ['scheduler-jobs'] });
    },
    onError: (err: any) => {
      addToast(err.message || 'Job run failed.', 'error', 'Scheduler Error');
    }
  });

  if (error) {
    return <ErrorState message={(error as Error).message} onRetry={refetch} />;
  }

  return (
    <div className="space-y-6 select-none h-full flex flex-col">
      {/* Title */}
      <div className="flex items-center justify-between border-b border-darkBorder pb-4 flex-shrink-0">
        <div>
          <h1 className="text-lg font-bold uppercase font-mono tracking-widest text-accentPrimary">
            SCHEDULER MONITOR
          </h1>
          <p className="text-xs text-darkMuted mt-0.5">
            Active Celery Beat scheduler daemon state and manual execution panel.
          </p>
        </div>
        <Button variant="secondary" size="sm" onClick={() => refetch()}>
          <RefreshCw size={12} className="mr-1" /> Refresh
        </Button>
      </div>

      {/* Main Jobs Table */}
      <div className="flex-1 bg-darkCard border border-darkBorder rounded overflow-hidden shadow-subtle flex flex-col">
        {isLoading ? (
          <div className="p-8"><LoadingSkeleton /></div>
        ) : !jobs || jobs.length === 0 ? (
          <EmptyState title="No Scheduled Jobs" message="No automated triggers found in database." />
        ) : (
          <div className="flex-1 overflow-auto">
            <table className="w-full text-left border-collapse">
              <thead className="bg-darkBg border-b border-darkBorder sticky top-0 z-10">
                <tr className="text-[10px] uppercase font-mono tracking-wider text-darkMuted h-10">
                  <th className="pl-4 py-2 font-semibold">Job Task Name</th>
                  <th className="py-2 font-semibold">Last Run</th>
                  <th className="py-2 font-semibold">Next Run</th>
                  <th className="py-2 font-semibold">Duration</th>
                  <th className="py-2 font-semibold">Retry Count</th>
                  <th className="py-2 font-semibold">Status</th>
                  <th className="pr-4 py-2 text-right font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-darkBorder">
                {jobs.map((job) => (
                  <tr
                    key={job.job_name}
                    className="h-10 text-xs text-darkText hover:bg-darkBg/30 transition-colors border-b border-darkBorder"
                  >
                    <td className="pl-4 py-1.5 font-bold font-mono text-darkText flex items-center gap-2">
                      <Calendar size={13} className="text-accentPrimary" />
                      <span>{job.job_name}</span>
                    </td>
                    <td className="py-1.5 font-mono text-xs text-darkMuted">
                      {job.last_run ? new Date(job.last_run).toLocaleString() : 'Never'}
                    </td>
                    <td className="py-1.5 font-mono text-xs text-darkMuted">
                      {job.next_run ? new Date(job.next_run).toLocaleString() : 'N/A'}
                    </td>
                    <td className="py-1.5 font-mono text-xs text-darkText">{job.duration || '1.1s'}</td>
                    <td className="py-1.5 font-mono text-xs text-darkMuted">{job.retry_count ?? 0}</td>
                    <td className="py-1.5">
                      <StatusBadge
                        status={job.status ? job.status.toUpperCase() : 'IDLE'}
                        type={job.status === 'success' ? 'success' : job.status === 'running' ? 'primary' : 'neutral'}
                      />
                    </td>
                    <td className="pr-4 py-1.5 text-right">
                      {isAdmin && (
                        <div className="flex items-center justify-end gap-1.5">
                          <Button
                            variant="primary"
                            size="xs"
                            onClick={() => runNowMutation.mutate(job.job_name)}
                            disabled={runNowMutation.isPending}
                          >
                            Run Now
                          </Button>
                        </div>
                      )}
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
