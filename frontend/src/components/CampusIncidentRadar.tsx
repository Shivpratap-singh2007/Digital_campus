import React, { useEffect, useState } from 'react';
import { api } from '../api/client';

export interface RadarReport {
  id: number;
  title: string;
  category: string;
  building: string;
  room?: string;
  created_at: string;
  detected_symptom?: string;
}

export interface RadarEvidence {
  evidence_level: string;
  time_basis: string;
  dependency_identifier?: string;
  dependency_name?: string;
  dependency_type?: string;
  symptoms_detected?: string[];
  reasons_for_connection?: string[];
  missing_information?: string[];
  analysis_method?: string;
  is_semantic_inference?: boolean;
  reports?: RadarReport[];
}

export interface RadarSuggestion {
  id: number;
  suggestion_type: 'shared_dependency' | 'location_time_cluster';
  headline: string;
  summary: string;
  building: string;
  location_summary?: string;
  status: 'pending_review' | 'confirmed_for_review' | 'rejected';
  created_at: string;
  report_count: number;
  dependency?: {
    id: number;
    dependency_identifier: string;
    name: string;
    dependency_type: string;
    building: string;
    is_synthetic: boolean;
  } | null;
  evidence: RadarEvidence;
  review_decision?: string;
  review_notes?: string;
  clarification_notes?: string;
  reviewed_at?: string;
  reports?: RadarReport[];
}

export const CampusIncidentRadar: React.FC = () => {
  const [suggestions, setSuggestions] = useState<RadarSuggestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [filter, setFilter] = useState<'all' | 'pending_review' | 'confirmed_for_review' | 'rejected'>('all');
  const [selectedSuggestion, setSelectedSuggestion] = useState<RadarSuggestion | null>(null);
  const [reviewNotes, setReviewNotes] = useState('');
  const [reviewSubmitting, setReviewSubmitting] = useState(false);
  const [alertNotice, setAlertNotice] = useState<{ type: 'success' | 'danger' | 'info'; message: string } | null>(null);

  const loadSuggestions = async () => {
    try {
      const res = await api.get('/api/admin/radar');
      setSuggestions(res.suggestions || []);
    } catch (err: any) {
      console.error('Failed to load incident radar suggestions:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSuggestions();
  }, []);

  const handleScan = async () => {
    setScanning(true);
    setAlertNotice(null);
    try {
      const res = await api.post('/api/admin/radar/refresh', {});
      setAlertNotice({
        type: 'success',
        message: `Radar analysis complete: ${res.created_suggestions_count} new suggestion(s), ${res.preserved_suggestions_count} preserved, ${res.scanned_complaints_count} eligible reports scanned.`,
      });
      await loadSuggestions();
    } catch (err: any) {
      setAlertNotice({
        type: 'danger',
        message: err.message || 'Failed to execute Incident Radar analysis scan.',
      });
    } finally {
      setScanning(false);
    }
  };

  const handleSeedDemo = async () => {
    setSeeding(true);
    setAlertNotice(null);
    try {
      const res = await api.post('/api/admin/radar/seed-demo', {});
      setAlertNotice({
        type: 'info',
        message: `${res.message} Running radar scan now...`,
      });
      // Automatically run scan right after seeding demo
      const scanRes = await api.post('/api/admin/radar/refresh', {});
      setAlertNotice({
        type: 'success',
        message: `Synthetic Demo Scenario A seeded & correlated! Created: ${scanRes.created_suggestions_count}, Preserved: ${scanRes.preserved_suggestions_count}.`,
      });
      await loadSuggestions();
    } catch (err: any) {
      setAlertNotice({
        type: 'danger',
        message: err.message || 'Failed to seed synthetic demo scenario.',
      });
    } finally {
      setSeeding(false);
    }
  };

  const handleOpenDetail = (sugg: RadarSuggestion) => {
    setSelectedSuggestion(sugg);
    setReviewNotes(sugg.clarification_notes || sugg.review_notes || '');
  };

  const handleReview = async (action: 'confirm' | 'reject' | 'clarify') => {
    if (!selectedSuggestion) return;
    setReviewSubmitting(true);
    try {
      const res = await api.post(`/api/admin/radar/${selectedSuggestion.id}/review`, {
        action,
        notes: reviewNotes,
      });
      setAlertNotice({
        type: 'success',
        message: `Radar suggestion #${selectedSuggestion.id} updated: ${res.status}. Note logged to audit trail.`,
      });
      // Update local suggestion list and selected modal item
      await loadSuggestions();
      setSelectedSuggestion(null);
      setReviewNotes('');
    } catch (err: any) {
      setAlertNotice({
        type: 'danger',
        message: err.message || 'Failed to submit review decision.',
      });
    } finally {
      setReviewSubmitting(false);
    }
  };

  const filteredSuggestions = suggestions.filter((s) => {
    if (filter === 'all') return true;
    return s.status === filter;
  });

  return (
    <div className="cv-card mb-4 overflow-hidden border border-slate-200 shadow-sm">
      {/* 1. Header with Advisory Context */}
      <div className="cv-card-header bg-white p-3 p-md-4 border-bottom d-flex flex-column flex-md-row justify-content-between align-items-start align-items-md-center gap-3">
        <div>
          <div className="d-flex align-items-center gap-2">
            <span
              className="d-flex align-items-center justify-content-center rounded-circle bg-warning-subtle text-warning"
              style={{ width: '32px', height: '32px' }}
            >
              <i className="bi bi-radar fs-5"></i>
            </span>
            <h5 className="mb-0 fw-bold text-dark">Campus Incident Radar</h5>
            <span className="badge bg-warning-subtle text-dark border border-warning-subtle px-2 py-1 font-monospace" style={{ fontSize: '0.72rem' }}>
              Advisory Correlation
            </span>
          </div>
          <p className="text-muted small mb-0 mt-1">
            Correlates distinct student reports across campus to identify possible shared operational dependencies (power, water, network). Advisory only &mdash; human review required.
          </p>
        </div>

        {/* Action Controls */}
        <div className="d-flex flex-wrap align-items-center gap-2">
          <button
            type="button"
            className="btn btn-outline-secondary btn-sm d-flex align-items-center gap-1 shadow-none"
            onClick={handleSeedDemo}
            disabled={seeding || scanning}
            title="Seed synthetic demo Scenario A (Block B electrical panel)"
          >
            <i className={`bi bi-database-add ${seeding ? 'spin' : ''}`}></i>
            <span>{seeding ? 'Seeding...' : 'Seed Demo Scenario'}</span>
          </button>

          <button
            type="button"
            className="btn btn-primary btn-sm d-flex align-items-center gap-1 shadow-none"
            onClick={handleScan}
            disabled={scanning || seeding}
          >
            <i className={`bi bi-arrow-clockwise ${scanning ? 'spin' : ''}`}></i>
            <span>{scanning ? 'Analyzing Radar...' : 'Scan Incident Radar'}</span>
          </button>
        </div>
      </div>

      {/* 2. Advisory Callout Banner */}
      <div className="bg-amber-50 border-bottom border-amber-200 px-3 py-2 px-md-4 d-flex align-items-center justify-content-between" style={{ backgroundColor: '#fffbeb', borderColor: '#fde68a' }}>
        <div className="d-flex align-items-center gap-2 small text-amber-900" style={{ color: '#78350f' }}>
          <i className="bi bi-info-circle-fill text-amber-600 flex-shrink-0" style={{ color: '#d97706' }}></i>
          <span>
            <strong>Operational Advisory:</strong> Distinct from duplicate grouping. Asks: <em>&ldquo;Could different reports be symptoms of a shared operational incident?&rdquo;</em> Does not auto-resolve or merge complaints.
          </span>
        </div>

        {/* Filter Tabs */}
        <div className="btn-group btn-group-sm ms-auto" role="group">
          <button
            type="button"
            className={`btn btn-sm ${filter === 'all' ? 'btn-dark' : 'btn-outline-secondary'}`}
            style={{ fontSize: '0.72rem' }}
            onClick={() => setFilter('all')}
          >
            All ({suggestions.length})
          </button>
          <button
            type="button"
            className={`btn btn-sm ${filter === 'pending_review' ? 'btn-dark' : 'btn-outline-secondary'}`}
            style={{ fontSize: '0.72rem' }}
            onClick={() => setFilter('pending_review')}
          >
            Pending ({suggestions.filter((s) => s.status === 'pending_review').length})
          </button>
          <button
            type="button"
            className={`btn btn-sm ${filter === 'confirmed_for_review' ? 'btn-dark' : 'btn-outline-secondary'}`}
            style={{ fontSize: '0.72rem' }}
            onClick={() => setFilter('confirmed_for_review')}
          >
            Confirmed ({suggestions.filter((s) => s.status === 'confirmed_for_review').length})
          </button>
        </div>
      </div>

      {/* Alert Notice */}
      {alertNotice && (
        <div className={`alert alert-${alertNotice.type} alert-dismissible fade show m-3 mb-0 py-2 small`} role="alert">
          {alertNotice.message}
          <button type="button" className="btn-close py-2" onClick={() => setAlertNotice(null)}></button>
        </div>
      )}

      {/* 3. Suggestions Content */}
      <div className="cv-card-body p-0">
        {loading ? (
          <div className="p-5 text-center text-muted">
            <div className="spinner-border spinner-border-sm text-secondary me-2" role="status"></div>
            Loading Incident Radar correlations...
          </div>
        ) : filteredSuggestions.length > 0 ? (
          <div className="table-responsive">
            <table className="cv-table align-middle mb-0">
              <thead className="bg-light">
                <tr>
                  <th style={{ width: '90px' }}>Type</th>
                  <th>Incident Suggestion</th>
                  <th>Location</th>
                  <th>Dependency Map</th>
                  <th className="text-center" style={{ width: '120px' }}>Evidence Base</th>
                  <th style={{ width: '130px' }}>Review Status</th>
                  <th style={{ width: '130px' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredSuggestions.map((s) => {
                  const isType1 = s.suggestion_type === 'shared_dependency';
                  return (
                    <tr key={s.id}>
                      {/* Type Badge */}
                      <td>
                        {isType1 ? (
                          <span
                            className="badge bg-warning-subtle text-warning-emphasis border border-warning-subtle px-2 py-1 text-nowrap"
                            style={{ fontSize: '0.72rem' }}
                          >
                            <i className="bi bi-diagram-3-fill me-1"></i>Type 1: Shared Dep
                          </span>
                        ) : (
                          <span
                            className="badge bg-secondary-subtle text-secondary-emphasis border border-secondary-subtle px-2 py-1 text-nowrap"
                            style={{ fontSize: '0.72rem' }}
                          >
                            <i className="bi bi-geo-alt-fill me-1"></i>Type 2: Cluster
                          </span>
                        )}
                      </td>

                      {/* Headline & Summary */}
                      <td>
                        <div className="fw-semibold text-dark">{s.headline}</div>
                        <div className="text-muted small text-truncate" style={{ maxWidth: '380px' }}>
                          {s.summary}
                        </div>
                      </td>

                      {/* Location */}
                      <td>
                        <div className="fw-medium text-dark">{s.building}</div>
                        <div className="text-muted small" style={{ fontSize: '0.75rem' }}>
                          {s.location_summary || 'Multiple areas'}
                        </div>
                      </td>

                      {/* Dependency */}
                      <td>
                        {s.dependency ? (
                          <div>
                            <span className="font-monospace text-primary fw-semibold" style={{ fontSize: '0.8rem' }}>
                              {s.dependency.dependency_identifier}
                            </span>
                            <div className="text-muted small" style={{ fontSize: '0.72rem' }}>
                              {s.dependency.name}
                              {s.dependency.is_synthetic && (
                                <span className="badge bg-info-subtle text-info border border-info-subtle ms-1" style={{ fontSize: '0.65rem' }}>
                                  Synthetic
                                </span>
                              )}
                            </div>
                          </div>
                        ) : (
                          <span className="text-muted small fst-italic">Cause Unknown (No mapped link)</span>
                        )}
                      </td>

                      {/* Evidence Base (Report Count + Time Window) */}
                      <td className="text-center">
                        <span className="badge bg-primary-subtle text-primary border border-primary-subtle px-2 py-1 font-monospace">
                          <i className="bi bi-file-earmark-text me-1"></i>
                          {s.report_count} reports
                        </span>
                        <div className="text-muted small mt-1" style={{ fontSize: '0.7rem' }}>
                          Window: &le; 4 hrs
                        </div>
                      </td>

                      {/* Review Status */}
                      <td>
                        {s.status === 'confirmed_for_review' ? (
                          <span className="badge bg-success-subtle text-success border border-success-subtle px-2 py-1" style={{ fontSize: '0.72rem' }}>
                            <i className="bi bi-check-circle me-1"></i>Confirmed for Review
                          </span>
                        ) : s.status === 'rejected' ? (
                          <span className="badge bg-secondary-subtle text-secondary border border-secondary-subtle px-2 py-1" style={{ fontSize: '0.72rem' }}>
                            <i className="bi bi-x-circle me-1"></i>Rejected
                          </span>
                        ) : (
                          <span className="badge bg-warning-subtle text-warning-emphasis border border-warning-subtle px-2 py-1" style={{ fontSize: '0.72rem' }}>
                            <i className="bi bi-clock-history me-1"></i>Pending Review
                          </span>
                        )}
                      </td>

                      {/* Action Button */}
                      <td>
                        <button
                          type="button"
                          className="btn btn-outline-primary btn-sm py-1 px-2 d-flex align-items-center gap-1 shadow-none"
                          style={{ fontSize: '0.75rem' }}
                          onClick={() => handleOpenDetail(s)}
                        >
                          <i className="bi bi-search"></i>
                          <span>Inspect Evidence</span>
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-5 text-center text-muted">
            <i className="bi bi-shield-check text-success fs-1 d-block mb-2"></i>
            <h6 className="fw-semibold text-dark">No Active Incident Radar Correlations</h6>
            <p className="small mb-3 text-muted" style={{ maxWidth: '480px', margin: '0 auto' }}>
              No shared-dependency incidents or spatial-temporal disruption clusters detected in the last 48 hours.
            </p>
            <div className="d-flex justify-content-center gap-2">
              <button className="btn btn-outline-secondary btn-sm" onClick={handleSeedDemo}>
                Seed Synthetic Demo (Scenario A)
              </button>
              <button className="btn btn-primary btn-sm" onClick={handleScan}>
                Run Radar Scan
              </button>
            </div>
          </div>
        )}
      </div>

      {/* 4. DETAIL & EVIDENCE INSPECTION MODAL */}
      {selectedSuggestion && (
        <div
          className="modal show d-block"
          tabIndex={-1}
          style={{ backgroundColor: 'rgba(15, 23, 42, 0.6)', backdropFilter: 'blur(3px)', zIndex: 1060 }}
        >
          <div className="modal-dialog modal-dialog-centered modal-lg modal-dialog-scrollable">
            <div className="modal-content cv-card shadow-lg border-0 overflow-hidden">
              {/* Modal Header */}
              <div className="cv-card-header bg-white py-3 px-4 border-bottom d-flex justify-content-between align-items-center">
                <div className="d-flex align-items-center gap-2">
                  <div
                    className="d-flex align-items-center justify-content-center rounded-circle bg-warning-subtle text-warning"
                    style={{ width: '36px', height: '36px' }}
                  >
                    <i className="bi bi-radar fs-5"></i>
                  </div>
                  <div>
                    <h5 className="modal-title mb-0 fw-bold text-dark fs-6">
                      Radar Suggestion #{selectedSuggestion.id}: {selectedSuggestion.headline}
                    </h5>
                    <span className="text-muted small" style={{ fontSize: '0.75rem' }}>
                      Building: {selectedSuggestion.building} &bull; Type:{' '}
                      {selectedSuggestion.suggestion_type === 'shared_dependency' ? 'Type 1 (Shared Dependency)' : 'Type 2 (Cluster)'}
                    </span>
                  </div>
                </div>
                <button
                  type="button"
                  className="btn-close shadow-none"
                  onClick={() => setSelectedSuggestion(null)}
                  disabled={reviewSubmitting}
                ></button>
              </div>

              {/* Modal Body */}
              <div className="modal-body p-4 bg-light bg-opacity-50">
                {/* NON-NEGOTIABLE ADVISORY WARNING CALLOUT */}
                <div className="alert alert-warning py-2 px-3 small d-flex align-items-start gap-2 mb-3 border-warning">
                  <i className="bi bi-exclamation-triangle-fill text-warning flex-shrink-0 mt-1"></i>
                  <div>
                    <strong>Advisory Incident Correlation:</strong> Suggested connection based on evidence, not a confirmed cause.
                    This analysis coordinates maintenance response and does NOT alter complaint statuses or merge tickets.
                  </div>
                </div>

                {/* Evidence Snapshot Card */}
                <div className="card border-0 shadow-sm p-3 mb-3 bg-white">
                  <h6 className="fw-bold text-dark mb-2 small text-uppercase tracking-wider">
                    <i className="bi bi-shield-check text-primary me-1"></i> Evidence Snapshot &amp; Pipeline Telemetry
                  </h6>
                  <div className="row g-2 small">
                    <div className="col-sm-6">
                      <span className="text-muted">Evidence Level: </span>
                      <span className="fw-semibold text-dark">{selectedSuggestion.evidence?.evidence_level}</span>
                    </div>
                    <div className="col-sm-6">
                      <span className="text-muted">Time Basis: </span>
                      <span className="fw-semibold text-dark">{selectedSuggestion.evidence?.time_basis} (Complaint submission timestamp)</span>
                    </div>
                    <div className="col-sm-6">
                      <span className="text-muted">Analysis Method: </span>
                      <span className="badge bg-secondary-subtle text-dark font-monospace" style={{ fontSize: '0.72rem' }}>
                        {selectedSuggestion.evidence?.analysis_method || 'rule_based_symptom_v1'}
                      </span>
                    </div>
                    <div className="col-sm-6">
                      <span className="text-muted">Mapped Dependency: </span>
                      <span className="fw-semibold text-dark font-monospace">
                        {selectedSuggestion.dependency?.dependency_identifier || 'None (Cause unknown)'}
                      </span>
                      {selectedSuggestion.dependency?.is_synthetic && (
                        <span className="badge bg-info-subtle text-info ms-1" style={{ fontSize: '0.65rem' }}>Synthetic Demo</span>
                      )}
                    </div>
                  </div>

                  {/* Detected Symptoms */}
                  {selectedSuggestion.evidence?.symptoms_detected && selectedSuggestion.evidence.symptoms_detected.length > 0 && (
                    <div className="mt-3 pt-2 border-top">
                      <span className="text-muted small d-block mb-1">Detected Symptoms:</span>
                      <div className="d-flex flex-wrap gap-1">
                        {selectedSuggestion.evidence.symptoms_detected.map((sym, idx) => (
                          <span key={idx} className="badge bg-primary-subtle text-primary border border-primary-subtle" style={{ fontSize: '0.7rem' }}>
                            {sym}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Reasons For Connection */}
                  {selectedSuggestion.evidence?.reasons_for_connection && selectedSuggestion.evidence.reasons_for_connection.length > 0 && (
                    <div className="mt-3 pt-2 border-top">
                      <span className="text-muted small fw-semibold d-block mb-1">Why Suggested:</span>
                      <ul className="mb-0 ps-3 small text-muted">
                        {selectedSuggestion.evidence.reasons_for_connection.map((reason, idx) => (
                          <li key={idx}>{reason}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Missing Information */}
                  {selectedSuggestion.evidence?.missing_information && selectedSuggestion.evidence.missing_information.length > 0 && (
                    <div className="mt-2 pt-2 border-top">
                      <span className="text-muted small fw-semibold d-block mb-1 text-danger">Missing Operational Evidence:</span>
                      <ul className="mb-0 ps-3 small text-muted">
                        {selectedSuggestion.evidence.missing_information.map((item, idx) => (
                          <li key={idx}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>

                {/* Linked Reports Table (Strictly masked / anonymous) */}
                <div className="card border-0 shadow-sm overflow-hidden mb-3 bg-white">
                  <div className="card-header bg-white py-2 px-3 border-bottom d-flex justify-content-between align-items-center">
                    <span className="fw-bold small text-dark">
                      <i className="bi bi-link-45deg text-primary me-1"></i>
                      Correlated Student Reports ({selectedSuggestion.evidence?.reports?.length || selectedSuggestion.report_count})
                    </span>
                    <span className="badge bg-secondary-subtle text-secondary" style={{ fontSize: '0.7rem' }}>
                      🔒 Identities Protected
                    </span>
                  </div>
                  <div className="table-responsive">
                    <table className="table table-sm align-middle mb-0 small">
                      <thead className="table-light">
                        <tr>
                          <th style={{ width: '70px' }}>ID</th>
                          <th>Complaint Title</th>
                          <th>Category</th>
                          <th>Location / Room</th>
                          <th>Symptom</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(selectedSuggestion.evidence?.reports || selectedSuggestion.reports || []).map((rep) => (
                          <tr key={rep.id}>
                            <td className="font-monospace text-muted">#{rep.id}</td>
                            <td className="fw-medium text-dark">{rep.title}</td>
                            <td>
                              <span className="badge bg-light text-dark border" style={{ fontSize: '0.7rem' }}>
                                {rep.category}
                              </span>
                            </td>
                            <td className="text-muted">
                              {rep.building} {rep.room ? `(${rep.room})` : ''}
                            </td>
                            <td>
                              <span className="badge bg-info-subtle text-info border border-info-subtle font-monospace" style={{ fontSize: '0.68rem' }}>
                                {rep.detected_symptom || 'unclassified'}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Review Notes Section */}
                <div className="mb-2">
                  <label className="form-label small fw-semibold text-dark mb-1">
                    Internal Operational / Verification Note:
                  </label>
                  <textarea
                    className="form-control form-control-sm"
                    rows={2}
                    placeholder="e.g., Electrician dispatched to inspect breaker P1; will verify physical contactors."
                    value={reviewNotes}
                    onChange={(e) => setReviewNotes(e.target.value)}
                    disabled={reviewSubmitting}
                  ></textarea>
                  <div className="text-muted small mt-1" style={{ fontSize: '0.72rem' }}>
                    Note will be recorded to the tamper-evident audit log with your reviewer account.
                  </div>
                </div>
              </div>

              {/* Modal Footer with Actions */}
              <div className="modal-footer py-2 px-4 bg-white border-top d-flex flex-column flex-sm-row justify-content-between align-items-center gap-2">
                <div className="small text-muted">
                  Decision:{' '}
                  <span className="fw-semibold text-dark">
                    {selectedSuggestion.status === 'confirmed_for_review'
                      ? 'Confirmed for Coordinated Investigation'
                      : selectedSuggestion.status === 'rejected'
                      ? 'Rejected Connection'
                      : 'Pending Review'}
                  </span>
                </div>

                <div className="d-flex align-items-center gap-2">
                  <button
                    type="button"
                    className="btn btn-outline-danger btn-sm"
                    onClick={() => handleReview('reject')}
                    disabled={reviewSubmitting}
                  >
                    <i className="bi bi-x-circle me-1"></i>Reject Connection
                  </button>

                  <button
                    type="button"
                    className="btn btn-outline-secondary btn-sm"
                    onClick={() => handleReview('clarify')}
                    disabled={reviewSubmitting}
                  >
                    <i className="bi bi-chat-left-text me-1"></i>Save Clarification Note
                  </button>

                  <button
                    type="button"
                    className="btn btn-success btn-sm"
                    onClick={() => handleReview('confirm')}
                    disabled={reviewSubmitting}
                  >
                    <i className="bi bi-check-circle me-1"></i>Confirm for Coordinated Review
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

