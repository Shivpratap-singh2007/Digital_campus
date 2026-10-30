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
      <div className="mb-4 d-flex justify-content-between align-items-center">
        <div>
          <h3 className="mb-1 text-dark">
            <i className="bi bi-journal-text me-2"></i>Security & Privacy Audit Log
          </h3>
          <p className="text-muted small mb-0">
            Immutable record of privileged operations and submitter identity disclosures.
          </p>
        </div>
        <span className="badge bg-danger-subtle text-danger border border-danger p-2">
          <i className="bi bi-shield-lock-fill me-1"></i>Admin Access Only
        </span>
      </div>

      <div className="alert alert-info small mb-4">
        <i className="bi bi-info-circle me-1"></i>
        <strong>Privacy Compliance Rule:</strong> Disclosed personal information (such as full names and email addresses) is intentionally <em>never</em> redundantly copied into the audit log. The audit log preserves the who, when, why, and what target, without proliferating PII.
      </div>

      {loading ? (
        <div className="card card-shadow p-5 text-center text-muted">
          Loading audit trail...
        </div>
      ) : events.length > 0 ? (
        <div className="card card-shadow">
          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0">
              <thead className="table-light">
                <tr>
                  <th style={{ width: '70px' }}>ID</th>
                  <th>Timestamp (UTC)</th>
                  <th>Administrator (Actor)</th>
                  <th>Action</th>
                  <th>Target</th>
                  <th>Operational Purpose / Justification</th>
                  <th>Client IP</th>
                </tr>
              </thead>
              <tbody>
                {events.map((ev) => (
                  <tr key={ev.id}>
                    <td><strong>#{ev.id}</strong></td>
                    <td className="small text-muted">{new Date(ev.created_at).toLocaleString()}</td>
                    <td>
                      <div><strong>{ev.actor_name}</strong></div>
                      <small className="text-muted">{ev.actor_email}</small>
                    </td>
                    <td>
                      <span className="badge bg-danger text-uppercase font-monospace">{ev.action}</span>
                    </td>
                    <td>
                      <span className="badge bg-light text-dark border">
                        {ev.target_type}: #{ev.target_id}
                      </span>
                    </td>
                    <td className="small" style={{ maxWidth: '320px' }}>
                      <em>"{ev.justification}"</em>
                    </td>
                    <td className="small text-muted font-monospace">{ev.ip_address || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="card card-shadow text-center p-5">
          <i className="bi bi-shield-check text-muted" style={{ fontSize: '3rem' }}></i>
          <h5 className="mt-3">No Privileged Audit Events</h5>
          <p className="text-muted small">No identity reveals or privileged privacy disclosures have been recorded.</p>
        </div>
      )}
    </div>
  );
};

