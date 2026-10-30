import React, { useEffect, useState } from 'react';
import { api } from '../api/client';

export const AuditLogPage: React.FC = () => {
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadAuditEvents() {
      try {
        const data = await api.get('/api/admin/audit-log');
        setEvents(data.audit_events || []);
      } catch (err) {
        console.error('Failed to load audit events:', err);
      } finally {
        setLoading(false);
      }
    }
    loadAuditEvents();
  }, []);

  return (
    <div>
      {/* Header */}
      <div className="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3 mb-4">
        <div>
          <div className="d-flex align-items-center gap-2 mb-1">
            <h3 className="mb-0 fw-bold">Security & Privacy Audit Log</h3>
            <span className="cv-badge cv-badge-urgent">
              <i className="bi bi-shield-lock me-1"></i>Admin Only
            </span>
          </div>
          <p className="text-muted small mb-0">
            Immutable audit record of privileged actions and authorized submitter identity disclosures.
          </p>
        </div>
      </div>

      {/* Compliance Note */}
      <div className="cv-card mb-4 bg-white">
        <div className="cv-card-body p-3 d-flex align-items-start gap-2">
          <i className="bi bi-info-circle text-primary mt-1"></i>
          <div className="small text-secondary">
            <strong>Privacy Compliance Architecture:</strong> To prevent data proliferation, submitter PII (full name and email) is <em>never</em> redundantly duplicated into the audit log. The audit log permanently records the actor, exact timestamp, target ID, and mandatory operational justification.
          </div>
        </div>
      </div>

      {/* Audit Events Table */}
      {loading ? (
        <div className="cv-card p-5 text-center text-muted">
          <div className="spinner-border spinner-border-sm text-secondary me-2" role="status"></div>
          Loading audit trail...
        </div>
      ) : events.length > 0 ? (
        <div className="cv-card overflow-hidden">
          <div className="table-responsive">
            <table className="cv-table">
              <thead>
                <tr>
                  <th style={{ width: '70px' }}>Log ID</th>
                  <th>Timestamp (UTC)</th>
                  <th>Administrator (Actor)</th>
                  <th>Action</th>
                  <th>Target Record</th>
                  <th>Operational Justification</th>
                  <th>Client IP</th>
                </tr>
              </thead>
              <tbody>
                {events.map((ev) => (
                  <tr key={ev.id}>
                    <td>
                      <span className="font-monospace fw-semibold text-secondary">#{ev.id}</span>
                    </td>
                    <td className="small text-muted font-monospace">
                      {new Date(ev.created_at).toLocaleString()}
                    </td>
                    <td>
                      <div className="fw-medium text-dark">{ev.actor_name}</div>
                      <div className="text-muted small">{ev.actor_email}</div>
                    </td>
                    <td>
                      <span className="cv-badge cv-badge-urgent font-monospace text-uppercase" style={{ fontSize: '0.72rem' }}>
                        {ev.action}
                      </span>
                    </td>
                    <td>
                      <span className="cv-badge cv-badge-low">
                        {ev.target_type}: #{ev.target_id}
                      </span>
                    </td>
                    <td className="small" style={{ maxWidth: '300px' }}>
                      <span className="text-dark fst-italic">"{ev.justification}"</span>
                    </td>
                    <td className="small text-muted font-monospace">{ev.ip_address || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="cv-card text-center p-5">
          <div className="text-muted mb-2">
            <i className="bi bi-shield-check" style={{ fontSize: '2.5rem' }}></i>
          </div>
          <h5 className="fw-semibold text-dark mb-1">No Privileged Audit Events</h5>
          <p className="text-muted small mb-0">
            No identity reveals or privileged privacy disclosures have been recorded.
          </p>
        </div>
      )}
    </div>
  );
};
