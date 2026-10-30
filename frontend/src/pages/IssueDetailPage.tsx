import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../api/client';
import { StatusBadge } from '../components/StatusBadge';

export const IssueDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();

  const [issue, setIssue] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Status update form
  const [newStatus, setNewStatus] = useState('under_review');
  const [statusNote, setStatusNote] = useState('');
  const [statusUpdating, setStatusUpdating] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');
  const [statusError, setStatusError] = useState('');

  // Manual link form
  const [manualComplaintId, setManualComplaintId] = useState('');
  const [manualRelType, setManualRelType] = useState('same_incident');

  const loadIssue = async () => {
    try {
      const data = await api.get(`/api/issues/${id}`);
      setIssue(data);
      setNewStatus(data.status);
    } catch (err: any) {
      setError(err.message || 'Failed to load issue.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadIssue();
  }, [id]);

  const handleStatusUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatusUpdating(true);
    setStatusMessage('');
    setStatusError('');

    try {
      const res = await api.post(`/api/issues/${id}/status`, {
        new_status: newStatus,
        note: statusNote,
      });
      setStatusMessage(res.message);
      setStatusNote('');
      await loadIssue();
    } catch (err: any) {
      setStatusError(err.message || 'Failed to update status.');
    } finally {
      setStatusUpdating(false);
    }
  };

  const handleUnlink = async (complaintId: number) => {
    if (!window.confirm('Unlink this complaint? Original report will be preserved intact.')) {
      return;
    }
    try {
      await api.post(`/api/issues/${id}/unlink/${complaintId}`);
      await loadIssue();
    } catch (err: any) {
      alert(err.message || 'Unlink failed.');
    }
  };

  const handleFastLink = async (complaintId: number, relType: string) => {
    try {
      await api.post(`/api/issues/${id}/link`, {
        complaint_id: complaintId,
        relationship_type: relType,
      });
      await loadIssue();
    } catch (err: any) {
      alert(err.message || 'Link failed.');
    }
  };

  const handleManualLink = async (e: React.FormEvent) => {
    e.preventDefault();
    const cId = parseInt(manualComplaintId, 10);
    if (!cId) return;

    try {
      await api.post(`/api/issues/${id}/link`, {
        complaint_id: cId,
        relationship_type: manualRelType,
      });
      setManualComplaintId('');
      await loadIssue();
    } catch (err: any) {
      alert(err.message || 'Link failed.');
    }
  };

  if (loading) {
    return (
      <div className="cv-card p-5 text-center text-muted">
        <div className="spinner-border spinner-border-sm text-secondary me-2" role="status"></div>
        Loading issue details...
      </div>
    );
  }

  if (error || !issue) {
    return (
      <div className="cv-card p-4 text-center my-4">
        <div className="text-danger mb-2">
          <i className="bi bi-exclamation-triangle" style={{ fontSize: '2rem' }}></i>
        </div>
        <h5 className="fw-semibold text-dark">{error || 'Issue Not Found'}</h5>
        <div className="mt-3">
          <Link to="/admin/queue" className="btn btn-outline-secondary btn-sm">
            Back to Operations Queue
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Back Link */}
      <div className="mb-3">
        <Link to="/admin/queue" className="text-decoration-none text-muted small d-inline-flex align-items-center gap-1">
          <i className="bi bi-arrow-left"></i> Back to Complaints Queue
        </Link>
      </div>

      <div className="row g-4">
        {/* Left Column: Details & Linked Submissions */}
        <div className="col-lg-8">
          <div className="cv-card mb-4">
            <div className="cv-card-header d-flex justify-content-between align-items-center">
              <div className="d-flex align-items-center gap-2">
                <span className="cv-badge cv-badge-low fw-bold">Master Issue #{issue.id}</span>
                <span className="text-muted small">
                  Created {new Date(issue.created_at).toLocaleString()}
                </span>
              </div>
              <div>
                <StatusBadge type="status" value={issue.status} />
              </div>
            </div>

            <div className="cv-card-body p-4">
              <h3 className="fw-bold text-dark mb-3">{issue.title}</h3>

              <div className="d-flex flex-wrap align-items-center gap-2 mb-4">
                <span className="cv-badge cv-badge-low">
                  <i className="bi bi-geo-alt me-1"></i>
                  {issue.building} {issue.room && `· ${issue.room}`}
                </span>
                <span className="cv-badge cv-badge-low">
                  <i className="bi bi-tag me-1"></i>
                  {issue.category}
                </span>
                <StatusBadge type="priority" value={issue.priority} />
              </div>

              <div className="p-3 rounded mb-4" style={{ backgroundColor: 'var(--bg-subtle)' }}>
                <div className="text-uppercase fw-bold text-muted mb-2" style={{ fontSize: '0.72rem', letterSpacing: '0.05em' }}>
                  Synthesized Public Summary
                </div>
                <p className="mb-0 text-dark" style={{ whiteSpace: 'pre-wrap', fontSize: '0.92rem', lineHeight: '1.6' }}>
                  {issue.description}
                </p>
              </div>

              {/* Linked Submissions */}
              <div className="mb-4">
                <div className="d-flex justify-content-between align-items-center mb-3">
                  <h5 className="mb-0 fw-semibold text-dark">
                    Linked Submissions ({issue.linked_complaints?.length || 0})
                  </h5>
                  <span className="text-muted small">Original reports preserved intact.</span>
                </div>

                {issue.linked_complaints && issue.linked_complaints.length > 0 ? (
                  <div className="d-flex flex-column gap-2">
                    {issue.linked_complaints.map((c: any) => (
                      <div
                        key={c.complaint_id}
                        className="p-3 rounded border d-flex justify-content-between align-items-center bg-white"
                      >
                        <div>
                          <div className="d-flex align-items-center gap-2">
                            <span className="font-monospace fw-semibold text-secondary">#{c.complaint_id}</span>
                            <Link to={`/complaints/${c.complaint_id}`} className="fw-semibold text-dark text-decoration-none">
                              {c.title}
                            </Link>
                            <span className="cv-badge cv-badge-low text-capitalize" style={{ fontSize: '0.7rem' }}>
                              {c.submission_type}
                            </span>
                          </div>
                          <div className="small text-muted mt-1">
                            <span><i className="bi bi-geo-alt"></i> {c.building} {c.room && `(${c.room})`}</span> &bull;{' '}
                            <span><i className="bi bi-tag"></i> {c.category}</span> &bull;{' '}
                            <span>Relationship: <code>{c.relationship_type}</code></span>
                          </div>
                        </div>
                        <div>
                          <button
                            type="button"
                            className="btn btn-sm btn-outline-secondary text-danger"
                            title="Unlink complaint (reversible)"
                            onClick={() => handleUnlink(c.complaint_id)}
                          >
                            Unlink
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="alert alert-light border small text-muted mb-0">
                    No complaints currently linked to this issue.
                  </div>
                )}
              </div>

              {/* Suggested Related Reports (Semantic AI & Proximity) */}
              <div className="mb-4">
                <div className="mb-2">
                  <h5 className="mb-1 fw-semibold text-dark">
                    Suggested Related Reports
                  </h5>
                  <p className="text-muted small mb-0">
                    Candidate complaints ranked via multilingual semantic embeddings and facility proximity.
                  </p>
                </div>

                {issue.suggested_matches && issue.suggested_matches.length > 0 ? (
                  <div className="d-flex flex-column gap-2 mt-3">
                    {issue.suggested_matches.map((m: any) => (
                      <div key={m.complaint_id} className="p-3 rounded border bg-white">
                        <div className="d-flex flex-column flex-sm-row justify-content-between align-items-sm-start gap-2">
                          <div>
                            <div className="d-flex align-items-center gap-2">
                              <span className="font-monospace fw-semibold text-secondary">#{m.complaint_id}</span>
                              <Link to={`/complaints/${m.complaint_id}`} target="_blank" className="fw-semibold text-dark text-decoration-none">
                                {m.title}
                              </Link>
                              {m.is_possible_recurrence && (
                                <span className="cv-badge cv-badge-urgent">
                                  Possible Recurrence
                                </span>
                              )}
                            </div>
                            <div className="small text-muted mt-1">
                              <span><i className="bi bi-geo-alt"></i> {m.building} {m.room && `(${m.room})`}</span> &bull;{' '}
                              <span className="text-primary fw-medium">{m.match_details}</span>
                            </div>
                          </div>
                          <div className="d-flex gap-2">
                            <button
                              type="button"
                              className="btn btn-sm btn-outline-secondary"
                              onClick={() => handleFastLink(m.complaint_id, 'same_incident')}
                            >
                              Same Incident
                            </button>
                            <button
                              type="button"
                              className="btn btn-sm btn-outline-secondary"
                              onClick={() => handleFastLink(m.complaint_id, 'related_only')}
                            >
                              Related Only
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="alert alert-light border small text-muted mb-0 mt-3">
                    No unlinked candidate complaints found with high similarity.
                  </div>
                )}
              </div>

              {/* Status Progression History */}
              <div className="cv-card border">
                <div className="cv-card-header">
                  <h6 className="mb-0 fw-semibold text-dark">Issue Status History</h6>
                </div>
                <div className="cv-card-body p-3">
                  {issue.status_events && issue.status_events.length > 0 ? (
                    <div className="d-flex flex-column gap-2">
                      {issue.status_events.map((ev: any) => (
                        <div key={ev.id} className="d-flex justify-content-between align-items-center py-2 border-bottom last-border-none">
                          <div className="d-flex align-items-center gap-2">
                            <span className="cv-badge cv-badge-low text-capitalize">{ev.new_status}</span>
                            <span className="text-dark small">{ev.note}</span>
                          </div>
                          <span className="text-muted small">
                            {new Date(ev.created_at).toLocaleString()}
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-muted small mb-0">No status updates logged.</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Status Operations, Resolution Rounds, Manual Link */}
        <div className="col-lg-4">
          {/* Status Update Form */}
          <div className="cv-card mb-4">
            <div className="cv-card-header">
              <h5 className="mb-0 fw-bold text-dark">Update Operational Status</h5>
            </div>
            <div className="cv-card-body p-3">
              {statusMessage && <div className="alert alert-success py-2 small mb-3">{statusMessage}</div>}
              {statusError && <div className="alert alert-danger py-2 small mb-3">{statusError}</div>}

              <form onSubmit={handleStatusUpdate}>
                <div className="mb-3">
                  <label className="form-label">New Status</label>
                  <select
                    className="form-select"
                    value={newStatus}
                    onChange={(e) => setNewStatus(e.target.value)}
                  >
                    <option value="submitted">Submitted</option>
                    <option value="under_review">Under Review</option>
                    <option value="in_progress">In Progress</option>
                    <option value="resolved">Resolved</option>
                  </select>
                </div>

                <div className="mb-3">
                  <label className="form-label">
                    Operational Note <span className="text-danger">*</span>
                  </label>
                  <textarea
                    className="form-control"
                    rows={3}
                    placeholder="Describe maintenance actions taken or resolution notes..."
                    value={statusNote}
                    onChange={(e) => setStatusNote(e.target.value)}
                    required
                    minLength={5}
                  />
                  <div className="form-text">
                    Marking Resolved opens a new feedback round for linked submitters.
                  </div>
                </div>

                <button
                  type="submit"
                  className="btn btn-primary w-100"
                  disabled={statusUpdating}
                >
                  {statusUpdating ? 'Updating Status...' : 'Commit Status Update'}
                </button>
              </form>
            </div>
          </div>

          {/* Resolution Feedback Rounds */}
          <div className="cv-card mb-4">
            <div className="cv-card-header">
              <h5 className="mb-0 fw-bold text-dark">Resolution Feedback Rounds</h5>
            </div>
            <div className="cv-card-body p-3">
              {issue.resolution_rounds && issue.resolution_rounds.length > 0 ? (
                issue.resolution_rounds.map((round: any) => (
                  <div key={round.round_number} className="p-3 rounded border mb-3 bg-white">
                    <div className="d-flex justify-content-between align-items-center mb-2">
                      <span className="fw-bold text-dark">Round #{round.round_number}</span>
                      <StatusBadge type="feedback_round" value={round.status} />
                    </div>

                    <p className="small text-muted mb-2">
                      <strong>Resolution Note:</strong> <em>"{round.resolution_note}"</em>
                    </p>

                    <div className="p-2 rounded small" style={{ backgroundColor: 'var(--bg-subtle)' }}>
                      <div className="fw-semibold text-secondary mb-1">Submitter Confirmations:</div>
                      <div className="d-flex justify-content-between">
                        <span className="text-success">
                          Fixed: <strong>{round.aggregate_counts.fixed}</strong>
                        </span>
                        <span className="text-warning text-dark">
                          Partial: <strong>{round.aggregate_counts.partially_fixed}</strong>
                        </span>
                        <span className="text-danger">
                          Not Fixed: <strong>{round.aggregate_counts.not_fixed}</strong>
                        </span>
                      </div>
                    </div>

                    <div className="small text-muted mt-2" style={{ fontSize: '0.75rem' }}>
                      <em>All submitters must confirm fixed before labeled Submitter-Confirmed.</em>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-muted small mb-0">
                  No resolution rounds yet. When this issue is marked Resolved, original submitters will be invited to confirm.
                </p>
              )}
            </div>
          </div>

          {/* Manual Link by ID */}
          <div className="cv-card mb-4">
            <div className="cv-card-header">
              <h6 className="mb-0 fw-bold text-dark">Link Complaint by ID</h6>
            </div>
            <div className="cv-card-body p-3">
              <form onSubmit={handleManualLink}>
                <div className="mb-2">
                  <label className="form-label">Complaint Reference ID</label>
                  <input
                    type="number"
                    className="form-control"
                    placeholder="e.g. 5"
                    value={manualComplaintId}
                    onChange={(e) => setManualComplaintId(e.target.value)}
                    required
                  />
                </div>
                <div className="mb-3">
                  <label className="form-label">Relationship Type</label>
                  <select
                    className="form-select"
                    value={manualRelType}
                    onChange={(e) => setManualRelType(e.target.value)}
                  >
                    <option value="same_incident">Same Incident</option>
                    <option value="related_only">Related Only</option>
                  </select>
                </div>
                <button type="submit" className="btn btn-outline-secondary w-100">
                  Link Submission
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
