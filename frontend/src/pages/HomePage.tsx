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

        // Compute counts from available public summaries
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
    <div>
      {/* Hero Header */}
      <div className="row align-items-center py-4 mb-4">
        <div className="col-lg-7">
          <span className="badge bg-primary-subtle text-primary border border-primary-subtle mb-2 px-3 py-1">
            <i className="bi bi-shield-check me-1"></i>Verified Campus Feedback & Accountability
          </span>
          <h1 className="display-5 fw-bold text-dark mt-2 mb-3">
            Campus Issues Resolved With Verified Submitter Feedback.
          </h1>
          <p className="lead text-secondary mb-4">
            A transparent platform for verified college students and staff to submit maintenance requests, report safety hazards, and confirm physical repairs with auditable resolution feedback.
          </p>

          <div className="d-flex flex-wrap gap-2">
            {user ? (
              <>
                <Link to="/new-complaint" className="btn btn-primary btn-lg px-4">
                  <i className="bi bi-plus-circle me-1"></i>Submit New Report
                </Link>
                <Link to="/my-complaints" className="btn btn-outline-secondary btn-lg px-4">
                  My Submissions
                </Link>
              </>
            ) : (
              <>
                <Link to="/register" className="btn btn-primary btn-lg px-4">
                  Register with College Email
                </Link>
                <Link to="/login" className="btn btn-outline-secondary btn-lg px-4">
                  Log In
                </Link>
              </>
            )}
          </div>
        </div>

        {/* Live Metrics Card */}
        <div className="col-lg-5 mt-4 mt-lg-0">
          <div className="card card-shadow border-0 bg-white p-4">
            <h5 className="fw-bold text-dark mb-3">
              <i className="bi bi-activity text-primary me-2"></i>Live Campus Activity
            </h5>
            <div className="d-flex justify-content-between align-items-center py-2 border-bottom">
              <span className="text-secondary">Total Submissions Received</span>
              <span className="badge bg-secondary fs-6">{stats.total_submissions}</span>
            </div>
            <div className="d-flex justify-content-between align-items-center py-2 border-bottom">
              <span className="text-secondary">Distinct Operational Issues</span>
              <span className="badge bg-primary fs-6">{stats.distinct_issues}</span>
            </div>
            <div className="d-flex justify-content-between align-items-center py-2">
              <span className="text-secondary">Issues Successfully Resolved</span>
              <span className="badge bg-success fs-6">{stats.resolved_issues}</span>
            </div>
            <div className="mt-3 text-center">
              <Link to="/public-issues" className="btn btn-sm btn-outline-primary w-100">
                View Public Issue Board
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* 3 Pillar Features */}
      <div className="row g-4 py-3 mb-5">
        <div className="col-md-4">
          <div className="card card-shadow h-100 p-3">
            <div className="card-body">
              <i className="bi bi-patch-check-fill text-success fs-1 mb-2"></i>
              <h5 className="card-title fw-bold">Verified Resolution Feedback</h5>
              <p className="card-text text-muted small">
                An issue is not labeled "confirmed resolved" merely by administrative declaration. Original verified submitters vote whether the fix was successful, preventing premature ticket closures.
              </p>
            </div>
          </div>
        </div>
        <div className="col-md-4">
          <div className="card card-shadow h-100 p-3">
            <div className="card-body">
              <i className="bi bi-eye-slash-fill text-primary fs-1 mb-2"></i>
              <h5 className="card-title fw-bold">Identity-Restricted Privacy</h5>
              <p className="card-text text-muted small">
                Submitter identities are concealed on ordinary operational dashboards to protect students. Administrators must supply an auditable operational justification to reveal identity.
              </p>
            </div>
          </div>
        </div>
        <div className="col-md-4">
          <div className="card card-shadow h-100 p-3">
            <div className="card-body">
              <i className="bi bi-diagram-3-fill text-warning fs-1 mb-2"></i>
              <h5 className="card-title fw-bold">Semantic Grouping & Explainability</h5>
              <p className="card-text text-muted small">
                Multilingual text embeddings and structured campus location matching surface duplicate or recurring reports. Reports are never deleted as duplicates; grouping is completely reversible.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Public Synthesized Issues Board */}
      <div className="card card-shadow mb-4">
        <div className="card-header bg-white py-3 d-flex justify-content-between align-items-center">
          <div>
            <h5 className="mb-0 text-dark">
              <i className="bi bi-kanban me-2"></i>Synthesized Campus Issues (Public Board)
            </h5>
            <small className="text-muted">Displays authorized operational summaries only. Raw personal descriptions and attachments remain restricted.</small>
          </div>
          <Link to="/public-issues" className="btn btn-sm btn-outline-secondary">
            View All
          </Link>
        </div>
        <div className="card-body p-0">
          {loading ? (
            <div className="p-4 text-center text-muted">Loading campus issues...</div>
          ) : issues.length > 0 ? (
            <div className="table-responsive">
              <table className="table table-hover align-middle mb-0">
                <thead className="table-light">
                  <tr>
                    <th style={{ width: '80px' }}>Issue</th>
                    <th>Summary Title</th>
                    <th>Location</th>
                    <th>Category</th>
                    <th>Priority</th>
                    <th>Operational Status</th>
                    <th>Submitter Feedback State</th>
                  </tr>
                </thead>
                <tbody>
                  {issues.map((iss) => (
                    <tr key={iss.id}>
                      <td><strong>#{iss.id}</strong></td>
                      <td>
                        <div className="fw-semibold text-dark">{iss.title}</div>
                        <small className="text-muted">
                          {iss.description.length > 110 ? iss.description.substring(0, 110) + '...' : iss.description}
                        </small>
                      </td>
                      <td>
                        <div>{iss.building}</div>
                        {iss.room && <small className="text-muted">{iss.room}</small>}
                      </td>
                      <td><span className="badge bg-light text-dark border">{iss.category}</span></td>
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
            </div>
          ) : (
            <div className="p-4 text-center text-muted">No synthesized public issues recorded yet.</div>
          )}
        </div>
      </div>
    </div>
  );
};

