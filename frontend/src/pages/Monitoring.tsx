import React from 'react';
import { Activity } from 'lucide-react';
import { StatusBadge } from '../components/UI';

export const Monitoring: React.FC = () => {
  return (
    <div className="space-y-6 select-none max-w-2xl mx-auto py-12 text-center bg-darkCard border border-darkBorder rounded p-6 shadow-subtle">
      <Activity className="text-accentPrimary mx-auto mb-3" size={36} />
      <h1 className="text-sm font-bold uppercase tracking-widest text-darkText mb-1">SYSTEM MONITORING ALERTS</h1>
      <p className="text-xs text-darkMuted leading-relaxed max-w-md mx-auto mb-4">
        This panel is designed for tracking crawler request delays, API failures, and rate limits. Detailed scheduler and celery worker states can be viewed in their respective subpanels.
      </p>
      <StatusBadge status="ACTIVE BACKGROUND MONITORING" type="primary" />
    </div>
  );
};
