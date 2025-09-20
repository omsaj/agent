import { CSSProperties, useCallback, useEffect, useMemo, useState } from 'react';
import { CSVLink } from 'react-csv';
import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts';
import classNames from 'classnames';
import './CyberScope.scss';

export interface ThreatData {
  cve_id: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM';
  cvss_score: number;
  title: string;
  published_date: string;
  analysis?: {
    summary: string;
    risk_score: number;
    mitigation_advice: string;
  };
}

interface SummaryMetrics {
  critical: number;
  high: number;
  medium: number;
  trending: number;
  total_analyzed: number;
  last_update?: string;
}

interface TrendPoint {
  date: string;
  count: number;
}

interface CategoryDistributionItem {
  name: string;
  value: number;
}

interface ThreatResponse {
  items: ThreatData[];
  total: number;
}

interface MetricCardProps {
  label: string;
  value: number;
  tone: 'critical' | 'high' | 'medium' | 'info';
}

const MetricCard = ({ label, value, tone }: MetricCardProps) => (
  <div
    className={classNames('metric-card', tone)}
    style={{ '--accent-color': SEVERITY_COLORS[tone] } as CSSProperties}
  >
    <span className="metric-card__label">{label}</span>
    <span className="metric-card__value">{value}</span>
  </div>
);

interface ThreatTableProps {
  threats: ThreatData[];
  onSelect: (threat: ThreatData) => void;
}

const ThreatTable = ({ threats, onSelect }: ThreatTableProps) => {
  const [sortField, setSortField] = useState<'cvss_score' | 'published_date'>('published_date');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');

  const sortedThreats = useMemo(() => {
    const clone = [...threats];
    clone.sort((a, b) => {
      const multiplier = sortDirection === 'asc' ? 1 : -1;
      if (sortField === 'cvss_score') {
        return (a.cvss_score - b.cvss_score) * multiplier;
      }
      return (new Date(a.published_date).getTime() - new Date(b.published_date).getTime()) * multiplier;
    });
    return clone;
  }, [threats, sortDirection, sortField]);

  const handleSort = (field: 'cvss_score' | 'published_date') => {
    if (sortField === field) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  return (
    <div className="threat-table">
      <table>
        <thead>
          <tr>
            <th>Severity</th>
            <th onClick={() => handleSort('cvss_score')} role="button" tabIndex={0}>
              CVSS Score
            </th>
            <th>Title</th>
            <th onClick={() => handleSort('published_date')} role="button" tabIndex={0}>
              Published
            </th>
          </tr>
        </thead>
        <tbody>
          {sortedThreats.map((threat) => (
            <tr key={threat.cve_id} onClick={() => onSelect(threat)}>
              <td>
                <span className={classNames('severity-pill', threat.severity.toLowerCase())}>{threat.severity}</span>
              </td>
              <td>{threat.cvss_score?.toFixed(1) ?? 'N/A'}</td>
              <td>{threat.title}</td>
              <td>{new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(threat.published_date))}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

interface ThreatTimelineProps {
  data: TrendPoint[];
}

const ThreatTimeline = ({ data }: ThreatTimelineProps) => (
  <div className="timeline-card">
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data}>
        <XAxis dataKey="date" tickFormatter={(value) => new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric' }).format(new Date(value))} />
        <YAxis allowDecimals={false} />
        <RechartsTooltip labelFormatter={(value) => new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value))} />
        <Line type="monotone" dataKey="count" stroke="#4f46e5" strokeWidth={3} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  </div>
);

interface CategoryDistributionProps {
  data: CategoryDistributionItem[];
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: '#ef4444',
  high: '#fb923c',
  medium: '#facc15',
  info: '#38bdf8',
};

const PIE_COLORS = ['#4f46e5', '#22c55e', '#f97316', '#38bdf8', '#e879f9', '#facc15'];

const CategoryDistribution = ({ data }: CategoryDistributionProps) => (
  <div className="category-card">
    <ResponsiveContainer width="100%" height={320}>
      <PieChart>
        <Pie data={data} innerRadius={60} outerRadius={110} paddingAngle={3} dataKey="value" nameKey="name">
          {data.map((entry, index) => (
            <Cell key={entry.name} fill={PIE_COLORS[index % PIE_COLORS.length]} />
          ))}
        </Pie>
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  </div>
);

interface ThreatDetailProps {
  threat: ThreatData | null;
  onClose: () => void;
}

const ThreatDetail = ({ threat, onClose }: ThreatDetailProps) => {
  if (!threat) return null;

  return (
    <div className="threat-detail" role="dialog" aria-modal>
      <div className="threat-detail__content">
        <button className="threat-detail__close" onClick={onClose}>
          ✕
        </button>
        <h2>{threat.title}</h2>
        <div className="threat-detail__meta">
          <span className={classNames('severity-pill', threat.severity.toLowerCase())}>{threat.severity}</span>
          <span>CVSS: {threat.cvss_score?.toFixed(1) ?? 'N/A'}</span>
          <span>Published: {new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(threat.published_date))}</span>
        </div>
        <section>
          <h3>Summary</h3>
          <p>{threat.analysis?.summary ?? 'Analysis pending.'}</p>
        </section>
        <section>
          <h3>Mitigation Advice</h3>
          <p>{threat.analysis?.mitigation_advice ?? 'Monitor vendor guidance.'}</p>
        </section>
      </div>
    </div>
  );
};

const useAutoRefresh = (callback: () => void, intervalMs: number) => {
  useEffect(() => {
    callback();
    const id = window.setInterval(callback, intervalMs);
    return () => window.clearInterval(id);
  }, [callback, intervalMs]);
};

const fetchJson = async <T,>(url: string): Promise<T> => {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
};

export const CyberScope = () => {
  const [summary, setSummary] = useState<SummaryMetrics | null>(null);
  const [threats, setThreats] = useState<ThreatData[]>([]);
  const [trends, setTrends] = useState<TrendPoint[]>([]);
  const [categories, setCategories] = useState<CategoryDistributionItem[]>([]);
  const [selectedThreat, setSelectedThreat] = useState<ThreatData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [summaryResponse, threatResponse, trendsResponse, metricsResponse] = await Promise.all([
        fetchJson<SummaryMetrics>('/api/dashboard/summary'),
        fetchJson<ThreatResponse>('/api/dashboard/threats?limit=20'),
        fetchJson<{ points: TrendPoint[] }>('/api/dashboard/trends?period=7d'),
        fetchJson<{ metrics: Record<string, number> }>('/api/dashboard/metrics').catch(() => ({ metrics: {} })),
      ]);
      setSummary(summaryResponse);
      setThreats(threatResponse.items);
      setTrends(
        trendsResponse.points.map((point) => ({
          ...point,
          date: new Date(point.date).toISOString(),
        })),
      );
      const distribution = Object.entries(metricsResponse.metrics?.categories ?? {}).map(([name, value]) => ({
        name,
        value: Number(value),
      }));
      setCategories(distribution);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  }, []);

  useAutoRefresh(loadData, 5 * 60 * 1000);

  const csvData = useMemo(
    () =>
      threats.map((threat) => ({
        cve_id: threat.cve_id,
        severity: threat.severity,
        cvss_score: threat.cvss_score,
        title: threat.title,
        published_date: threat.published_date,
        summary: threat.analysis?.summary ?? '',
        mitigation: threat.analysis?.mitigation_advice ?? '',
      })),
    [threats],
  );

  return (
    <div className="cyberscope" data-theme="light">
      <header className="cyberscope__header">
        <h1>CyberScope Threat Dashboard</h1>
        <div className="cyberscope__actions">
          <CSVLink data={csvData} filename="cyberscope-threats.csv" className="button">
            Export CSV
          </CSVLink>
          {summary?.last_update && <span className="last-update">Last updated: {new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(summary.last_update))}</span>}
        </div>
      </header>

      {error && <div className="alert alert--error">{error}</div>}

      <section className={classNames('metric-grid', { 'metric-grid--loading': loading })}>
        <MetricCard label="Critical" value={summary?.critical ?? 0} tone="critical" />
        <MetricCard label="High" value={summary?.high ?? 0} tone="high" />
        <MetricCard label="Medium" value={summary?.medium ?? 0} tone="medium" />
        <MetricCard label="Trending" value={summary?.trending ?? 0} tone="info" />
      </section>

      <section className="content-grid">
        <div className="content-grid__primary">
          <h2>Recent Threats</h2>
          <ThreatTable threats={threats} onSelect={setSelectedThreat} />
        </div>
        <aside className="content-grid__secondary">
          <h2>7 Day Trend</h2>
          <ThreatTimeline data={trends} />
          <h2>Categories</h2>
          <CategoryDistribution data={categories} />
        </aside>
      </section>

      {selectedThreat && <ThreatDetail threat={selectedThreat} onClose={() => setSelectedThreat(null)} />}
    </div>
  );
};

export default CyberScope;
