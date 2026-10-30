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
      {/* Header */}
      <div className="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3 mb-4">
        <div>
          <div className="d-flex align-items-center gap-2 mb-1">
            <h3 className="mb-0 fw-bold">Operations & Complaints Queue</h3>
            <span className="cv-badge cv-badge-low">{complaints.length} Records</span>
          </div>
          <p className="text-muted small mb-0">
            Submitter identities remain concealed. Audited reveal actions are strictly restricted to safety emergencies.
          </p>
        </div>
        <Link to="/admin/create-issue" className="btn btn-primary d-inline-flex align-items-center gap-2">
          <i className="bi bi-folder-plus"></i>
          <span>Synthesize Issue</span>
        </Link>
      </div>

      {/* Disclosed Identity Result Banner */}
      {revealResult && (
        <div className="cv-card mb-4 border-warning bg-white">
          <div className="cv-card-body p-3 d-flex justify-content-between align-items-center">
            <div className="d-flex align-items-center gap-2">
              <i className="bi bi-shield-check text-warning fs-5"></i>
              <div>
                <strong className="text-dark">Disclosed Submitter Identity (Audit Event #{revealResult.audit_id}):</strong>
                <div className="small text-secondary mt-1">
                  Name: <strong>{revealResult.full_name}</strong> &bull; Email: <strong>{revealResult.email}</strong> &bull; User ID: #{revealResult.user_id}
                </div>
              </div>
            </div>
            <button
              type="button"
              className="btn btn-outline-secondary btn-sm"
              onClick={() => setRevealResult(null)}
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

      {/* Filter Toolbar */}
      <div className="cv-card mb-4">
        <div className="cv-card-body p-3">
          <div className="row g-2 align-items-center">
            <div className="col-md-3">
              <select
                className="form-select"
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
              <select
                className="form-select"
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
              <select
                className="form-select"
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
              <select
                className="form-select"
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
                className="btn btn-outline-secondary w-100"
                onClick={() => {
                  setFilterCategory('');
                  setFilterBuilding('');
                  setFilterStatus('');
                  setFilterPriority('');
                }}
              >
                Reset Filters
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Queue Table */}
      {loading ? (
        <div className="cv-card p-5 text-center text-muted">
          <div className="spinner-border spinner-border-sm text-secondary me-2" role="status"></div>
          Loading operations queue...
        </div>
      ) : complaints.length > 0 ? (
        <div className="cv-card overflow-hidden">
          <div className="table-responsive">
            <table className="cv-table">
              <thead>
                <tr>
                  <th style={{ width: '70px' }}>ID</th>
                  <th>Type & Title</th>
                  <th>Submitter Privacy</th>
                  <th>Location</th>
                  <th>Category</th>
                  <th>Priority</th>
                  <th>Status / AI</th>
                  <th className="text-end" style={{ minWidth: '140px' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {complaints.map((c) => (
                  <tr key={c.id}>
                    <td>
                      <span className="font-monospace fw-semibold text-secondary">#{c.id}</span>
                    </td>
                    <td style={{ maxWidth: '280px' }}>
                      <div className="d-flex align-items-center gap-1 mb-1">
                        <span className="cv-badge cv-badge-low text-capitalize" style={{ fontSize: '0.7rem' }}>
                          {c.submission_type}
                        </span>
                        <Link
                          to={`/complaints/${c.id}`}
                          className="fw-semibold text-dark text-decoration-none text-truncate"
                          style={{ maxWidth: '220px' }}
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
                      <span className="cv-badge cv-badge-low" title="Concealed for submitter privacy">
                        <i className="bi bi-lock me-1"></i>
                        {c.anonymous_submitter}
                      </span>
                    </td>
                    <td>
                      <div className="fw-medium text-dark">{c.building}</div>
                      {c.room && <div className="text-muted small">{c.room}</div>}
                    </td>
                    <td>
                      <span className="cv-badge cv-badge-low">{c.display_category}</span>
                      {c.suggested_category && c.suggested_category !== c.user_category && (
                        <div className="text-primary small mt-1" style={{ fontSize: '0.75rem' }}>
                          AI: {c.suggested_category}
                        </div>
                      )}
                    </td>
                    <td>
                      <StatusBadge type="priority" value={c.display_priority} />
                    </td>
                    <td>
                      <div><StatusBadge type="status" value={c.status} /></div>
                      <div className="text-muted small mt-1" style={{ fontSize: '0.75rem' }}>
                        {c.analysis_state === 'needs_review' ? (
                          <span className="text-danger fw-semibold">Needs Review</span>
                        ) : (
                          c.analysis_state
                        )}
                      </div>
                    </td>
                    <td className="text-end">
                      <div className="d-inline-flex gap-1">
                        <Link
                          to={`/complaints/${c.id}`}
                          className="btn btn-outline-secondary btn-sm"
                          title="View submission details"
                        >
                          View
                        </Link>
                        <Link
                          to={`/admin/create-issue?seed_id=${c.id}`}
                          className="btn btn-outline-secondary btn-sm"
                          title="Synthesize into Master Issue"
                        >
                          <i className="bi bi-folder-plus"></i>
                        </Link>
                        <button
                          type="button"
                          className="btn btn-outline-secondary btn-sm"
                          title="Re-run AI Analysis"
                          onClick={() => handleRetryAnalysis(c.id)}
                        >
                          <i className="bi bi-arrow-repeat"></i>
                        </button>
                        {user?.is_admin && (
                          <button
                            type="button"
                            className="btn btn-outline-secondary btn-sm text-danger"
                            title="Reveal Submitter Identity (Audited)"
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
        <div className="cv-card text-center p-5">
          <div className="text-muted mb-2">
            <i className="bi bi-check2-circle" style={{ fontSize: '2.5rem' }}></i>
          </div>
          <h5 className="fw-semibold text-dark mb-1">Queue is Clear</h5>
          <p className="text-muted small mb-0">
            No complaints currently match the selected filter criteria.
          </p>
        </div>
      )}

      {/* Audited Identity Reveal Modal */}
      {selectedComplaintId && (
        <div className="modal show d-block" tabIndex={-1} style={{ backgroundColor: 'rgba(15, 23, 42, 0.4)' }}>
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content cv-card shadow-lg">
              <form onSubmit={handleRevealIdentity}>
                <div className="cv-card-header d-flex justify-content-between align-items-center">
                  <div className="d-flex align-items-center gap-2">
                    <i className="bi bi-shield-lock text-danger"></i>
                    <h5 className="modal-title mb-0 fw-bold">Restricted Identity Disclosure</h5>
                  </div>
                  <button
                    type="button"
                    className="btn-close"
                    onClick={() => setSelectedComplaintId(null)}
                  ></button>
                </div>

                <div className="cv-card-body p-4 text-start">
                  <div className="alert alert-warning small mb-3">
                    <strong>Mandatory Audit Trail:</strong> Submitter identities are legally protected under campus policy. An immutable <code>AuditEvent</code> with your administrator ID, timestamp, and justification will be recorded before disclosure.
                  </div>

                  <div className="text-muted small mb-3">
                    Target Submission: <strong>Report #{selectedComplaintId}</strong>
                  </div>

                  {revealError && <div className="alert alert-danger py-2 small mb-3">{revealError}</div>}

                  <div className="mb-3">
                    <label className="form-label">
                      Operational Justification (Required) <span className="text-danger">*</span>
                    </label>
                    <textarea
                      className="form-control"
                      rows={3}
                      required
                      minLength={10}
                      placeholder="Specify the operational purpose (e.g., Immediate safety follow-up for electrical hazard)..."
                      value={justification}
                      onChange={(e) => setJustification(e.target.value)}
                    />
                  </div>
                </div>

                <div className="cv-card-header bg-white d-flex justify-content-end gap-2 border-top">
                  <button
                    type="button"
                    className="btn btn-outline-secondary btn-sm"
                    onClick={() => setSelectedComplaintId(null)}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="btn btn-primary btn-sm"
                    disabled={revealSubmitting}
                  >
                    {revealSubmitting ? 'Recording Audit...' : 'Confirm & Commit Audit'}
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
