import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Settings as SettingsIcon, Save } from 'lucide-react';
import { Button, LoadingSkeleton, ErrorState, StatusBadge } from '../components/UI';
import { useToast } from '../context/ToastContext';
import { useAuth } from '../context/AuthContext';
import { API_BASE_URL } from '../config';

export const Settings: React.FC = () => {
  const queryClient = useQueryClient();
  const { addToast } = useToast();
  const { isAdmin } = useAuth();

  // Local Form state
  const [searchFreq, setSearchFreq] = useState('');
  const [maxSearchDepth, setMaxSearchDepth] = useState(3);
  const [langThreshold, setLangThreshold] = useState(0.85);
  const [retryPolicy, setRetryPolicy] = useState('');
  const [concurrency, setConcurrency] = useState(4);
  const [logLevel, setLogLevel] = useState('INFO');
  const [apiLimit, setApiLimit] = useState(10000);

  // Validation state
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Fetch Settings
  const { data: settingsData, isLoading, error, refetch } = useQuery<any>({
    queryKey: ['system-settings'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/settings`);
      if (!res.ok) throw new Error('Failed to retrieve system configuration');
      return res.json();
    }
  });

  // Sync state with fetched data
  useEffect(() => {
    if (settingsData) {
      setSearchFreq(settingsData.search_frequency || 'Every 15 minutes');
      setMaxSearchDepth(settingsData.max_search_depth ?? 3);
      setLangThreshold(settingsData.language_confidence_threshold ?? 0.85);
      setRetryPolicy(settingsData.transcript_retry_policy || 'exponential_backoff_3');
      setConcurrency(settingsData.worker_concurrency ?? 4);
      setLogLevel(settingsData.logging_level || 'INFO');
      setApiLimit(settingsData.api_quota_limit ?? 10000);
    }
  }, [settingsData]);

  // Update Settings Mutation
  const saveMutation = useMutation({
    mutationFn: async (payload: any) => {
      const res = await fetch(`${API_BASE_URL}/settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Settings validation error');
      }
      return res.json();
    },
    onSuccess: (data) => {
      addToast(data.message || 'Settings validated and saved successfully.', 'success', 'Settings Manager');
      queryClient.invalidateQueries({ queryKey: ['system-settings'] });
      setErrors({});
    },
    onError: (err: any) => {
      addToast(err.message || 'Failed to update settings.', 'error', 'Validation Error');
      setErrors({ global: err.message });
    }
  });

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    if (!isAdmin) {
      addToast('Permissions Error: Viewer role is restricted from editing system settings.', 'error', 'Restricted Action');
      return;
    }

    // Local Validations
    const formErrors: Record<string, string> = {};

    if (maxSearchDepth < 1 || maxSearchDepth > 10) {
      formErrors.maxSearchDepth = "Maximum search depth must be an integer between 1 and 10.";
    }
    if (langThreshold < 0.0 || langThreshold > 1.0) {
      formErrors.langThreshold = "Language confidence threshold must be a decimal between 0.0 and 1.0.";
    }
    if (apiLimit < 0 || apiLimit > 100000) {
      formErrors.apiLimit = "API Quota Limit must be an integer between 0 and 100,000.";
    }
    if (concurrency < 1 || concurrency > 32) {
      formErrors.concurrency = "Worker concurrency must be between 1 and 32 threads.";
    }

    if (Object.keys(formErrors).length > 0) {
      setErrors(formErrors);
      addToast('Validation failed. Please correct form inputs and try again.', 'error', 'Validation Error');
      return;
    }

    // Trigger save
    const payload = {
      search_frequency: searchFreq,
      max_search_depth: maxSearchDepth,
      language_confidence_threshold: langThreshold,
      transcript_retry_policy: retryPolicy,
      worker_concurrency: concurrency,
      logging_level: logLevel,
      api_quota_limit: apiLimit
    };
    saveMutation.mutate(payload);
  };

  if (error) {
    return <ErrorState message={(error as Error).message} onRetry={refetch} />;
  }

  return (
    <div className="space-y-6 select-none max-w-4xl mx-auto">
      {/* Title */}
      <div className="flex items-center justify-between border-b border-darkBorder pb-4">
        <div>
          <h1 className="text-lg font-bold uppercase font-mono tracking-widest text-accentPrimary flex items-center gap-2">
            <SettingsIcon size={18} /> CONFIGURATION SETTINGS
          </h1>
          <p className="text-xs text-darkMuted mt-0.5">
            Modify YouTube crawler limits, language filters, and Celery background task concurrency settings.
          </p>
        </div>
      </div>

      {isLoading ? (
        <LoadingSkeleton />
      ) : (
        <form onSubmit={handleSave} className="bg-darkCard border border-darkBorder rounded p-6 space-y-6 shadow-subtle">
          {/* Header Status */}
          <div className="flex items-center justify-between border-b border-darkBorder pb-3">
            <span className="text-[10px] uppercase font-mono tracking-widest text-darkMuted">System variables</span>
            <StatusBadge status={isAdmin ? "EDIT MODE ACTIVE" : "VIEWER ROLE RESTRICTED"} type={isAdmin ? "primary" : "warning"} />
          </div>

          {/* Form Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Search Frequency */}
            <div className="space-y-1.5">
              <label className="text-[10px] uppercase font-mono tracking-wider text-darkMuted block">Search Loop Frequency</label>
              <input
                type="text"
                disabled={!isAdmin}
                value={searchFreq}
                onChange={(e) => setSearchFreq(e.target.value)}
                className="w-full h-8 px-3 rounded bg-darkBg border border-darkBorder text-xs text-darkText focus:outline-none focus:border-accentPrimary transition-colors disabled:opacity-50"
              />
            </div>

            {/* Maximum Search Depth */}
            <div className="space-y-1.5">
              <label className="text-[10px] uppercase font-mono tracking-wider text-darkMuted block">Maximum Search Depth (Max 10)</label>
              <input
                type="number"
                disabled={!isAdmin}
                value={maxSearchDepth}
                onChange={(e) => setMaxSearchDepth(parseInt(e.target.value) || 0)}
                className={`w-full h-8 px-3 rounded bg-darkBg border text-xs text-darkText focus:outline-none focus:border-accentPrimary transition-colors disabled:opacity-50 ${
                  errors.maxSearchDepth ? 'border-accentDanger' : 'border-darkBorder'
                }`}
              />
              {errors.maxSearchDepth && <span className="text-[9px] text-accentDanger font-mono block">{errors.maxSearchDepth}</span>}
            </div>

            {/* Language confidence threshold */}
            <div className="space-y-1.5">
              <label className="text-[10px] uppercase font-mono tracking-wider text-darkMuted block">German Language Confidence (0.0 - 1.0)</label>
              <input
                type="number"
                step="0.01"
                disabled={!isAdmin}
                value={langThreshold}
                onChange={(e) => setLangThreshold(parseFloat(e.target.value) || 0)}
                className={`w-full h-8 px-3 rounded bg-darkBg border text-xs text-darkText focus:outline-none focus:border-accentPrimary transition-colors disabled:opacity-50 ${
                  errors.langThreshold ? 'border-accentDanger' : 'border-darkBorder'
                }`}
              />
              {errors.langThreshold && <span className="text-[9px] text-accentDanger font-mono block">{errors.langThreshold}</span>}
            </div>

            {/* Transcript Retry Policy */}
            <div className="space-y-1.5">
              <label className="text-[10px] uppercase font-mono tracking-wider text-darkMuted block">Transcript Retry Policy</label>
              <select
                disabled={!isAdmin}
                value={retryPolicy}
                onChange={(e) => setRetryPolicy(e.target.value)}
                className="w-full h-8 px-2 rounded bg-darkBg border border-darkBorder text-xs text-darkText focus:outline-none focus:border-accentPrimary transition-colors disabled:opacity-50"
              >
                <option value="exponential_backoff_3">Exponential Backoff (3 retries)</option>
                <option value="immediate_retry_2">Immediate Retry (2 retries)</option>
                <option value="no_retry">Disabled (Immediate Failure)</option>
              </select>
            </div>

            {/* Worker Concurrency */}
            <div className="space-y-1.5">
              <label className="text-[10px] uppercase font-mono tracking-wider text-darkMuted block">Celery Worker Thread Concurrency</label>
              <input
                type="number"
                disabled={!isAdmin}
                value={concurrency}
                onChange={(e) => setConcurrency(parseInt(e.target.value) || 0)}
                className={`w-full h-8 px-3 rounded bg-darkBg border text-xs text-darkText focus:outline-none focus:border-accentPrimary transition-colors disabled:opacity-50 ${
                  errors.concurrency ? 'border-accentDanger' : 'border-darkBorder'
                }`}
              />
              {errors.concurrency && <span className="text-[9px] text-accentDanger font-mono block">{errors.concurrency}</span>}
            </div>

            {/* Logging level */}
            <div className="space-y-1.5">
              <label className="text-[10px] uppercase font-mono tracking-wider text-darkMuted block">Output Logging Level</label>
              <select
                disabled={!isAdmin}
                value={logLevel}
                onChange={(e) => setLogLevel(e.target.value)}
                className="w-full h-8 px-2 rounded bg-darkBg border border-darkBorder text-xs text-darkText focus:outline-none focus:border-accentPrimary transition-colors disabled:opacity-50"
              >
                <option value="DEBUG">DEBUG (Detailed logs)</option>
                <option value="INFO">INFO (Normal logs)</option>
                <option value="WARNING">WARNING (Issues and alerts)</option>
                <option value="ERROR">ERROR (Severe failures)</option>
              </select>
            </div>

            {/* API Quota limits */}
            <div className="space-y-1.5">
              <label className="text-[10px] uppercase font-mono tracking-wider text-darkMuted block">Daily YouTube API Quota Limit (Max 100k)</label>
              <input
                type="number"
                disabled={!isAdmin}
                value={apiLimit}
                onChange={(e) => setApiLimit(parseInt(e.target.value) || 0)}
                className={`w-full h-8 px-3 rounded bg-darkBg border text-xs text-darkText focus:outline-none focus:border-accentPrimary transition-colors disabled:opacity-50 ${
                  errors.apiLimit ? 'border-accentDanger' : 'border-darkBorder'
                }`}
              />
              {errors.apiLimit && <span className="text-[9px] text-accentDanger font-mono block">{errors.apiLimit}</span>}
            </div>
          </div>

          {/* Action Row */}
          {isAdmin && (
            <div className="flex items-center justify-end border-t border-darkBorder pt-4 mt-6 flex-shrink-0">
              <Button
                type="submit"
                variant="primary"
                disabled={saveMutation.isPending}
              >
                <Save size={12} className="mr-1" />
                {saveMutation.isPending ? 'Saving Settings...' : 'Save Configuration'}
              </Button>
            </div>
          )}
        </form>
      )}
    </div>
  );
};
