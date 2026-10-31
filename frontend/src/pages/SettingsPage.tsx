import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export const SettingsPage: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [loggingOut, setLoggingOut] = useState(false);

  if (!user) {
    return null;
  }

  const handleLogout = async () => {
    setLoggingOut(true);
    try {
      await logout();
      navigate('/login', { replace: true });
    } catch (err) {
      console.error('Logout failed:', err);
      setLoggingOut(false);
    }
  };

  const getRoleBadge = () => {
    if (user.is_admin) {
      return <span className="cv-badge cv-badge-urgent">System Administrator</span>;
    }
    if (user.is_handler) {
      return <span className="cv-badge cv-badge-high">Operations Handler</span>;
    }
    return <span className="cv-badge cv-badge-low">Student / Campus User</span>;
  };

  return (
    <div className="row justify-content-center">
      <div className="col-12 col-md-9 col-lg-7">
        {/* Page Header */}
        <div className="mb-4">
          <h3 className="fw-bold text-dark mb-1">Account & Settings</h3>
          <p className="text-muted small mb-0">
            View your verified campus profile, credentials, and session controls.
          </p>
        </div>

        {/* Profile Card */}
        <div className="cv-card mb-4">
          <div className="cv-card-body p-4">
            <div className="d-flex align-items-center gap-3 mb-4">
              <div
                className="d-flex align-items-center justify-content-center rounded-circle bg-light border text-primary"
                style={{ width: '64px', height: '64px', fontSize: '1.75rem', borderColor: 'var(--border-subtle)' }}
              >
                <i className="bi bi-person-fill"></i>
              </div>
              <div className="flex-grow-1">
                <div className="d-flex align-items-center gap-2 flex-wrap mb-1">
                  <h5 className="fw-bold text-dark mb-0">{user.full_name}</h5>
                  {getRoleBadge()}
                </div>
                <div className="text-muted small font-monospace">{user.email}</div>
              </div>
            </div>

            <div className="list-group list-group-flush border-top border-bottom my-3">
              <div className="list-group-item px-0 py-3 d-flex justify-content-between align-items-center bg-transparent">
                <div>
                  <div className="fw-medium text-dark small">Account Verification</div>
                  <div className="text-muted small">
                    {user.is_verified
                      ? 'Verified institutional college domain'
                      : 'Verification required to submit complaints'}
                  </div>
                </div>
                {user.is_verified ? (
                  <span className="cv-badge cv-badge-resolved d-inline-flex align-items-center gap-1">
                    <i className="bi bi-patch-check-fill text-success"></i>
                    <span>Verified</span>
                  </span>
                ) : (
                  <Link to="/verify-email" className="btn btn-sm btn-outline-warning">
                    Verify Email
                  </Link>
                )}
              </div>

              <div className="list-group-item px-0 py-3 d-flex justify-content-between align-items-center bg-transparent">
                <div>
                  <div className="fw-medium text-dark small">User Account ID</div>
                  <div className="text-muted small">Unique campus directory reference</div>
                </div>
                <span className="font-monospace text-secondary fw-semibold">#{user.id}</span>
              </div>

              <div className="list-group-item px-0 py-3 d-flex justify-content-between align-items-center bg-transparent">
                <div>
                  <div className="fw-medium text-dark small">Access Level</div>
                  <div className="text-muted small">Assigned operational permissions</div>
                </div>
                <span className="text-capitalize text-dark fw-medium small">{user.role}</span>
              </div>
            </div>

            {/* Quick Actions / Role Views */}
            <div className="pt-2">
              <div className="text-muted small fw-semibold text-uppercase mb-2" style={{ fontSize: '0.75rem' }}>
                Quick Navigation
              </div>
              <div className="d-flex flex-wrap gap-2 mb-4">
                <Link to="/" className="btn btn-sm btn-outline-secondary">
                  <i className="bi bi-house-door me-1"></i>Home Dashboard
                </Link>
                <Link to={user.is_handler ? '/admin/queue' : '/my-complaints'} className="btn btn-sm btn-outline-secondary">
                  <i className="bi bi-card-checklist me-1"></i>{user.is_handler ? 'Operations Queue' : 'My Complaints'}
                </Link>
                {user.is_admin && (
                  <Link to="/admin/audit-log" className="btn btn-sm btn-outline-secondary">
                    <i className="bi bi-journal-text me-1"></i>Audit Trail
                  </Link>
                )}
                <Link to="/public-issues" className="btn btn-sm btn-outline-secondary">
                  <i className="bi bi-kanban me-1"></i>Public Issues
                </Link>
              </div>
            </div>

            {/* Sign Out Action */}
            <div className="pt-3 border-top">
              <button
                type="button"
                className="btn btn-outline-danger d-inline-flex align-items-center gap-2 w-100 justify-content-center py-2"
                onClick={handleLogout}
                disabled={loggingOut}
              >
                {loggingOut ? (
                  <>
                    <span className="spinner-border spinner-border-sm" role="status"></span>
                    <span>Signing Out...</span>
                  </>
                ) : (
                  <>
                    <i className="bi bi-box-arrow-right"></i>
                    <span>Log Out from Session</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

