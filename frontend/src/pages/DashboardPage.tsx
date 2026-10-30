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

const COLORS = ['#0d6efd', '#20c997', '#ffc107', '#fd7e14', '#dc3545', '#6c757d', '#6610f2'];

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

  if (loading) return <div className="p-5 text-center text-muted">Loading metrics dashboard...</div>;
  if (!data) return <div className="alert alert-danger">Could not load operational metrics.</div>;

  const m = data.metrics || {};
  const catData = data.category_breakdown || [];
  const statusData = data.issue_status_breakdown || [];
  const locData = data.location_breakdown || [];

  return (
    <div>
      <div className="mb-4">
        <h3 className="mb-1 text-dark">
          <i className="bi bi-graph-up me-2"></i>Campus Operations & Metrics Dashboard
        </h3>
        <p className="text-muted small mb-0">
          All metrics are strictly calculated from live SQLite database records. No synthetic multipliers or simulated counts.
        </p>
      </div>

      {/* 6 Primary Metric Cards */}
      <div className="row g-3 mb-4">
        <div className="col-md-4 col-xl-2">
          <div className="card card-shadow border-0 bg-white p-3 text-center h-100">
            <span className="text-muted small fw-semibold text-uppercase">Total Submissions</span>
            <h2 className="display-6 fw-bold text-dark mt-2 mb-0">{m.total_submissions}</h2>
            <small className="text-muted">Raw user reports</small>
          </div>
        </div>
        <div className="col-md-4 col-xl-2">
          <div className="card card-shadow border-0 bg-white p-3 text-center h-100">
            <span className="text-muted small fw-semibold text-uppercase">Distinct Issues</span>
            <h2 className="display-6 fw-bold text-primary mt-2 mb-0">{m.distinct_issues}</h2>
            <small className="text-muted">Consolidated tasks</small>
          </div>
        </div>
        <div className="col-md-4 col-xl-2">
          <div className="card card-shadow border-0 bg-white p-3 text-center h-100">
            <span className="text-muted small fw-semibold text-uppercase">Unresolved Issues</span>
            <h2 className="display-6 fw-bold text-warning mt-2 mb-0">{m.unresolved_issues}</h2>
            <small className="text-muted">Active in progress</small>
          </div>
        </div>
        <div className="col-md-4 col-xl-2">
          <div className="card card-shadow border-0 bg-white p-3 text-center h-100">
            <span className="text-muted small fw-semibold text-uppercase">Urgent Reviews</span>
            <h2 className="display-6 fw-bold text-danger mt-2 mb-0">{m.urgent_reviews}</h2>
            <small className="text-muted">High-hazard flags</small>
          </div>
        </div>
        <div className="col-md-4 col-xl-2">
          <div className="card card-shadow border-0 bg-white p-3 text-center h-100">
            <span className="text-muted small fw-semibold text-uppercase">Resolved Issues</span>
            <h2 className="display-6 fw-bold text-success mt-2 mb-0">{m.resolved_issues}</h2>
            <small className="text-muted">Completed repairs</small>
          </div>
        </div>
        <div className="col-md-4 col-xl-2">
          <div className="card card-shadow border-0 bg-white p-3 text-center h-100">
            <span className="text-muted small fw-semibold text-uppercase">Disputed Feedback</span>
            <h2 className="display-6 fw-bold text-danger mt-2 mb-0">{m.disputed_resolutions}</h2>
            <small className="text-muted">Failed verification</small>
          </div>
        </div>
      </div>

      {/* Visual Recharts Charts */}
      <div className="row g-4 mb-4">
        <div className="col-lg-6">
          <div className="card card-shadow h-100">
            <div className="card-header bg-white py-3">
              <h5 className="mb-0 text-dark"><i className="bi bi-bar-chart me-2"></i>Reports by Category</h5>
            </div>
            <div className="card-body" style={{ height: '300px' }}>
              {catData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={catData} margin={{ top: 20, right: 30, left: 0, bottom: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="category" angle={-15} textAnchor="end" tick={{ fontSize: 11 }} />
                    <YAxis allowDecimals={false} />
                    <Tooltip />
                    <Bar dataKey="count" fill="#0d6efd" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="text-center text-muted pt-5">No category data logged.</div>
              )}
            </div>
          </div>
        </div>

        <div className="col-lg-6">
          <div className="card card-shadow h-100">
            <div className="card-header bg-white py-3">
              <h5 className="mb-0 text-dark"><i className="bi bi-pie-chart me-2"></i>Issues by Operational Status</h5>
            </div>
            <div className="card-body" style={{ height: '300px' }}>
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
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="text-center text-muted pt-5">No status data logged.</div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Standalone Numerical Breakdown Tables */}
      <div className="row g-4 mb-4">
        {/* Category Breakdown Table */}
        <div className="col-lg-6">
          <div className="card card-shadow h-100">
            <div className="card-header bg-white py-3">
              <h5 className="mb-0 text-dark"><i className="bi bi-table me-2"></i>Category Breakdown Data Table</h5>
            </div>
            <div className="card-body">
              {catData.length > 0 ? (
                <table className="table table-hover align-middle mb-0">
                  <thead className="table-light">
                    <tr>
                      <th>Category</th>
                      <th className="text-end">Submissions</th>
                      <th className="text-end" style={{ width: '130px' }}>Proportion</th>
                    </tr>
                  </thead>
                  <tbody>
                    {catData.map((c: any) => (
                      <tr key={c.category}>
                        <td><strong>{c.category}</strong></td>
                        <td className="text-end font-monospace">{c.count}</td>
                        <td className="text-end">
                          <span className="badge bg-secondary-subtle text-secondary">
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
                <p className="text-muted small">No category activity recorded.</p>
              )}
            </div>
          </div>
        </div>

        {/* Issue Status Breakdown Table */}
        <div className="col-lg-6">
          <div className="card card-shadow h-100">
            <div className="card-header bg-white py-3">
              <h5 className="mb-0 text-dark"><i className="bi bi-table me-2"></i>Operational Status Data Table</h5>
            </div>
            <div className="card-body">
              {statusData.length > 0 ? (
                <table className="table table-hover align-middle mb-0">
                  <thead className="table-light">
                    <tr>
                      <th>Operational Status</th>
                      <th className="text-end">Count</th>
                      <th className="text-end" style={{ width: '130px' }}>Proportion</th>
                    </tr>
                  </thead>
                  <tbody>
                    {statusData.map((s: any) => (
                      <tr key={s.status}>
                        <td><strong className="text-capitalize">{s.status.replace('_', ' ')}</strong></td>
                        <td className="text-end font-monospace">{s.count}</td>
                        <td className="text-end">
                          <span className="badge bg-secondary-subtle text-secondary">
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
                <p className="text-muted small">No issues created yet.</p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Location Distribution */}
      <div className="card card-shadow">
        <div className="card-header bg-white py-3">
          <h5 className="mb-0 text-dark"><i className="bi bi-geo-alt me-2"></i>Top Report Locations Across Campus</h5>
        </div>
        <div className="card-body">
          {locData.length > 0 ? (
            <div className="row g-3">
              {locData.map((l: any) => (
                <div key={l.location} className="col-md-3">
                  <div className="border rounded p-3 bg-light text-center">
                    <div className="fw-semibold text-truncate" title={l.location}>
                      {l.location}
                    </div>
                    <div className="h4 text-primary mt-1 mb-0">{l.count}</div>
                    <small className="text-muted">reports logged</small>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-muted small">No location activity recorded.</p>
          )}
        </div>
      </div>
    </div>
  );
};

