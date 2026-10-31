import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export const BottomNav: React.FC = () => {
  const { user } = useAuth();
  const location = useLocation();

  if (!user) {
    return null;
  }

  const currentPath = location.pathname;

  // Role-appropriate destinations
  const homePath = '/';
  const trackerPath = user.is_handler ? '/admin/queue' : '/my-complaints';

  // Real route-based active tab highlighting
  const isHomeActive = currentPath === '/' || currentPath === '/dashboard';

  const isTrackerActive =
    currentPath.startsWith('/my-complaints') ||
    currentPath.startsWith('/complaints') ||
    currentPath.startsWith('/new-complaint') ||
    currentPath.startsWith('/admin/queue') ||
    currentPath.startsWith('/admin/issues') ||
    currentPath.startsWith('/admin/create-issue') ||
    currentPath === '/tracker';

  const isSettingsActive = currentPath === '/settings';

  return (
    <nav className="cv-bottom-nav" aria-label="Authenticated Navigation">
      <div className="cv-bottom-nav-inner">
        <Link
          to={homePath}
          className={`cv-bottom-nav-item ${isHomeActive ? 'active' : ''}`}
          aria-label="Home"
        >
          <i className={`bi ${isHomeActive ? 'bi-house-door-fill' : 'bi-house-door'}`}></i>
          <span>Home</span>
        </Link>

        <Link
          to={trackerPath}
          className={`cv-bottom-nav-item ${isTrackerActive ? 'active' : ''}`}
          aria-label="Tracker"
        >
          <i className="bi bi-card-checklist"></i>
          <span>Tracker</span>
        </Link>

        <Link
          to="/settings"
          className={`cv-bottom-nav-item ${isSettingsActive ? 'active' : ''}`}
          aria-label="Settings"
        >
          <i className={`bi ${isSettingsActive ? 'bi-gear-fill' : 'bi-gear'}`}></i>
          <span>Settings</span>
        </Link>
      </div>
    </nav>
  );
};

