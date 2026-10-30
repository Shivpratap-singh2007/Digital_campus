import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { StatusBadge } from '../components/StatusBadge';

export const HomePage: React.FC = () => {
  const { user } = useAuth();
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

  return (
    <div className="py-2">
      {/* Editorial Minimalist Hero Header */}
      <div className="row align-items-center py-4 mb-5">
        <div className="col-lg-8">
          <div className="d-inline-flex align-items-center gap-2 cv-badge cv-badge-low mb-3">
            <span className="text-secondary fw-semibold">Campus Operations Platform</span>
          </div>
          <h1 className="display-6 fw-bold text-dark mb-3" style={{ letterSpacing: '-0.03em' }}>
            Campus Maintenance with Verified Submitter Resolution.
          </h1>
          <p className="lead text-secondary mb-4" style={{ fontSize: '1.05rem', maxWidth: '640px' }}>
            A transparent system for college students and staff to submit maintenance requests, report facilities safety hazards, and independently verify physical repairs with structured resolution feedback.
          </p>

          <div className="d-flex flex-wrap gap-2">
            {user ? (
              <>
                <Link to="/new-complaint" className="btn btn-primary d-inline-flex align-items-center gap-2">
                  <i className="bi bi-plus-lg"></i>
                  <span>Submit Report</span>
                </Link>
                <Link to="/my-complaints" className="btn btn-outline-secondary">
                  My Submissions
                </Link>
              </>
            ) : (
              <>
                <Link to="/register" className="btn btn-primary">
                  Register with College Email
                </Link>
                <Link to="/login" className="btn btn-outline-secondary">
                  Log In
                </Link>
              </>
            )}
          </div>
        </div>

        {/* Live Metrics Widget */}
        <div className="col-lg-4 mt-4 mt-lg-0">
          <div className="cv-card p-4">
            <div className="d-flex justify-content-between align-items-center mb-3">
              <span className="small fw-semibold text-secondary text-uppercase" style={{ letterSpacing: '0.04em' }}>
                System Activity
              </span>
              <span className="cv-badge cv-badge-normal">Live</span>
            </div>

            <div className="d-flex justify-content-between align-items-baseline py-2 border-bottom">
              <span className="small text-secondary">Total Submissions</span>
              <span className="fw-bold text-dark fs-5">{stats.total_submissions}</span>
            </div>
            <div className="d-flex justify-content-between align-items-baseline py-2 border-bottom">
              <span className="small text-secondary">Distinct Operational Issues</span>
              <span className="fw-bold text-dark fs-5">{stats.distinct_issues}</span>
            </div>
            <div className="d-flex justify-content-between align-items-baseline py-2 mb-3">
              <span className="small text-secondary">Resolved Issues</span>
              <span className="fw-bold text-success fs-5">{stats.resolved_issues}</span>
            </div>

            <Link to="/public-issues" className="btn btn-sm btn-outline-secondary w-100">
              Browse Public Board &rarr;
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
            <h5 className="fw-bold text-dark mb-2 fs-6">Verified Resolution Feedback</h5>
            <p className="text-secondary small mb-0">
              Administrative closures remain provisional until original submitters independently evaluate physical repairs as Fixed, Partially fixed, or Not fixed.
            </p>
          </div>
        </div>

        <div className="col-md-4">
          <div className="cv-card p-4 h-100">
            <div className="text-primary mb-3">
              <i className="bi bi-shield-lock fs-3"></i>
            </div>
            <h5 className="fw-bold text-dark mb-2 fs-6">Identity-Restricted Privacy</h5>
            <p className="text-secondary small mb-0">
              Submitter personal details are masked in operational queues. Disclosures require an explicitly audited justification recorded before information retrieval.
            </p>
          </div>
        </div>

        <div className="col-md-4">
          <div className="cv-card p-4 h-100">
            <div className="text-primary mb-3">
              <i className="bi bi-diagram-3 fs-3"></i>
            </div>
            <h5 className="fw-bold text-dark mb-2 fs-6">Reversible Semantic Grouping</h5>
            <p className="text-secondary small mb-0">
              Duplicate reports are clustered into underlying master tasks using multilingual embeddings and structured room proximity without deleting original submissions.
            </p>
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
            View All Issues
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
    </div>
  );
};
