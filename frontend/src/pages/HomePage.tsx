import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useViewMode } from '../context/ViewModeContext';
import { StatusBadge } from '../components/StatusBadge';
import { AdminResolutionDashboard } from '../components/AdminResolutionDashboard';

export const HomePage: React.FC = () => {
  const { user, loading: authLoading } = useAuth();
  const { openSubmitModal } = useViewMode();
  const [issues, setIssues] = useState<any[]>([]);
  const [stats, setStats] = useState({
    total_submissions: 0,
    distinct_issues: 0,
    resolved_issues: 0,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const issuesRes = await api.get('/api/issues');
        const issueList = issuesRes.issues || [];
        setIssues(issueList.slice(0, 8));

        const resolved = issueList.filter((i: any) => i.status === 'resolved').length;
        setStats({
          total_submissions: issueList.reduce((acc: number, curr: any) => acc + (curr.linked_reports_count || 1), 0),
          distinct_issues: issueList.length,
          resolved_issues: resolved,
        });
      } catch (err) {
        console.error('Error fetching home data:', err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  // Role strictly fixed based on authenticated user profile:
  // Handlers and Admins automatically see the Admin Resolution Dashboard;
  // Students and guests see the Student Issue Tracker Portal.
  const isAdminView = Boolean(user && (user.is_handler || user.is_admin || user.role === 'admin' || user.role === 'handler'));

  if (authLoading) {
    return (
      <div className="py-5 text-center text-muted">
        <div className="spinner-border spinner-border-sm text-primary me-2" role="status"></div>
        <span>Loading workspace...</span>
      </div>
    );
  }

  return (
    <div className="py-2">
      {isAdminView ? (
        <AdminResolutionDashboard />
      ) : (
        <>
          {/* Editorial Minimalist Hero Header */}
          <div className="row align-items-center pt-2 pb-4 mb-5">
            <div className="col-lg-8">
              <h1
                className="text-dark mb-3"
                style={{
                  fontSize: 'clamp(2.75rem, 5vw, 3.85rem)',
                  fontWeight: 800,
                  lineHeight: 1.12,
                  letterSpacing: '-0.04em',
                }}
              >
                Report Track Resolve
              </h1>
              <p
                className="mb-4"
                style={{
                  fontSize: '1.3rem',
                  fontWeight: 500,
                  color: '#475569',
                  lineHeight: 1.5,
                  maxWidth: '640px',
                }}
              >
                Report campus issues and track their progress.
              </p>

              {user && (user.is_handler || user.is_admin || user.role === 'admin' || user.role === 'handler') ? (
                <div className="d-flex flex-column gap-2">
                  <div className="d-flex flex-wrap gap-3">
                    <Link
                      to="/admin/dashboard"
                      className="btn btn-primary btn-lg px-4 py-2 d-inline-flex align-items-center gap-2 fs-6 fw-semibold shadow-sm"
                    >
                      <i className="bi bi-graph-up-arrow"></i>
                      <span>Executive Dashboard</span>
                    </Link>
                    <Link
                      to="/admin/queue"
                      className="btn btn-outline-primary btn-lg px-4 py-2 d-inline-flex align-items-center gap-2 fs-6 fw-medium"
                    >
                      <i className="bi bi-list-task"></i>
                      <span>All Issues Queue</span>
                    </Link>
                    <Link
                      to="/admin/create-issue"
                      className="btn btn-outline-secondary btn-lg px-4 py-2 fs-6 fw-medium"
                    >
                      <span>Create Master Issue</span>
                    </Link>
                  </div>
                  <div className="text-muted small mt-1">
                    <i className="bi bi-shield-check text-success me-1"></i>
                    Signed in as <strong>{user.full_name}</strong> ({user.is_admin ? 'Administrator' : 'Handler'}). Administrative accounts manage and resolve campus issues.
                  </div>
                </div>
              ) : (
                <div className="d-flex flex-wrap gap-3">
                  <button
                    type="button"
                    className="btn btn-primary btn-lg px-4 py-2 d-inline-flex align-items-center gap-2 fs-6 fw-semibold shadow-sm"
                    onClick={openSubmitModal}
                  >
                    <i className="bi bi-plus-lg"></i>
                    <span>Submit Report</span>
                  </button>
                  <Link
                    to={user ? "/my-complaints" : "/login"}
                    className="btn btn-outline-secondary btn-lg px-4 py-2 fs-6 fw-medium"
                  >
                    My Reports
                  </Link>
                </div>
              )}
            </div>

        {/* Overview Metrics Widget */}
        <div className="col-lg-4 mt-4 mt-lg-0">
          <div className="cv-card p-4">
            <div className="d-flex justify-content-between align-items-center mb-3">
              <span className="small fw-semibold text-secondary text-uppercase" style={{ letterSpacing: '0.04em' }}>
                Campus Overview
              </span>
            </div>

            <div className="d-flex justify-content-between align-items-baseline py-2 border-bottom">
              <span className="small text-secondary">Reports</span>
              <span className="fw-bold text-dark fs-5">{stats.total_submissions}</span>
            </div>
            <div className="d-flex justify-content-between align-items-baseline py-2 border-bottom">
              <span className="small text-secondary">Issues</span>
              <span className="fw-bold text-dark fs-5">{stats.distinct_issues}</span>
            </div>
            <div className="d-flex justify-content-between align-items-baseline py-2 mb-3">
              <span className="small text-secondary">Resolved</span>
              <span className="fw-bold text-success fs-5">{stats.resolved_issues}</span>
            </div>

            <Link to="/public-issues" className="btn btn-sm btn-outline-secondary w-100">
              View Issues
            </Link>
          </div>
        </div>
      </div>

      {/* 3 Core Architectural Pillars */}
      <div className="row g-3 mb-5">
        <div className="col-md-4">
          <div className="cv-card p-4 h-100">
            <div className="text-primary mb-3">
              <i className="bi bi-check2-circle fs-3"></i>
            </div>
            <h5 className="fw-bold text-dark mb-2 fs-6">Resolution Feedback</h5>
            <ul className="text-secondary small mb-0 ps-3">
              <li>Review the reported fix.</li>
              <li>Mark fixed, partial, or not fixed.</li>
            </ul>
          </div>
        </div>

        <div className="col-md-4">
          <div className="cv-card p-4 h-100">
            <div className="text-primary mb-3">
              <i className="bi bi-shield-lock fs-3"></i>
            </div>
            <h5 className="fw-bold text-dark mb-2 fs-6">Protected Identity</h5>
            <ul className="text-secondary small mb-0 ps-3">
              <li>Identity hidden in public views.</li>
              <li>Restricted access with audit history.</li>
            </ul>
          </div>
        </div>

        <div className="col-md-4">
          <div className="cv-card p-4 h-100">
            <div className="text-primary mb-3">
              <i className="bi bi-diagram-3 fs-3"></i>
            </div>
            <h5 className="fw-bold text-dark mb-2 fs-6">Related Reports</h5>
            <ul className="text-secondary small mb-0 ps-3">
              <li>Review similar reports together.</li>
              <li>Keep original submissions.</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Public Synthesized Issues Board */}
      <div className="cv-card mb-4">
        <div className="cv-card-header d-flex justify-content-between align-items-center">
          <div>
            <h5 className="mb-0 text-dark fs-6 fw-bold">Public Operational Issues</h5>
            <small className="text-muted">Approved summaries of campus issues currently tracked by facilities.</small>
          </div>
          <Link to="/public-issues" className="btn btn-sm btn-outline-secondary">
            View Issues
          </Link>
        </div>

        <div className="table-responsive">
          {loading ? (
            <div className="p-4 text-center text-muted small">Loading campus issues...</div>
          ) : issues.length > 0 ? (
            <table className="cv-table">
              <thead>
                <tr>
                  <th style={{ width: '80px' }}>Issue</th>
                  <th>Summary & Scope</th>
                  <th>Location</th>
                  <th>Category</th>
                  <th>Priority</th>
                  <th>Status</th>
                  <th>Submitter Confirmation</th>
                </tr>
              </thead>
              <tbody>
                {issues.map((iss) => (
                  <tr key={iss.id}>
                    <td><span className="fw-semibold text-dark">#{iss.id}</span></td>
                    <td>
                      <div className="fw-semibold text-dark">{iss.title}</div>
                      <small className="text-muted">
                        {iss.description.length > 95 ? iss.description.substring(0, 95) + '...' : iss.description}
                      </small>
                    </td>
                    <td>
                      <div>{iss.building}</div>
                      {iss.room && <small className="text-muted">{iss.room}</small>}
                    </td>
                    <td>
                      <span className="cv-badge cv-badge-low">{iss.category}</span>
                    </td>
                    <td><StatusBadge type="priority" value={iss.priority} /></td>
                    <td><StatusBadge type="status" value={iss.status} /></td>
                    <td>
                      {iss.resolution_round_status ? (
                        <StatusBadge type="feedback_round" value={iss.resolution_round_status} />
                      ) : (
                        <span className="text-muted small">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="p-4 text-center text-muted small">No operational issues recorded yet.</div>
          )}
        </div>
      </div>
    </>
    )}
  </div>
);
};
