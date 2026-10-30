import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { StatusBadge } from '../components/StatusBadge';

export const PublicIssuesPage: React.FC = () => {
  const [issues, setIssues] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadIssues() {
      try {
        const data = await api.get('/api/issues');
        setIssues(data.issues || []);
      } catch (err) {
        console.error('Failed to load public issues:', err);
      } finally {
        setLoading(false);
      }
    }
    loadIssues();
  }, []);

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h3 className="mb-1 text-dark">
            <i className="bi bi-kanban me-2"></i>Campus Synthesized Issues Board
          </h3>
          <p className="text-muted small mb-0">
            Public progress transparency. Shows verified operational issue summaries across campus facilities.
          </p>
        </div>
        <Link to="/new-complaint" className="btn btn-primary">
          <i className="bi bi-plus-circle me-1"></i>Report an Issue
        </Link>
      </div>

      {loading ? (
        <div className="card card-shadow p-5 text-center text-muted">
          Loading issues board...
        </div>
      ) : issues.length > 0 ? (
        <div className="card card-shadow">
          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0">
              <thead className="table-light">
                <tr>
                  <th style={{ width: '80px' }}>Issue</th>
                  <th>Summary Title & Scope</th>
                  <th>Building / Area</th>
                  <th>Category</th>
                  <th>Priority</th>
                  <th>Operational Status</th>
                  <th>Verified Feedback State</th>
                </tr>
              </thead>
              <tbody>
                {issues.map((issue) => (
                  <tr key={issue.id}>
                    <td><strong>#{issue.id}</strong></td>
                    <td>
                      <div className="fw-semibold text-dark">{issue.title}</div>
                      <small className="text-muted">{issue.description}</small>
                    </td>
                    <td>
                      <div>{issue.building}</div>
                      {issue.room && <small className="text-muted">{issue.room}</small>}
                    </td>
                    <td><span className="badge bg-light text-dark border">{issue.category}</span></td>
                    <td><StatusBadge type="priority" value={issue.priority} /></td>
                    <td><StatusBadge type="status" value={issue.status} /></td>
                    <td>
                      {issue.resolution_round_status ? (
                        <StatusBadge type="feedback_round" value={issue.resolution_round_status} />
                      ) : (
                        <span className="text-muted small">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="card card-shadow text-center p-5">
          <i className="bi bi-clipboard-check text-muted" style={{ fontSize: '3rem' }}></i>
          <h5 className="mt-3">No Public Issues</h5>
          <p className="text-muted small">No operational issues have been synthesized yet.</p>
        </div>
      )}
    </div>
  );
};

