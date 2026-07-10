import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { AuthProvider, useAuth } from './context/AuthContext';
import { ToastProvider } from './context/ToastContext';
import { Shell } from './layouts/Shell';

// Import Pages
import { Login } from './pages/Login';
import { DashboardHome } from './pages/DashboardHome';
import { Channels } from './pages/Channels';
import { Videos } from './pages/Videos';
import { Phrases } from './pages/Phrases';
import { Queries } from './pages/Queries';
import { DiscoveryFeed } from './pages/DiscoveryFeed';
import { Communities } from './pages/Communities';
import { Scoring } from './pages/Scoring';
import { Monitoring } from './pages/Monitoring';
import { Analytics } from './pages/Analytics';
import { SchedulerMonitor } from './pages/SchedulerMonitor';
import { WorkerMonitor } from './pages/WorkerMonitor';
import { LogsViewer } from './pages/LogsViewer';
import { Settings } from './pages/Settings';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

// Guard component to enforce authentication and routing
const AuthenticatedShell: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  return <Shell>{children}</Shell>;
};

const AnonymousRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated } = useAuth();
  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
};

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ToastProvider>
          <BrowserRouter>
            <Routes>
              {/* Anonymous Route */}
              <Route
                path="/login"
                element={
                  <AnonymousRoute>
                    <Login />
                  </AnonymousRoute>
                }
              />

              {/* Secure App Shell Routes */}
              <Route
                path="/"
                element={
                  <AuthenticatedShell>
                    <DashboardHome />
                  </AuthenticatedShell>
                }
              />
              <Route
                path="/channels"
                element={
                  <AuthenticatedShell>
                    <Channels />
                  </AuthenticatedShell>
                }
              />
              <Route
                path="/videos"
                element={
                  <AuthenticatedShell>
                    <Videos />
                  </AuthenticatedShell>
                }
              />
              <Route
                path="/phrases"
                element={
                  <AuthenticatedShell>
                    <Phrases />
                  </AuthenticatedShell>
                }
              />
              <Route
                path="/queries"
                element={
                  <AuthenticatedShell>
                    <Queries />
                  </AuthenticatedShell>
                }
              />
              <Route
                path="/feed"
                element={
                  <AuthenticatedShell>
                    <DiscoveryFeed />
                  </AuthenticatedShell>
                }
              />
              <Route
                path="/communities"
                element={
                  <AuthenticatedShell>
                    <Communities />
                  </AuthenticatedShell>
                }
              />
              <Route
                path="/scoring"
                element={
                  <AuthenticatedShell>
                    <Scoring />
                  </AuthenticatedShell>
                }
              />
              <Route
                path="/monitoring"
                element={
                  <AuthenticatedShell>
                    <Monitoring />
                  </AuthenticatedShell>
                }
              />
              <Route
                path="/analytics"
                element={
                  <AuthenticatedShell>
                    <Analytics />
                  </AuthenticatedShell>
                }
              />
              <Route
                path="/scheduler"
                element={
                  <AuthenticatedShell>
                    <SchedulerMonitor />
                  </AuthenticatedShell>
                }
              />
              <Route
                path="/workers"
                element={
                  <AuthenticatedShell>
                    <WorkerMonitor />
                  </AuthenticatedShell>
                }
              />
              <Route
                path="/logs"
                element={
                  <AuthenticatedShell>
                    <LogsViewer />
                  </AuthenticatedShell>
                }
              />
              <Route
                path="/settings"
                element={
                  <AuthenticatedShell>
                    <Settings />
                  </AuthenticatedShell>
                }
              />

              {/* Catch-all fallback */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </BrowserRouter>
        </ToastProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
