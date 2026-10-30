import React, { useEffect, useState } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts';
import { api } from '../api/client';

const CHART_PALETTE = ['#2563eb', '#0284c7', '#0d9488', '#16a34a', '#ea580c', '#dc2626', '#64748b'];

export const DashboardPage: React.FC = () => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadMetrics() {
      try {
        const res = await api.get('/api/admin/dashboard');
        setData(res);
      } catch (err) {
        console.error('Failed to load dashboard metrics:', err);
      } finally {
        setLoading(false);
      }
    }
    loadMetrics();
  }, []);

  if (loading) {
    return (
      <div className="cv-card p-5 text-center text-muted">
        <div className="spinner-border spinner-border-sm text-secondary me-2" role="status"></div>
        Loading operations metrics...
      </div>
    );
  }

  if (!data) {
    return (
      <div className="cv-card p-4 text-center my-4">
        <div className="text-danger mb-2">
          <i className="bi bi-exclamation-triangle" style={{ fontSize: '2rem' }}></i>
        </div>
        <h5 className="fw-semibold text-dark">Could not load operational metrics</h5>
      </div>
    );
  }

  const m = data.metrics || {};
  const catData = data.category_breakdown || [];
  const statusData = data.issue_status_breakdown || [];
  const locData = data.location_breakdown || [];

  return (
    <div>
      {/* Header */}
      <div className="mb-4">
        <h3 className="mb-1 fw-bold text-dark">Campus Operations & Metrics Dashboard</h3>
        <p className="text-muted small mb-0">
          Calculated in real time from live SQLite database records. No synthetic multipliers or simulated counts.
        </p>
      </div>

      {/* 6 Primary Metric Stat Widgets */}
      <div className="row g-3 mb-4">
        <div className="col-6 col-md-4 col-xl-2">
          <div className="stat-widget h-100">
            <span className="stat-label">Total Submissions</span>
            <div className="stat-number">{m.total_submissions}</div>
            <span className="stat-meta">Raw user reports</span>
          </div>
        </div>

        <div className="col-6 col-md-4 col-xl-2">
          <div className="stat-widget h-100">
            <span className="stat-label">Distinct Issues</span>
            <div className="stat-number text-primary">{m.distinct_issues}</div>
            <span className="stat-meta">Synthesized tasks</span>
          </div>
        </div>

        <div className="col-6 col-md-4 col-xl-2">
          <div className="stat-widget h-100">
            <span className="stat-label">Active Issues</span>
            <div className="stat-number text-warning text-dark">{m.unresolved_issues}</div>
            <span className="stat-meta">Under review / progress</span>
          </div>
        </div>

        <div className="col-6 col-md-4 col-xl-2">
          <div className="stat-widget h-100">
            <span className="stat-label">Urgent Reviews</span>
            <div className="stat-number text-danger">{m.urgent_reviews}</div>
            <span className="stat-meta">High-hazard flags</span>
          </div>
        </div>

        <div className="col-6 col-md-4 col-xl-2">
          <div className="stat-widget h-100">
            <span className="stat-label">Resolved Issues</span>
            <div className="stat-number text-success">{m.resolved_issues}</div>
            <span className="stat-meta">Completed repairs</span>
          </div>
        </div>

        <div className="col-6 col-md-4 col-xl-2">
          <div className="stat-widget h-100">
            <span className="stat-label">Disputed Feedback</span>
            <div className="stat-number text-danger">{m.disputed_resolutions}</div>
            <span className="stat-meta">Failed confirmation</span>
          </div>
        </div>
      </div>

      {/* Recharts Visualizations */}
      <div className="row g-4 mb-4">
        <div className="col-lg-6">
          <div className="cv-card h-100">
            <div className="cv-card-header">
              <h6 className="mb-0 fw-bold text-dark">Submissions by Category</h6>
            </div>
            <div className="cv-card-body" style={{ height: '300px' }}>
              {catData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={catData} margin={{ top: 20, right: 20, left: -10, bottom: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                    <XAxis
                      dataKey="category"
                      angle={-15}
                      textAnchor="end"
                      tick={{ fontSize: 11, fill: '#64748b' }}
                      stroke="#cbd5e1"
                    />
                    <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: '#64748b' }} stroke="#cbd5e1" />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#ffffff',
                        border: '1px solid #e2e8f0',
                        borderRadius: '6px',
                        fontSize: '0.82rem',
                        boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
                      }}
                    />
                    <Bar dataKey="count" fill="#2563eb" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="text-center text-muted pt-5">No category data recorded.</div>
              )}
            </div>
          </div>
        </div>

        <div className="col-lg-6">
          <div className="cv-card h-100">
            <div className="cv-card-header">
              <h6 className="mb-0 fw-bold text-dark">Issues by Operational Status</h6>
            </div>
            <div className="cv-card-body" style={{ height: '300px' }}>
              {statusData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={statusData}
                      dataKey="count"
                      nameKey="status"
                      cx="50%"
                      cy="50%"
                      outerRadius={85}
                      label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                    >
                      {statusData.map((_: any, index: number) => (
                        <Cell key={`cell-${index}`} fill={CHART_PALETTE[index % CHART_PALETTE.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#ffffff',
                        border: '1px solid #e2e8f0',
                        borderRadius: '6px',
                        fontSize: '0.82rem',
                      }}
                    />
                    <Legend wrapperStyle={{ fontSize: '0.8rem' }} />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="text-center text-muted pt-5">No status data recorded.</div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Standalone Numerical Breakdown Tables */}
      <div className="row g-4 mb-4">
        {/* Category Table */}
        <div className="col-lg-6">
          <div className="cv-card h-100 overflow-hidden">
            <div className="cv-card-header">
              <h6 className="mb-0 fw-bold text-dark">Category Breakdown Table</h6>
            </div>
            <div className="cv-card-body p-0">
              {catData.length > 0 ? (
                <table className="cv-table">
                  <thead>
                    <tr>
                      <th>Category</th>
                      <th className="text-end">Submissions</th>
                      <th className="text-end" style={{ width: '120px' }}>Proportion</th>
                    </tr>
                  </thead>
                  <tbody>
                    {catData.map((c: any) => (
                      <tr key={c.category}>
                        <td className="fw-medium text-dark">{c.category}</td>
                        <td className="text-end font-monospace">{c.count}</td>
                        <td className="text-end">
                          <span className="cv-badge cv-badge-low">
                            {m.total_submissions > 0
                              ? `${((c.count / m.total_submissions) * 100).toFixed(1)}%`
                              : '0%'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="text-muted small p-4 mb-0">No category activity recorded.</p>
              )}
            </div>
          </div>
        </div>

        {/* Operational Status Table */}
        <div className="col-lg-6">
          <div className="cv-card h-100 overflow-hidden">
            <div className="cv-card-header">
              <h6 className="mb-0 fw-bold text-dark">Operational Status Table</h6>
            </div>
            <div className="cv-card-body p-0">
              {statusData.length > 0 ? (
                <table className="cv-table">
                  <thead>
                    <tr>
                      <th>Operational Status</th>
                      <th className="text-end">Count</th>
                      <th className="text-end" style={{ width: '120px' }}>Proportion</th>
                    </tr>
                  </thead>
                  <tbody>
                    {statusData.map((s: any) => (
                      <tr key={s.status}>
                        <td className="fw-medium text-dark text-capitalize">{s.status.replace('_', ' ')}</td>
                        <td className="text-end font-monospace">{s.count}</td>
                        <td className="text-end">
                          <span className="cv-badge cv-badge-low">
                            {m.distinct_issues > 0
                              ? `${((s.count / m.distinct_issues) * 100).toFixed(1)}%`
                              : '0%'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="text-muted small p-4 mb-0">No issues created yet.</p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Top Report Locations Across Campus */}
      <div className="cv-card">
        <div className="cv-card-header">
          <h6 className="mb-0 fw-bold text-dark">Top Report Locations Across Campus</h6>
        </div>
        <div className="cv-card-body p-4">
          {locData.length > 0 ? (
            <div className="row g-3">
              {locData.map((l: any) => (
                <div key={l.location} className="col-sm-6 col-md-3">
                  <div className="p-3 rounded border bg-white text-center">
                    <div className="fw-semibold text-dark text-truncate" title={l.location}>
                      {l.location}
                    </div>
                    <div className="fs-4 fw-bold text-primary mt-1 mb-0">{l.count}</div>
                    <span className="text-muted small" style={{ fontSize: '0.75rem' }}>reports logged</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-muted small mb-0">No location activity recorded.</p>
          )}
        </div>
      </div>
    </div>
  );
};
