import React from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export const Navbar: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const isActive = (path: string) => location.pathname === path;

  return (
    <nav className="navbar navbar-expand-lg app-navbar sticky-top">
      <div className="container">
        <Link className="navbar-brand" to="/">
          <i className="bi bi-megaphone-fill"></i>
          <span>CampusVoice</span>
        </Link>
        
        <button
          className="navbar-toggler border-0 shadow-none"
          type="button"
          data-bs-toggle="collapse"
          data-bs-target="#navContent"
        >
          <span className="navbar-toggler-icon"></span>
        </button>

        <div className="collapse navbar-collapse" id="navContent">
          <ul className="navbar-nav me-auto mb-2 mb-lg-0 ms-lg-3">
            <li className="nav-item">
              <Link
                className={`nav-link ${isActive('/public-issues') ? 'active' : ''}`}
                to="/public-issues"
              >
                Public Issues
              </Link>
            </li>

            {user && (
              <>
                {user.is_handler ? (
                  <>
                    <li className="nav-item">
                      <Link
                        className={`nav-link ${isActive('/admin/dashboard') ? 'active' : ''}`}
                        to="/admin/dashboard"
                      >
                        <i className="bi bi-graph-up me-1 text-primary"></i>Dashboard & Analytics
                      </Link>
                    </li>
                    <li className="nav-item">
                      <Link
                        className={`nav-link ${isActive('/admin/queue') ? 'active' : ''}`}
                        to="/admin/queue"
                      >
                        All Issues Queue
                      </Link>
                    </li>
                    {user.is_admin && (
                      <li className="nav-item">
                        <Link
                          className={`nav-link ${isActive('/admin/audit-log') ? 'active' : ''}`}
                          to="/admin/audit-log"
                        >
                          Audit Log
                        </Link>
                      </li>
                    )}
                  </>
                ) : (
                  <li className="nav-item">
                    <Link
                      className={`nav-link ${isActive('/my-complaints') ? 'active' : ''}`}
                      to="/my-complaints"
                    >
                      My Submissions
                    </Link>
                  </li>
                )}
              </>
            )}
          </ul>

          <ul className="navbar-nav ms-auto align-items-lg-center">
            {user ? (
              <li className="nav-item dropdown">
                <button
                  className="btn btn-sm btn-outline-secondary dropdown-toggle d-flex align-items-center gap-2"
                  type="button"
                  data-bs-toggle="dropdown"
                  style={{ borderColor: 'var(--border-strong)', backgroundColor: 'var(--bg-surface)' }}
                >
                  <i className="bi bi-person-circle text-secondary"></i>
                  <span className="fw-medium text-dark">{user.full_name}</span>
                  {user.is_admin ? (
                    <span className="badge bg-danger-subtle text-danger border border-danger-subtle" style={{ fontSize: '0.7rem', padding: '0.15rem 0.45rem' }}>
                      <i className="bi bi-shield-lock-fill me-1"></i>Admin
                    </span>
                  ) : user.is_handler ? (
                    <span className="badge bg-info-subtle text-primary border border-info-subtle" style={{ fontSize: '0.7rem', padding: '0.15rem 0.45rem' }}>
                      Handler
                    </span>
                  ) : user.is_verified ? (
                    <span className="cv-badge cv-badge-normal" style={{ fontSize: '0.7rem', padding: '0.1rem 0.4rem' }}>
                      Verified
                    </span>
                  ) : (
                    <span className="cv-badge cv-badge-review" style={{ fontSize: '0.7rem', padding: '0.1rem 0.4rem' }}>
                      Unverified
                    </span>
                  )}
                </button>
                <ul className="dropdown-menu dropdown-menu-end shadow-sm border" style={{ borderColor: 'var(--border-subtle)' }}>
                  <li className="dropdown-header text-muted small">
                    {user.email} &bull; <span className="text-capitalize">{user.role}</span>
                  </li>
                  {!user.is_verified && (
                    <li>
                      <Link className="dropdown-item text-warning" to="/verify-email">
                        <i className="bi bi-envelope-exclamation me-2"></i>Verify College Email
                      </Link>
                    </li>
                  )}
                  {user.is_handler ? (
                    <>
                      <li>
                        <Link className="dropdown-item py-2" to="/admin/dashboard">
                          <i className="bi bi-graph-up me-2 text-primary"></i>Executive Analytics Dashboard
                        </Link>
                      </li>
                      <li>
                        <Link className="dropdown-item py-2" to="/admin/queue">
                          <i className="bi bi-list-task me-2 text-secondary"></i>All Issues Queue
                        </Link>
                      </li>
                    </>
                  ) : (
                    <li>
                      <Link className="dropdown-item py-2" to="/my-complaints">
                        <i className="bi bi-collection me-2 text-secondary"></i>My Complaints
                      </Link>
                    </li>
                  )}
                  <li>
                    <Link className="dropdown-item py-2" to="/settings">
                      <i className="bi bi-gear me-2 text-secondary"></i>Account Settings
                    </Link>
                  </li>
                  <li><hr className="dropdown-divider" /></li>
                  <li>
                    <button className="dropdown-item text-danger py-2" onClick={handleLogout}>
                      <i className="bi bi-box-arrow-right me-2"></i>Log Out
                    </button>
                  </li>
                </ul>
              </li>
            ) : (
              <>
                <li className="nav-item">
                  <Link className="nav-link" to="/login">
                    Log In
                  </Link>
                </li>
                <li className="nav-item">
                  <Link className="btn btn-outline-secondary btn-sm" to="/register">
                    Register
                  </Link>
                </li>
              </>
            )}
          </ul>
        </div>
      </div>
    </nav>
  );
};
