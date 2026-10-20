import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { apiRequest } from '../api/client';
import { WishlistItem, PriceObservation, HistorySummary } from '../types';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';
import { ArrowLeft, ExternalLink, Plus, Trash2 } from 'lucide-react';

export const ItemDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [item, setItem] = useState<WishlistItem | null>(null);
  const [history, setHistory] = useState<PriceObservation[]>([]);
  const [summary, setSummary] = useState<HistorySummary | null>(null);
  const [range, setRange] = useState<string>('30d');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Manual observation modal / inputs
  const [showObsForm, setShowObsForm] = useState(false);
  const [newPrice, setNewPrice] = useState('');
  const [isSubmittingObs, setIsSubmittingObs] = useState(false);

  const loadData = async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const [itemData, histData, sumData] = await Promise.all([
        apiRequest<WishlistItem>(`/items/${id}`),
        apiRequest<PriceObservation[]>(`/items/${id}/history?range=${range}`),
        apiRequest<HistorySummary>(`/items/${id}/history/summary`),
      ]);
      setItem(itemData);
      setHistory(histData);
      setSummary(sumData);
    } catch (err: any) {
      setError(err.message || 'Failed to load product details');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [id, range]);

  const handleAddObservation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id || !newPrice.trim()) return;

    setIsSubmittingObs(true);
    try {
      const priceMinor = Math.round(parseFloat(newPrice) * 100);
      await apiRequest(`/items/${id}/observations`, {
        method: 'POST',
        body: JSON.stringify({
          price_minor: priceMinor,
          currency: item?.currency || 'INR',
          raw_price_text: newPrice.trim(),
        }),
      });
      setNewPrice('');
      setShowObsForm(false);
      await loadData();
    } catch (err: any) {
      alert(err.message || 'Failed to record price observation');
    } finally {
      setIsSubmittingObs(false);
    }
  };

  const formatPrice = (minor?: number, currency = 'INR') => {
    if (minor === undefined || minor === null) return 'N/A';
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: currency || 'INR',
      maximumFractionDigits: 2,
    }).format(minor / 100);
  };

  const chartData = history.map((obs) => ({
    date: new Date(obs.observed_at).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' }),
    price: obs.price_minor / 100,
  }));

  if (loading && !item) {
    return <div style={{ textAlign: 'center', padding: '60px 0', color: '#64748b' }}>Loading product details...</div>;
  }

  if (error || !item) {
    return (
      <div style={{ maxWidth: '640px', margin: '40px auto', textAlign: 'center' }}>
        <div style={{ backgroundColor: '#fef2f2', border: '1px solid #fecaca', color: '#b91c1c', padding: '16px', borderRadius: '8px', marginBottom: '16px' }}>
          {error || 'Item not found'}
        </div>
        <button onClick={() => navigate('/app/wishlist')} style={{ background: 'none', border: 'none', color: '#2563eb', cursor: 'pointer', fontWeight: '600' }}>
          &larr; Return to Wishlist
        </button>
      </div>
    );
  }

  return (
    <div>
      {/* Back button */}
      <button
        onClick={() => navigate('/app/wishlist')}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '6px',
          background: 'none',
          border: 'none',
          color: '#64748b',
          cursor: 'pointer',
          fontSize: '14px',
          marginBottom: '20px',
          padding: 0,
        }}
      >
        <ArrowLeft size={16} /> Back to Wishlist
      </button>

      {/* Header Info Card */}
      <div style={{ backgroundColor: '#ffffff', borderRadius: '12px', border: '1px solid #e2e8f0', padding: '16px', marginBottom: '20px', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '14px' }}>
          <div style={{ flex: '1 1 240px', minWidth: '200px' }}>
            <span style={{ fontSize: '11px', fontWeight: 'bold', color: '#2563eb', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              {item.retailer_host} &bull; {item.tracking_mode} mode
            </span>
            <h1 style={{ fontSize: 'clamp(18px, 4vw, 24px)', fontWeight: 'bold', color: '#0f172a', margin: '4px 0 10px 0', lineHeight: '1.3' }}>
              {item.title}
            </h1>

            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
              <a
                href={item.product_url}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  color: '#475569',
                  backgroundColor: '#f1f5f9',
                  padding: '5px 10px',
                  borderRadius: '6px',
                  fontSize: '12px',
                  textDecoration: 'none',
                  fontWeight: '500',
                }}
              >
                <ExternalLink size={13} /> Open Store
              </a>

              {item.tags.map((t) => (
                <span key={t} style={{ fontSize: '11px', backgroundColor: '#e2e8f0', color: '#334155', padding: '3px 8px', borderRadius: '4px' }}>
                  #{t}
                </span>
              ))}
            </div>
          </div>

          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', width: 'auto' }}>
            <button
              onClick={async () => {
                if (!item) return;
                const confirmDelete = window.confirm(`Permanently remove "${item.title}" from your wishlist?`);
                if (!confirmDelete) return;
                try {
                  await apiRequest(`/items/${item.id}?archive=false`, { method: 'DELETE' });
                  navigate('/app/wishlist');
                } catch (err: any) {
                  alert(err.message || 'Failed to delete item');
                }
              }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                backgroundColor: '#ffffff',
                color: '#ef4444',
                border: '1px solid #fecaca',
                padding: '8px 12px',
                borderRadius: '8px',
                fontWeight: '600',
                cursor: 'pointer',
                fontSize: '13px',
              }}
            >
              <Trash2 size={15} /> Delete
            </button>

            <button
              onClick={() => setShowObsForm(!showObsForm)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                backgroundColor: '#2563eb',
                color: '#ffffff',
                border: 'none',
                padding: '8px 14px',
                borderRadius: '8px',
                fontWeight: '600',
                cursor: 'pointer',
                fontSize: '13px',
              }}
            >
              <Plus size={15} /> Log Price
            </button>
          </div>
        </div>

        {/* Manual Observation Form */}
        {showObsForm && (
          <form
            onSubmit={handleAddObservation}
            style={{
              marginTop: '20px',
              padding: '16px',
              backgroundColor: '#f8fafc',
              borderRadius: '8px',
              border: '1px solid #cbd5e1',
              display: 'flex',
              gap: '12px',
              alignItems: 'flex-end',
              flexWrap: 'wrap',
            }}
          >
            <div style={{ flex: 1, minWidth: '180px' }}>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: '600', color: '#334155', marginBottom: '4px' }}>
                Observed Price ({item.currency || 'INR'})
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                required
                value={newPrice}
                onChange={(e) => setNewPrice(e.target.value)}
                placeholder="e.g. 19999.00"
                style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '14px', boxSizing: 'border-box' }}
              />
            </div>
            <button
              type="submit"
              disabled={isSubmittingObs}
              style={{
                backgroundColor: '#16a34a',
                color: '#ffffff',
                border: 'none',
                padding: '9px 16px',
                borderRadius: '6px',
                fontWeight: '600',
                cursor: isSubmittingObs ? 'not-allowed' : 'pointer',
                fontSize: '14px',
              }}
            >
              {isSubmittingObs ? 'Saving...' : 'Save Observation'}
            </button>
          </form>
        )}
      </div>

      {/* Metrics Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 140px), 1fr))', gap: '12px', marginBottom: '20px' }}>
        <div style={{ backgroundColor: '#ffffff', padding: '12px 14px', borderRadius: '10px', border: '1px solid #e2e8f0' }}>
          <div style={{ fontSize: '11px', color: '#64748b', fontWeight: '600', textTransform: 'uppercase' }}>Current Price</div>
          <div style={{ fontSize: 'clamp(18px, 4vw, 22px)', fontWeight: 'bold', color: '#0f172a', marginTop: '2px' }}>
            {formatPrice(summary?.current_price_minor, summary?.currency)}
          </div>
          {summary?.change_percent !== null && summary?.change_percent !== undefined && (
            <div style={{ fontSize: '11px', color: summary.change_percent <= 0 ? '#16a34a' : '#dc2626', marginTop: '2px', fontWeight: '600' }}>
              {summary.change_percent <= 0 ? '↓' : '↑'} {Math.abs(summary.change_percent)}%
            </div>
          )}
        </div>

        <div style={{ backgroundColor: '#ffffff', padding: '12px 14px', borderRadius: '10px', border: '1px solid #e2e8f0' }}>
          <div style={{ fontSize: '11px', color: '#64748b', fontWeight: '600', textTransform: 'uppercase' }}>365d Low</div>
          <div style={{ fontSize: 'clamp(18px, 4vw, 22px)', fontWeight: 'bold', color: '#16a34a', marginTop: '2px' }}>
            {formatPrice(summary?.lowest_365d_price_minor, summary?.currency)}
          </div>
          <div style={{ fontSize: '10px', color: '#94a3b8', marginTop: '2px' }}>Rolling low</div>
        </div>

        <div style={{ backgroundColor: '#ffffff', padding: '12px 14px', borderRadius: '10px', border: '1px solid #e2e8f0' }}>
          <div style={{ fontSize: '11px', color: '#64748b', fontWeight: '600', textTransform: 'uppercase' }}>Target</div>
          <div style={{ fontSize: 'clamp(18px, 4vw, 22px)', fontWeight: 'bold', color: '#2563eb', marginTop: '2px' }}>
            {item.target_price_minor ? formatPrice(item.target_price_minor, item.currency) : 'Not set'}
          </div>
          {summary?.target_reached && (
            <div style={{ fontSize: '11px', color: '#16a34a', fontWeight: '600', marginTop: '2px' }}>Hit!</div>
          )}
        </div>

        <div style={{ backgroundColor: '#ffffff', padding: '12px 14px', borderRadius: '10px', border: '1px solid #e2e8f0' }}>
          <div style={{ fontSize: '11px', color: '#64748b', fontWeight: '600', textTransform: 'uppercase' }}>Total Checks</div>
          <div style={{ fontSize: 'clamp(18px, 4vw, 22px)', fontWeight: 'bold', color: '#0f172a', marginTop: '2px' }}>
            {summary?.observation_count || 0}
          </div>
          <div style={{ fontSize: '10px', color: '#94a3b8', marginTop: '2px' }}>Recorded</div>
        </div>
      </div>

      {/* Chart Card */}
      <div style={{ backgroundColor: '#ffffff', borderRadius: '12px', border: '1px solid #e2e8f0', padding: '16px', marginBottom: '20px', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '10px' }}>
          <h2 style={{ fontSize: '16px', fontWeight: 'bold', color: '#1e293b', margin: 0 }}>Price History Chart</h2>
          <div style={{ display: 'flex', gap: '4px', overflowX: 'auto', WebkitOverflowScrolling: 'touch' }}>
            {['7d', '30d', '90d', '180d', '365d'].map((r) => (
              <button
                key={r}
                onClick={() => setRange(r)}
                style={{
                  padding: '5px 10px',
                  borderRadius: '6px',
                  border: '1px solid #cbd5e1',
                  backgroundColor: range === r ? '#2563eb' : '#ffffff',
                  color: range === r ? '#ffffff' : '#475569',
                  fontSize: '11px',
                  fontWeight: '600',
                  cursor: 'pointer',
                  flexShrink: 0,
                }}
              >
                {r}
              </button>
            ))}
          </div>
        </div>

        {chartData.length < 2 ? (
          <div style={{ textAlign: 'center', padding: '40px 0', color: '#94a3b8', fontSize: '14px' }}>
            Need at least 2 price observations to display trend chart. Log another price above to see graph!
          </div>
        ) : (
          <div style={{ height: '300px', width: '100%' }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="date" stroke="#94a3b8" fontSize={12} tickLine={false} />
                <YAxis stroke="#94a3b8" fontSize={12} tickLine={false} domain={['auto', 'auto']} />
                <Tooltip
                  formatter={(val: any) => [`₹${val}`, 'Price']}
                  contentStyle={{ backgroundColor: '#1e293b', color: '#ffffff', borderRadius: '8px', border: 'none' }}
                />
                <Line type="monotone" dataKey="price" stroke="#2563eb" strokeWidth={3} dot={{ r: 4, fill: '#2563eb' }} activeDot={{ r: 6 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Observation Table */}
      <div style={{ backgroundColor: '#ffffff', borderRadius: '12px', border: '1px solid #e2e8f0', padding: '24px', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
        <h2 style={{ fontSize: '18px', fontWeight: 'bold', color: '#1e293b', margin: '0 0 16px 0' }}>All Logged Observations</h2>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '14px' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #f1f5f9', color: '#64748b' }}>
                <th style={{ padding: '10px 12px' }}>Timestamp (UTC)</th>
                <th style={{ padding: '10px 12px' }}>Price</th>
                <th style={{ padding: '10px 12px' }}>Availability</th>
                <th style={{ padding: '10px 12px' }}>Source</th>
              </tr>
            </thead>
            <tbody>
              {history.map((obs) => (
                <tr key={obs.id} style={{ borderBottom: '1px solid #f8fafc' }}>
                  <td style={{ padding: '10px 12px', color: '#475569' }}>
                    {new Date(obs.observed_at).toLocaleString()}
                  </td>
                  <td style={{ padding: '10px 12px', fontWeight: 'bold', color: '#0f172a' }}>
                    {formatPrice(obs.price_minor, obs.currency)}
                  </td>
                  <td style={{ padding: '10px 12px' }}>
                    <span style={{ fontSize: '12px', backgroundColor: '#dcfce7', color: '#166534', padding: '2px 8px', borderRadius: '4px' }}>
                      {obs.availability}
                    </span>
                  </td>
                  <td style={{ padding: '10px 12px', color: '#64748b', textTransform: 'capitalize' }}>
                    {obs.source}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
