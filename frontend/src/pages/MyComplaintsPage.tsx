import React, { useEffect, useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { StatusBadge } from '../components/StatusBadge';
import { useAuth } from '../context/AuthContext';

export const MyComplaintsPage: React.FC = () => {
  const { user } = useAuth();
  const [complaints, setComplaints] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [filterType, setFilterType] = useState<string>('');

  useEffect(() => {
    async function loadComplaints() {
      try {
        const data = await api.get('/api/complaints');
        setComplaints(data.complaints || []);
      } catch (err) {
        console.error('Failed to load user complaints:', err);
      } finally {
        setLoading(false);
      }
    }
    loadComplaints();
  }, []);

  const filtered = useMemo(() => {
    if (!filterType) return complaints;
    return complaints.filter((c) => c.submission_type === filterType);
  }, [complaints, filterType]);

  return (
    <div>
      {/* Page Header */}
      <div className="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3 mb-4">
        <div>
          <div className="d-flex align-items-center gap-2 mb-1">
            <h3 className="mb-0 fw-bold">My Submissions</h3>
            <span className="cv-badge cv-badge-low">{complaints.length} Total</span>
          </div>
          <p className="text-muted small mb-0">
            Track operational status progression and submit verified feedback once repairs are marked resolved.
          </p>
        </div>
        <Link to="/new-complaint" className="btn btn-primary d-inline-flex align-items-center gap-2">
          <i className="bi bi-plus-lg"></i>
          <span>New Submission</span>
        </Link>
      </div>

      {/* Unverified Email Alert */}
      {!user?.is_verified && (
        <div className="cv-card mb-4 border-warning bg-white">
          <div className="cv-card-body p-3 d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-2">
            <div className="d-flex align-items-center gap-2">
              <i className="bi bi-exclamation-triangle text-warning fs-5"></i>
              <div>
                <span className="fw-semibold text-dark">Email Verification Required:</span>{' '}
                <span className="text-secondary small">
                  Verify your campus domain email address before submitting new complaints or suggestions.
                </span>
              </div>
            </div>
            <Link to="/verify-email" className="btn btn-outline-secondary btn-sm">
              Verify Email Address
            </Link>
          </div>
        </div>
      )}

      {/* Filter Tabs if complaints exist */}
      {complaints.length > 0 && (
        <div className="d-flex gap-2 mb-3">
          <button
            type="button"
            className={`btn btn-sm ${filterType === '' ? 'btn-primary' : 'btn-outline-secondary'}`}
            onClick={() => setFilterType('')}
          >
            All ({complaints.length})
          </button>
          <button
            type="button"
            className={`btn btn-sm ${filterType === 'complaint' ? 'btn-primary' : 'btn-outline-secondary'}`}
            onClick={() => setFilterType('complaint')}
          >
            Complaints ({complaints.filter((c) => c.submission_type === 'complaint').length})
          </button>
          <button
            type="button"
            className={`btn btn-sm ${filterType === 'suggestion' ? 'btn-primary' : 'btn-outline-secondary'}`}
            onClick={() => setFilterType('suggestion')}
          >
            Suggestions ({complaints.filter((c) => c.submission_type === 'suggestion').length})
          </button>
        </div>
      )}

      {/* Complaints Table */}
      {loading ? (
        <div className="cv-card p-5 text-center text-muted">
          <div className="spinner-border spinner-border-sm text-secondary me-2" role="status"></div>
          Loading your submissions...
        </div>
      ) : filtered.length > 0 ? (
        <div className="cv-card overflow-hidden">
          <div className="table-responsive">
            <table className="cv-table">
              <thead>
                <tr>
                  <th style={{ width: '80px' }}>Ref ID</th>
                  <th>Type & Title</th>
                  <th>Category</th>
                  <th>Campus Location</th>
                  <th>Priority</th>
                  <th>Status</th>
                  <th>Resolution Feedback</th>
                  <th className="text-end" style={{ width: '100px' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((c) => (
                  <tr key={c.id}>
                    <td>
                      <span className="font-monospace fw-semibold text-secondary">#{c.id}</span>
                    </td>
                    <td style={{ maxWidth: '320px' }}>
                      <div className="d-flex align-items-center gap-1 mb-1">
                        <span className="cv-badge cv-badge-low text-capitalize" style={{ fontSize: '0.7rem' }}>
                          {c.submission_type}
                        </span>
                        <Link
                          to={`/complaints/${c.id}`}
                          className="fw-semibold text-dark text-decoration-none text-truncate"
                          style={{ maxWidth: '240px' }}
                        >
                          {c.title}
                        </Link>
                      </div>
                      <div className="text-muted small">
                        {new Date(c.created_at).toLocaleDateString(undefined, {
                          year: 'numeric',
                          month: 'short',
                          day: 'numeric',
                        })}
                      </div>
                    </td>
                    <td>
                      <span className="cv-badge cv-badge-low">{c.display_category}</span>
                    </td>
                    <td>
                      <div className="fw-medium text-dark">{c.building}</div>
                      {c.room && <div className="text-muted small">{c.room}</div>}
                    </td>
                    <td>
                      <StatusBadge type="priority" value={c.priority} />
                    </td>
                    <td>
                      <StatusBadge type="status" value={c.status} />
                    </td>
                    <td>
                      {c.linked_issue_status === 'resolved' ? (
                        <Link
                          to={`/complaints/${c.id}#feedback`}
                          className="btn btn-sm btn-outline-secondary text-success border-success"
                        >
                          <i className="bi bi-patch-check me-1"></i>Give Feedback
                        </Link>
                      ) : (
                        <span className="text-muted small">—</span>
                      )}
                    </td>
                    <td className="text-end">
                      <Link to={`/complaints/${c.id}`} className="btn btn-sm btn-outline-secondary">
                        View
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="cv-card text-center p-5">
          <div className="text-muted mb-2">
            <i className="bi bi-inbox" style={{ fontSize: '2.5rem' }}></i>
          </div>
          <h5 className="fw-semibold text-dark mb-1">No Submissions Found</h5>
          <p className="text-muted small mb-3">
            {complaints.length === 0
              ? "You haven't submitted any campus complaints or suggestions yet."
              : 'No submissions match the selected filter category.'}
          </p>
          <Link to="/new-complaint" className="btn btn-primary btn-sm">
            Submit Your First Report
          </Link>
        </div>
      )}
    </div>
  );
};
