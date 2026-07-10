import React from 'react';
import { Percent } from 'lucide-react';
import { StatusBadge } from '../components/UI';

export const Scoring: React.FC = () => {
  return (
    <div className="space-y-6 select-none max-w-2xl mx-auto py-12 text-center bg-darkCard border border-darkBorder rounded p-6 shadow-subtle">
      <Percent className="text-accentPrimary mx-auto mb-3" size={36} />
      <h1 className="text-sm font-bold uppercase tracking-widest text-darkText mb-1">NICHE QUALITY SCORING</h1>
      <p className="text-xs text-darkMuted leading-relaxed max-w-md mx-auto mb-4">
        This module scores German trading terminology relevancy. In Phase 2B – Community Intelligence Engine, scoring metrics will be expanded to encompass sentiment and external community score values.
      </p>
      <StatusBadge status="PHASE 2B PREPARATION" type="primary" />
    </div>
  );
};
