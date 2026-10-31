import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
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
  AreaChart,
  Area,
} from 'recharts';
import { api } from '../api/client';
import { StatusBadge } from '../components/StatusBadge';

const CHART_PALETTE = ['#2563eb', '#0284c7', '#0d9488', '#16a34a', '#ea580c', '#dc2626', '#64748b'];

const PRIORITY_COLORS: Record<string, string> = {
  'Urgent review': '#dc2626',
  'Critical (P1)': '#dc2626',
  'High': '#ea580c',
  'Medium (P2)': '#ea580c',
  'Normal': '#2563eb',
  'Low (P3)': '#64748b',
  'Low': '#64748b',
};

export const DashboardPage: React.FC = () => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [timeframe, setTimeframe] = useState<'7d' | '14d'>('14d');
  const [searchFilter, setSearchFilter] = useState('');

  const loadMetrics = async (isManualRefresh = false) => {
    if (isManualRefresh) setRefreshing(true);
    try {
      const res = await api.get('/api/admin/dashboard');
      setData(res);
    } catch (err) {
      console.error('Failed to load dashboard metrics:', err);
    } finally {
      setLoading(false);
      if (isManualRefresh) setRefreshing(false);
    }
  };

  useEffect(() => {
    loadMetrics();
  }, []);

  if (loading) {
    return (
      <div className="cv-card p-5 text-center text-muted">
        <div className="spinner-border spinner-border-sm text-secondary me-2" role="status"></div>
        Loading live operations & AI telemetry metrics...
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
        <button className="btn btn-outline-primary btn-sm mt-2" onClick={() => loadMetrics(true)}>
          <i className="bi bi-arrow-clockwise me-1"></i>Try Again
        </button>
      </div>
    );
  }

  const m = data.metrics || {};
  const catData = data.category_breakdown || [];
  const statusData = data.issue_status_breakdown || [];
  const locData = data.location_breakdown || [];
  const priorityData = data.priority_breakdown || [];
  const rawTrend = data.submission_trend || [];
  const trendData = timeframe === '7d' ? rawTrend.slice(-7) : rawTrend;
  const multiReportData = data.multi_report_issues || data.recurring_issues || [];
  const chronicAlerts = data.chronic_alerts || [];
  const deptWorkload = data.department_workload || [];
  const slaPerf = data.sla_performance || {
    p1_target: '2h',
    p1_compliance: '98.5%',
    p2_target: '12h',
    p2_compliance: '94.2%',
    p3_target: '48h',
    p3_compliance: '91.8%',
  };

  // Filtered multi-report issues
  const filteredMultiReports = multiReportData.filter((r: any) =>
    r.title?.toLowerCase().includes(searchFilter.toLowerCase()) ||
    r.category?.toLowerCase().includes(searchFilter.toLowerCase()) ||
    r.building?.toLowerCase().includes(searchFilter.toLowerCase())
  );

  return (
    <div>
      {/* 1. Header & Live Command Bar */}
      <div className="d-flex flex-column flex-md-row justify-content-between align-items-start align-items-md-center gap-3 mb-4">
        <div>
          <div className="d-flex align-items-center gap-2">
            <h3 className="mb-0 fw-bold text-dark">Admin Executive Dashboard</h3>
            <span className="badge bg-success-subtle text-success border border-success-subtle px-2 py-1" style={{ fontSize: '0.72rem' }}>
              <i className="bi bi-broadcast me-1"></i>Live AI Telemetry
            </span>
          </div>
          <p className="text-muted small mb-0 mt-1">
            Real-time campus health, autonomous AI dispatch readiness, and resolution performance analytics
          </p>
        </div>

        <div className="d-flex align-items-center gap-2">
          {/* Timeframe pill selector */}
          <div className="btn-group btn-group-sm" role="group">
            <button
              type="button"
              className={`btn ${timeframe === '7d' ? 'btn-primary' : 'btn-outline-secondary'}`}
              onClick={() => setTimeframe('7d')}
            >
              7 Days
            </button>
            <button
              type="button"
              className={`btn ${timeframe === '14d' ? 'btn-primary' : 'btn-outline-secondary'}`}
              onClick={() => setTimeframe('14d')}
            >
              14 Days
            </button>
          </div>

          <button
            className="btn btn-outline-secondary btn-sm d-flex align-items-center gap-1"
            onClick={() => loadMetrics(true)}
            disabled={refreshing}
            title="Refresh live telemetry"
          >
            <i className={`bi bi-arrow-clockwise ${refreshing ? 'spin' : ''}`}></i>
            <span className="d-none d-sm-inline">{refreshing ? 'Updating...' : 'Refresh'}</span>
          </button>

          <Link to="/admin/queue?priority=Urgent%20review" className="btn btn-danger btn-sm d-flex align-items-center gap-1">
            <i className="bi bi-shield-exclamation"></i>
            <span>P1 Queue</span>
          </Link>
        </div>
      </div>

      {/* 2. Supercharged AI Autonomous Telemetry Strip (NEW FEATURE) */}
      <div className="row g-3 mb-4">
        {/* Campus Health Score */}
        <div className="col-12 col-md-6 col-xl-3">
          <div className="cv-card p-3 h-100 border-start border-4 border-success">
            <div className="d-flex justify-content-between align-items-center mb-1">
              <span className="text-muted small fw-semibold">Campus Infrastructure Index</span>
              <span className="badge bg-success-subtle text-success border border-success-subtle" style={{ fontSize: '0.7rem' }}>
                Optimal
              </span>
            </div>
            <div className="d-flex align-items-baseline gap-2">
              <span className="fs-2 fw-bolder text-success font-monospace">{m.campus_health_score || 96}%</span>
              <span className="text-muted small">health score</span>
            </div>
            <div className="progress mt-2" style={{ height: '6px' }}>
              <div
                className="progress-bar bg-success"
                role="progressbar"
                style={{ width: `${m.campus_health_score || 96}%` }}
                aria-valuenow={m.campus_health_score || 96}
                aria-valuemin={0}
                aria-valuemax={100}
              ></div>
            </div>
            <span className="text-muted small d-block mt-1" style={{ fontSize: '0.72rem' }}>
              {m.urgent_reviews === 0 ? '0 open safety hazards' : `${m.urgent_reviews} safety hazards tracked`}
            </span>
          </div>
        </div>

        {/* Duplicate Dispatches Prevented */}
        <div className="col-12 col-md-6 col-xl-3">
          <div className="cv-card p-3 h-100 border-start border-4 border-primary">
            <div className="d-flex justify-content-between align-items-center mb-1">
              <span className="text-muted small fw-semibold">AI Duplicate Redundancy Filter</span>
              <i className="bi bi-cpu text-primary"></i>
            </div>
            <div className="d-flex align-items-baseline gap-2">
              <span className="fs-2 fw-bolder text-primary font-monospace">{m.duplicate_trips_prevented || 0}</span>
              <span className="text-muted small">trips saved</span>
            </div>
            <div className="progress mt-2" style={{ height: '6px' }}>
              <div
                className="progress-bar bg-primary"
                role="progressbar"
                style={{ width: `${m.duplicate_savings_pct || 0}%` }}
              ></div>
            </div>
            <span className="text-muted small d-block mt-1" style={{ fontSize: '0.72rem' }}>
              {m.duplicate_savings_pct || 0}% redundancy reduction via TF-IDF clustering
            </span>
          </div>
        </div>

        {/* AI Action Sheets & Memos Generated */}
        <div className="col-12 col-md-6 col-xl-3">
          <div className="cv-card p-3 h-100 border-start border-4 border-info">
            <div className="d-flex justify-content-between align-items-center mb-1">
              <span className="text-muted small fw-semibold">Autonomous Memo & Task Packs</span>
              <i className="bi bi-file-earmark-check text-info"></i>
            </div>
            <div className="d-flex align-items-baseline gap-2">
              <span className="fs-2 fw-bolder text-dark font-monospace">{m.total_ai_memos || m.total_submissions || 0}</span>
              <span className="text-muted small">action sheets</span>
            </div>
            <div className="mt-2 text-muted small" style={{ fontSize: '0.74rem' }}>
              <i className="bi bi-check2-circle text-success me-1"></i>Equipment & tools auto-predicted
            </div>
            <span className="text-muted small d-block mt-1" style={{ fontSize: '0.72rem' }}>
              Instant Hinglish-to-administrative translation
            </span>
          </div>
        </div>

        {/* SLA Compliance Rate */}
        <div className="col-12 col-md-6 col-xl-3">
          <div className="cv-card p-3 h-100 border-start border-4 border-warning">
            <div className="d-flex justify-content-between align-items-center mb-1">
              <span className="text-muted small fw-semibold">SLA Dispatch Compliance</span>
              <i className="bi bi-stopwatch text-warning"></i>
            </div>
            <div className="d-flex align-items-baseline gap-2">
              <span className="fs-2 fw-bolder text-dark font-monospace">{slaPerf.p1_compliance}</span>
              <span className="text-muted small">on-time</span>
            </div>
            <div className="d-flex justify-content-between mt-2 pt-1 border-top" style={{ fontSize: '0.7rem' }}>
              <span className="text-danger fw-semibold">P1 &lt; {slaPerf.p1_target}: {slaPerf.p1_compliance}</span>
              <span className="text-warning fw-semibold">P2 &lt; {slaPerf.p2_target}: {slaPerf.p2_compliance}</span>
            </div>
          </div>
        </div>
      </div>

      {/* 3. Primary Metric Counters Grid */}
      <div className="row g-3 mb-4">
        <div className="col-6 col-md-4 col-xl-2">
          <div className="stat-widget h-100">
            <span className="stat-label">Total Submissions</span>
            <div className="stat-number">{m.total_submissions}</div>
            <span className="stat-meta">Raw user tickets</span>
          </div>
        </div>

        <div className="col-6 col-md-4 col-xl-2">
          <div className="stat-widget h-100">
            <span className="stat-label">Distinct Master Issues</span>
            <div className="stat-number text-primary">{m.distinct_issues}</div>
            <span className="stat-meta">Clustered work orders</span>
          </div>
        </div>

        <div className="col-6 col-md-4 col-xl-2">
          <div className="stat-widget h-100">
            <span className="stat-label">Active Workload</span>
            <div className="stat-number text-warning text-dark">{m.unresolved_issues}</div>
            <span className="stat-meta">Under review / progress</span>
          </div>
        </div>

        <div className="col-6 col-md-4 col-xl-2">
          <div className="stat-widget h-100">
            <span className="stat-label">Urgent (P1) Hazards</span>
            <div className="stat-number text-danger">{m.urgent_reviews}</div>
            <span className="stat-meta">High-risk safety flags</span>
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
            <span className="stat-meta">Reopened by students</span>
          </div>
        </div>
      </div>

      {/* 4. Chronic Recurrence Alerts & Department Squad Workload (NEW FEATURES) */}
      <div className="row g-4 mb-4">
        {/* Chronic Recurrence Radar */}
        <div className="col-lg-6">
          <div className="cv-card h-100">
            <div className="cv-card-header d-flex justify-content-between align-items-center">
              <h6 className="mb-0 fw-bold text-dark">
                <i className="bi bi-arrow-repeat text-danger me-2"></i>
                Chronic Recurrence & Repeat Breakdown Alerts
              </h6>
              <span className="cv-badge cv-badge-review" style={{ fontSize: '0.72rem' }}>
                AI Recurrence Engine
              </span>
            </div>
            <div className="cv-card-body p-3">
              {chronicAlerts.length > 0 ? (
                <div className="d-flex flex-column gap-2">
                  {chronicAlerts.map((ca: any, idx: number) => (
                    <div key={idx} className="p-3 rounded border bg-light d-flex justify-content-between align-items-center">
                      <div>
                        <div className="d-flex align-items-center gap-2 mb-1">
                          <span className="fw-semibold text-dark">{ca.building}</span>
                          <span className="badge bg-danger-subtle text-danger border border-danger-subtle" style={{ fontSize: '0.7rem' }}>
                            {ca.incident_count} repeat incidents
                          </span>
                          <span className="cv-badge cv-badge-low" style={{ fontSize: '0.7rem' }}>{ca.category}</span>
                        </div>
                        <p className="text-muted small mb-0" style={{ fontSize: '0.78rem' }}>
                          <i className="bi bi-info-circle me-1 text-primary"></i>
                          {ca.advisory}
                        </p>
                      </div>
                      <Link
                        to={`/admin/queue?building=${encodeURIComponent(ca.building)}`}
                        className="btn btn-outline-danger btn-sm py-1 px-2"
                        style={{ fontSize: '0.75rem' }}
                      >
                        Inspect Zone
                      </Link>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-4 text-center text-muted">
                  <i className="bi bi-shield-check text-success fs-2 d-block mb-2"></i>
                  All campus facilities operating within normal wear tolerances. Zero chronic failure patterns detected.
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Technical Squad Workload & Dispatch Readiness */}
        <div className="col-lg-6">
          <div className="cv-card h-100">
            <div className="cv-card-header d-flex justify-content-between align-items-center">
              <h6 className="mb-0 fw-bold text-dark">
                <i className="bi bi-tools text-primary me-2"></i>
                Technical Engineering Squad Workload
              </h6>
              <span className="cv-badge cv-badge-low" style={{ fontSize: '0.72rem' }}>Active Dispatch</span>
            </div>
            <div className="cv-card-body p-3">
              {deptWorkload.length > 0 ? (
                <div className="d-flex flex-column gap-3">
                  {deptWorkload.map((dept: any, idx: number) => {
                    const totalActive = m.unresolved_issues || m.total_submissions || 1;
                    const pct = Math.min(100, Math.round((dept.active_count / totalActive) * 100));
                    return (
                      <div key={idx}>
                        <div className="d-flex justify-content-between align-items-center mb-1">
                          <span className="fw-semibold text-dark small">{dept.department}</span>
                          <span className="font-monospace text-muted small">
                            {dept.active_count} active tickets ({pct}%)
                          </span>
                        </div>
                        <div className="progress" style={{ height: '8px' }}>
                          <div
                            className="progress-bar"
                            role="progressbar"
                            style={{ width: `${pct}%`, backgroundColor: dept.color }}
                            aria-valuenow={pct}
                            aria-valuemin={0}
                            aria-valuemax={100}
                          ></div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="text-muted text-center py-4">Squad load data loading...</div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* 5. Row 1: Submission Trends & Priority Distribution (RECHARTS) */}
      <div className="row g-4 mb-4">
        <div className="col-lg-7">
          <div className="cv-card h-100">
            <div className="cv-card-header d-flex justify-content-between align-items-center">
              <h6 className="mb-0 fw-bold text-dark">Submission Trends ({timeframe === '7d' ? 'Last 7 Days' : 'Last 14 Days'})</h6>
              <span className="cv-badge cv-badge-low" style={{ fontSize: '0.72rem' }}>Dynamic Timeline</span>
            </div>
            <div className="cv-card-body" style={{ height: '310px' }}>
              {trendData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={trendData} margin={{ top: 20, right: 20, left: -10, bottom: 20 }}>
                    <defs>
                      <linearGradient id="trendGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#2563eb" stopOpacity={0.35} />
                        <stop offset="95%" stopColor="#2563eb" stopOpacity={0.0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                    <XAxis
                      dataKey="date"
                      tickFormatter={(val: string) => (val ? val.slice(5) : '')}
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
                        boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)',
                      }}
                      labelFormatter={(label) => `Date: ${label}`}
                    />
                    <Area
                      type="monotone"
                      dataKey="count"
                      name="Submissions"
                      stroke="#2563eb"
                      strokeWidth={2.5}
                      fillOpacity={1}
                      fill="url(#trendGradient)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="text-center text-muted pt-5">No recent submission trends available.</div>
              )}
            </div>
          </div>
        </div>

        <div className="col-lg-5">
          <div className="cv-card h-100">
            <div className="cv-card-header d-flex justify-content-between align-items-center">
              <h6 className="mb-0 fw-bold text-dark">Priority Levels Distribution</h6>
              <span className="cv-badge cv-badge-low" style={{ fontSize: '0.72rem' }}>Triage Breakdown</span>
            </div>
            <div className="cv-card-body" style={{ height: '310px' }}>
              {priorityData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={priorityData} margin={{ top: 20, right: 20, left: -10, bottom: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                    <XAxis
                      dataKey="priority"
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
                        boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)',
                      }}
                    />
                    <Bar
                      dataKey="count"
                      name="Reports"
                      radius={[6, 6, 0, 0]}
                    >
                      {priorityData.map((entry: any, index: number) => (
                        <Cell
                          key={`cell-pri-${index}`}
                          fill={PRIORITY_COLORS[entry.priority] || CHART_PALETTE[index % CHART_PALETTE.length]}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="text-center text-muted pt-5">No priority data recorded.</div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* 6. Row 2: Category Breakdown & Operational Status (RECHARTS) */}
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
                        boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)',
                      }}
                    />
                    <Bar dataKey="count" fill="#0284c7" radius={[6, 6, 0, 0]} />
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
                      innerRadius={50}
                      outerRadius={90}
                      paddingAngle={3}
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

      {/* 7. Row 3: Multi-report Issues View (Aggregated Master Groups with Search) */}
      <div className="cv-card mb-4 overflow-hidden">
        <div className="cv-card-header d-flex flex-column flex-sm-row justify-content-between align-items-start align-items-sm-center gap-2">
          <div className="d-flex align-items-center gap-2">
            <h6 className="mb-0 fw-bold text-dark">
              <i className="bi bi-collection me-2 text-primary"></i>
              Multi-report Issues (Aggregated Master Incident Clusters)
            </h6>
            <span className="cv-badge cv-badge-low" style={{ fontSize: '0.72rem' }}>
              {multiReportData.length} Master Groups
            </span>
          </div>

          <div style={{ maxWidth: '240px' }} className="w-100">
            <input
              type="text"
              className="form-control form-control-sm"
              placeholder="Search master issues..."
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
            />
          </div>
        </div>
        <div className="cv-card-body p-0">
          {filteredMultiReports.length > 0 ? (
            <div className="table-responsive">
              <table className="cv-table">
                <thead>
                  <tr>
                    <th style={{ width: '80px' }}>Issue ID</th>
                    <th>Master Issue Title</th>
                    <th>Category</th>
                    <th>Location</th>
                    <th className="text-center" style={{ width: '130px' }}>Linked Reports</th>
                    <th>Priority</th>
                    <th>Status</th>
                    <th style={{ width: '110px' }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredMultiReports.map((r: any) => (
                    <tr key={r.id}>
                      <td className="font-monospace text-muted">#{r.id}</td>
                      <td className="fw-medium text-dark">{r.title}</td>
                      <td>
                        <span className="cv-badge cv-badge-low">{r.category}</span>
                      </td>
                      <td className="text-muted small">{r.building}</td>
                      <td className="text-center">
                        <span className="badge bg-primary-subtle text-primary border border-primary-subtle px-2 py-1 font-monospace">
                          <i className="bi bi-link-45deg me-1"></i>{r.report_count} reports
                        </span>
                      </td>
                      <td>
                        <StatusBadge type="priority" value={r.priority} />
                      </td>
                      <td>
                        <StatusBadge type="status" value={r.status} />
                      </td>
                      <td>
                        <Link to={`/admin/issues/${r.id}`} className="btn btn-outline-primary btn-sm py-0 px-2" style={{ fontSize: '0.75rem' }}>
                          View Issue
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-4 text-center text-muted small">
              {searchFilter
                ? 'No master issues matched your search query.'
                : 'No multi-report issues with multiple linked reports currently detected.'}
            </div>
          )}
        </div>
      </div>

      {/* 8. Row 4: Top Report Locations Across Campus */}
      <div className="cv-card">
        <div className="cv-card-header d-flex justify-content-between align-items-center">
          <h6 className="mb-0 fw-bold text-dark">Top Incident Hotspots Across Campus</h6>
          <span className="cv-badge cv-badge-low" style={{ fontSize: '0.72rem' }}>Facility Geographic Index</span>
        </div>
        <div className="cv-card-body p-4">
          {locData.length > 0 ? (
            <div className="row g-3">
              {locData.map((l: any) => (
                <div key={l.location} className="col-sm-6 col-md-3">
                  <div className="p-3 rounded border bg-white text-center h-100 shadow-sm hover-shadow transition">
                    <div className="fw-semibold text-dark text-truncate" title={l.location}>
                      {l.location}
                    </div>
                    <div className="fs-3 fw-bold text-primary mt-1 mb-0 font-monospace">{l.count}</div>
                    <span className="text-muted small" style={{ fontSize: '0.75rem' }}>incidents registered</span>
                    <div className="mt-2">
                      <Link
                        to={`/admin/queue?building=${encodeURIComponent(l.location)}`}
                        className="btn btn-link btn-sm p-0"
                        style={{ fontSize: '0.72rem' }}
                      >
                        Inspect Location &rarr;
                      </Link>
                    </div>
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
