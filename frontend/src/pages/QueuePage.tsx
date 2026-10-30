import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { StatusBadge } from '../components/StatusBadge';
import { useAuth } from '../context/AuthContext';

export const QueuePage: React.FC = () => {
  const { user } = useAuth();

  const [complaints, setComplaints] = useState<any[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [locations, setLocations] = useState<string[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  // Filters
  const [filterCategory, setFilterCategory] = useState('');
  const [filterBuilding, setFilterBuilding] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [filterPriority, setFilterPriority] = useState('');

  // Identity reveal modal state
  const [selectedComplaintId, setSelectedComplaintId] = useState<number | null>(null);
  const [justification, setJustification] = useState('');
  const [revealSubmitting, setRevealSubmitting] = useState(false);
  const [revealResult, setRevealResult] = useState<any | null>(null);
  const [revealError, setRevealError] = useState('');

  const loadQueue = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filterCategory) params.append('category', filterCategory);
      if (filterBuilding) params.append('building', filterBuilding);
      if (filterStatus) params.append('status', filterStatus);
      if (filterPriority) params.append('priority', filterPriority);

      const data = await api.get(`/api/admin/queue?${params.toString()}`);
      setComplaints(data.complaints || []);
      setCategories(data.available_categories || []);
      setLocations(data.available_locations || []);
    } catch (err) {
      console.error('Failed to load queue:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadQueue();
  }, [filterCategory, filterBuilding, filterStatus, filterPriority]);

  const handleRetryAnalysis = async (complaintId: number) => {
    try {
      await api.post(`/api/complaints/${complaintId}/retry-analysis`);
      await loadQueue();
    } catch (err: any) {
      alert(err.message || 'Retry analysis failed.');
    }
  };

  const handleRevealIdentity = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedComplaintId) return;

    setRevealSubmitting(true);
    setRevealError('');

    try {
      const res = await api.post(`/api/admin/complaint/${selectedComplaintId}/reveal-identity`, {
        justification,
      });
      setRevealResult(res.identity);
      setSelectedComplaintId(null);
      setJustification('');
    } catch (err: any) {
      setRevealError(err.message || 'Identity reveal failed.');
    } finally {
      setRevealSubmitting(false);
    }
  };

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h3 className="mb-1 text-dark">
            <i className="bi bi-list-task me-2"></i>Campus Operations & Complaints Queue
          </h3>
          <p className="text-muted small mb-0">
            Submitter identities are concealed in this view. Use audited reveal actions only when required for safety follow-up.
          </p>
        </div>
        <Link to="/admin/create-issue" className="btn btn-outline-primary">
          <i className="bi bi-plus-circle me-1"></i>Create Synthesized Issue
        </Link>
      </div>

      {revealResult && (
        <div className="alert alert-warning alert-dismissible fade show mb-4" role="alert">
          <h6 className="alert-heading fw-bold">
            <i className="bi bi-shield-lock-fill me-1"></i>Disclosed Submitter Identity (Logged under Audit Event #{revealResult.audit_id})
          </h6>
          <p className="mb-0 small">
            <strong>Full Name:</strong> {revealResult.full_name} &bull;{' '}
            <strong>Email:</strong> {revealResult.email} &bull;{' '}
            <strong>User ID:</strong> #{revealResult.user_id}
          </p>
          <button
            type="button"
            className="btn-close"
            onClick={() => setRevealResult(null)}
            aria-label="Close"
          ></button>
        </div>
      )}

      {/* Filter Toolbar */}
      <div className="card card-shadow mb-4">
        <div className="card-body p-3">
          <div className="row g-2 align-items-end">
            <div className="col-md-3">
              <label className="form-label small fw-semibold">Category</label>
              <select
                className="form-select form-select-sm"
                value={filterCategory}
                onChange={(e) => setFilterCategory(e.target.value)}
              >
                <option value="">All Categories</option>
                {categories.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
            <div className="col-md-3">
              <label className="form-label small fw-semibold">Building / Location</label>
              <select
                className="form-select form-select-sm"
                value={filterBuilding}
                onChange={(e) => setFilterBuilding(e.target.value)}
              >
                <option value="">All Locations</option>
                {locations.map((loc) => (
                  <option key={loc} value={loc}>{loc}</option>
                ))}
              </select>
            </div>
            <div className="col-md-2">
              <label className="form-label small fw-semibold">Status</label>
              <select
                className="form-select form-select-sm"
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
              >
                <option value="">All Statuses</option>
                <option value="submitted">Submitted</option>
                <option value="under_review">Under Review</option>
                <option value="in_progress">In Progress</option>
                <option value="resolved">Resolved</option>
              </select>
            </div>
            <div className="col-md-2">
              <label className="form-label small fw-semibold">Priority</label>
              <select
                className="form-select form-select-sm"
                value={filterPriority}
                onChange={(e) => setFilterPriority(e.target.value)}
              >
                <option value="">All Priorities</option>
                <option value="Urgent review">Urgent review</option>
                <option value="High">High</option>
                <option value="Normal">Normal</option>
                <option value="Low">Low</option>
              </select>
            </div>
            <div className="col-md-2">
              <button
                type="button"
                className="btn btn-outline-secondary btn-sm w-100"
                onClick={() => {
                  setFilterCategory('');
                  setFilterBuilding('');
                  setFilterStatus('');
                  setFilterPriority('');
                }}
              >
                <i className="bi bi-arrow-counterclockwise me-1"></i>Reset
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Queue Table */}
      {loading ? (
        <div className="card card-shadow p-5 text-center text-muted">
          Loading operations queue...
        </div>
      ) : complaints.length > 0 ? (
        <div className="card card-shadow">
          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0">
              <thead className="table-light">
                <tr>
                  <th style={{ width: '70px' }}>ID</th>
                  <th>Type & Title</th>
                  <th>Submitter Reference</th>
                  <th>Location</th>
                  <th>Category</th>
                  <th>Priority</th>
                  <th>Status / AI</th>
                  <th className="text-end" style={{ minWidth: '150px' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {complaints.map((c) => (
                  <tr key={c.id}>
                    <td><strong>#{c.id}</strong></td>
                    <td>
                      <div>
                        <span className="badge bg-secondary text-capitalize me-1">{c.submission_type}</span>
                        <Link to={`/complaints/${c.id}`} className="fw-semibold text-decoration-none">
                          {c.title}
                        </Link>
                      </div>
                      <small className="text-muted">
                        {new Date(c.created_at).toLocaleString()}
                      </small>
                    </td>
                    <td>
                      {/* Submitter Identity Concealed */}
                      <span className="badge bg-secondary-subtle text-secondary border">
                        <i className="bi bi-person-lock me-1"></i>{c.anonymous_submitter}
                      </span>
                    </td>
                    <td>
                      <div>{c.building}</div>
                      {c.room && <small className="text-muted">{c.room}</small>}
                    </td>
                    <td>
                      <div><span className="badge bg-light text-dark border">{c.display_category}</span></div>
                      {c.suggested_category && c.suggested_category !== c.user_category && (
                        <small className="text-primary d-block">AI: {c.suggested_category}</small>
                      )}
                    </td>
                    <td><StatusBadge type="priority" value={c.display_priority} /></td>
                    <td>
                      <div><StatusBadge type="status" value={c.status} /></div>
                      <small className="text-muted">
                        {c.analysis_state === 'needs_review' ? (
                          <span className="text-danger fw-semibold">Needs Review</span>
                        ) : (
                          c.analysis_state
                        )}
                      </small>
                    </td>
                    <td className="text-end">
                      <div className="btn-group btn-group-sm">
                        <Link to={`/complaints/${c.id}`} className="btn btn-outline-primary" title="View details">
                          View
                        </Link>
                        <Link
                          to={`/admin/create-issue?seed_id=${c.id}`}
                          className="btn btn-outline-secondary"
                          title="Create master issue"
                        >
                          <i className="bi bi-folder-plus"></i>
                        </Link>
                        <button
                          type="button"
                          className="btn btn-outline-info"
                          title="Re-run AI analysis"
                          onClick={() => handleRetryAnalysis(c.id)}
                        >
                          <i className="bi bi-arrow-repeat"></i>
                        </button>
                        {user?.is_admin && (
                          <button
                            type="button"
                            className="btn btn-outline-danger"
                            title="Reveal submitter identity (audited)"
                            onClick={() => {
                              setSelectedComplaintId(c.id);
                              setJustification('');
                              setRevealError('');
                            }}
                          >
                            <i className="bi bi-shield-lock"></i>
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="card card-shadow text-center p-5">
          <i className="bi bi-check-circle text-success" style={{ fontSize: '3rem' }}></i>
          <h5 className="mt-3">No Complaints Match Filters</h5>
          <p className="text-muted small">All operational queues are clear or no complaints match current filter settings.</p>
        </div>
      )}

      {/* Identity Reveal Modal (Admin Only) */}
      {selectedComplaintId && (
        <div className="modal show d-block" tabIndex={-1} style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog">
            <div className="modal-content">
              <form onSubmit={handleRevealIdentity}>
                <div className="modal-header bg-danger text-white">
                  <h5 className="modal-title">
                    <i className="bi bi-shield-lock-fill me-2"></i>Restricted Identity Disclosure
                  </h5>
                  <button
                    type="button"
                    className="btn-close btn-close-white"
                    onClick={() => setSelectedComplaintId(null)}
                  ></button>
                </div>
                <div className="modal-body text-start">
                  <div className="alert alert-warning small">
                    <strong>Audit Warning:</strong> Disclosing submitter identity is strictly monitored. An immutable <code>AuditEvent</code> with your administrator ID, timestamp, and justification will be recorded before disclosure.
                  </div>
                  <p className="small text-muted mb-3">
                    Complaint #{selectedComplaintId}
                  </p>
                  {revealError && <div className="alert alert-danger py-2 small">{revealError}</div>}
                  <div className="mb-3">
                    <label className="form-label fw-semibold small">Operational Justification (Required):</label>
                    <textarea
                      className="form-control"
                      rows={3}
                      required
                      minLength={10}
                      placeholder="State the specific administrative purpose (e.g., Immediate safety follow-up for electrical hazard in lab)..."
                      value={justification}
                      onChange={(e) => setJustification(e.target.value)}
                    />
                  </div>
                </div>
                <div className="modal-footer">
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => setSelectedComplaintId(null)}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="btn btn-danger btn-sm"
                    disabled={revealSubmitting}
                  >
                    {revealSubmitting ? 'Recording Audit...' : 'Confirm & Record Audit'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

