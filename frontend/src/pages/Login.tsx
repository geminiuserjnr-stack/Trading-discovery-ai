import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import type { UserRole } from '../context/AuthContext';
import { ShieldCheck, User } from 'lucide-react';
import { Button } from '../components/UI';

export const Login: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState('trader_elite');
  const [role, setRole] = useState<UserRole>('Admin');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    login(username, role);
    navigate('/');
  };

  return (
    <div className="min-h-screen bg-darkBg text-darkText flex items-center justify-center font-mono p-4">
      <div className="w-full max-w-sm bg-darkCard border border-darkBorder rounded p-6 shadow-subtle space-y-6">
        {/* Branding header */}
        <div className="text-center space-y-2 border-b border-darkBorder pb-4">
          <div className="w-10 h-10 rounded bg-accentPrimary flex items-center justify-center font-bold text-darkBg text-lg mx-auto">
            Y
          </div>
          <h1 className="text-sm font-bold uppercase tracking-widest text-darkText">
            YOUTUBE DISCOVERY ENGINE
          </h1>
          <p className="text-[10px] text-darkMuted uppercase tracking-wider">
            German Trading Community Intelligence Portal
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-[10px] uppercase font-mono tracking-wider text-darkMuted block">Username / Handle</label>
            <div className="relative">
              <div className="absolute inset-y-0 left-3 flex items-center pointer-events-none text-darkMuted">
                <User size={14} />
              </div>
              <input
                type="text"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full h-9 pl-9 pr-4 rounded bg-darkBg border border-darkBorder text-xs text-darkText focus:outline-none focus:border-accentPrimary transition-colors"
                placeholder="Enter handle..."
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-[10px] uppercase font-mono tracking-wider text-darkMuted block">User Access Role</label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setRole('Admin')}
                className={`h-9 rounded font-bold uppercase tracking-wider text-xs border transition-colors ${
                  role === 'Admin'
                    ? 'bg-accentPrimary/10 border-accentPrimary text-accentPrimary'
                    : 'bg-darkBg border-darkBorder text-darkMuted hover:text-darkText'
                }`}
              >
                Admin
              </button>
              <button
                type="button"
                onClick={() => setRole('Viewer')}
                className={`h-9 rounded font-bold uppercase tracking-wider text-xs border transition-colors ${
                  role === 'Viewer'
                    ? 'bg-accentPrimary/10 border-accentPrimary text-accentPrimary'
                    : 'bg-darkBg border-darkBorder text-darkMuted hover:text-darkText'
                }`}
              >
                Viewer
              </button>
            </div>
          </div>

          <Button
            type="submit"
            variant="primary"
            className="w-full h-9 mt-4"
          >
            <ShieldCheck size={14} /> Authenticate Session
          </Button>
        </form>

        {/* Footer info */}
        <div className="text-center pt-2 text-[9px] text-darkMuted uppercase">
          Secured Sandbox Instance Only
        </div>
      </div>
    </div>
  );
};
