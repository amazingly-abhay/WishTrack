import React, { useState, useEffect } from 'react';
import { apiRequest } from '../api/client';
import { Bell, CheckCheck, TrendingDown, Target, ArrowDownRight } from 'lucide-react';

interface NotificationItem {
  id: string;
  type: string;
  title: string;
  body: string;
  payload: Record<string, any>;
  read_at?: string;
  created_at: string;
}

interface Preferences {
  in_app_enabled: boolean;
  web_push_enabled: boolean;
  price_drop_enabled: boolean;
  target_reached_enabled: boolean;
  new_low_enabled: boolean;
  minimum_drop_percent?: number;
}

export const NotificationsPage: React.FC = () => {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [preferences, setPreferences] = useState<Preferences | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'inbox' | 'preferences'>('inbox');
  const [savingPrefs, setSavingPrefs] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const [notifData, prefData] = await Promise.all([
        apiRequest<{ items: NotificationItem[]; total: number }>('/notifications?limit=50'),
        apiRequest<Preferences>('/notifications/preferences'),
      ]);
      setNotifications(notifData.items);
      setPreferences(prefData);
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleMarkAllRead = async () => {
    try {
      await apiRequest('/notifications/read-all', { method: 'POST' });
      setNotifications((prev) => prev.map((n) => ({ ...n, read_at: new Date().toISOString() })));
    } catch (err: any) {
      alert(err.message || 'Failed to mark read');
    }
  };

  const handleSavePreferences = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!preferences) return;

    setSavingPrefs(true);
    try {
      const updated = await apiRequest<Preferences>('/notifications/preferences', {
        method: 'PATCH',
        body: JSON.stringify(preferences),
      });
      setPreferences(updated);
      alert('Preferences updated successfully!');
    } catch (err: any) {
      alert(err.message || 'Failed to update preferences');
    } finally {
      setSavingPrefs(false);
    }
  };

  return (
    <div style={{ maxWidth: '720px', margin: '0 auto' }}>
      {/* Header & Tabs */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h1 style={{ fontSize: 'clamp(20px, 4vw, 24px)', fontWeight: 'bold', margin: '0 0 4px 0', color: '#0f172a' }}>Notifications</h1>
          <p style={{ margin: 0, color: '#64748b', fontSize: '13px' }}>Price drops, targets reached, and 365-day lows</p>
        </div>

        <div style={{ display: 'flex', gap: '6px' }}>
          <button
            onClick={() => setActiveTab('inbox')}
            style={{
              padding: '7px 12px',
              borderRadius: '8px',
              border: '1px solid #cbd5e1',
              backgroundColor: activeTab === 'inbox' ? '#2563eb' : '#ffffff',
              color: activeTab === 'inbox' ? '#ffffff' : '#475569',
              fontWeight: '600',
              fontSize: '12px',
              cursor: 'pointer',
            }}
          >
            Inbox ({notifications.filter((n) => !n.read_at).length})
          </button>
          <button
            onClick={() => setActiveTab('preferences')}
            style={{
              padding: '7px 12px',
              borderRadius: '8px',
              border: '1px solid #cbd5e1',
              backgroundColor: activeTab === 'preferences' ? '#2563eb' : '#ffffff',
              color: activeTab === 'preferences' ? '#ffffff' : '#475569',
              fontWeight: '600',
              fontSize: '12px',
              cursor: 'pointer',
            }}
          >
            Preferences
          </button>
        </div>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '60px 0', color: '#64748b' }}>Loading notifications...</div>
      ) : activeTab === 'inbox' ? (
        <div>
          {notifications.length > 0 && notifications.some((n) => !n.read_at) && (
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '12px' }}>
              <button
                onClick={handleMarkAllRead}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  background: 'none',
                  border: 'none',
                  color: '#2563eb',
                  fontSize: '13px',
                  fontWeight: '600',
                  cursor: 'pointer',
                }}
              >
                <CheckCheck size={16} /> Mark all as read
              </button>
            </div>
          )}

          {notifications.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '60px 20px', backgroundColor: '#ffffff', borderRadius: '12px', border: '1px dashed #cbd5e1' }}>
              <Bell size={36} color="#94a3b8" style={{ marginBottom: '12px' }} />
              <h3 style={{ margin: '0 0 6px 0', fontSize: '18px', color: '#334155' }}>Your notification inbox is clear</h3>
              <p style={{ margin: 0, color: '#64748b', fontSize: '14px' }}>
                We will notify you immediately when your tracked items drop in price or hit your target!
              </p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {notifications.map((notif) => {
                const isTarget = notif.type === 'target_reached';
                const isNewLow = notif.type === 'new_365d_low';

                return (
                  <div
                    key={notif.id}
                    style={{
                      backgroundColor: notif.read_at ? '#ffffff' : '#f8fafc',
                      borderRadius: '10px',
                      border: `1px solid ${notif.read_at ? '#e2e8f0' : '#bfdbfe'}`,
                      padding: '16px',
                      display: 'flex',
                      gap: '14px',
                      boxShadow: notif.read_at ? 'none' : '0 1px 3px rgba(37,99,235,0.08)',
                    }}
                  >
                    <div
                      style={{
                        padding: '10px',
                        borderRadius: '50%',
                        backgroundColor: isTarget ? '#dcfce7' : isNewLow ? '#fef3c7' : '#fee2e2',
                        color: isTarget ? '#166534' : isNewLow ? '#b45309' : '#b91c1c',
                        height: 'fit-content',
                      }}
                    >
                      {isTarget ? <Target size={20} /> : isNewLow ? <TrendingDown size={20} /> : <ArrowDownRight size={20} />}
                    </div>

                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                        <h4 style={{ margin: 0, fontSize: '15px', fontWeight: '600', color: '#0f172a' }}>{notif.title}</h4>
                        <span style={{ fontSize: '12px', color: '#94a3b8' }}>
                          {new Date(notif.created_at).toLocaleDateString()}
                        </span>
                      </div>
                      <p style={{ margin: 0, fontSize: '14px', color: '#475569', lineHeight: '1.4' }}>{notif.body}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      ) : (
        /* Preferences Form */
        preferences && (
          <form
            onSubmit={handleSavePreferences}
            style={{
              backgroundColor: '#ffffff',
              borderRadius: '12px',
              border: '1px solid #e2e8f0',
              padding: '24px',
              display: 'flex',
              flexDirection: 'column',
              gap: '20px',
            }}
          >
            <h2 style={{ fontSize: '18px', fontWeight: 'bold', margin: '0 0 4px 0', color: '#0f172a' }}>Alert Channels & Rules</h2>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={preferences.in_app_enabled}
                  onChange={(e) => setPreferences({ ...preferences, in_app_enabled: e.target.checked })}
                />
                <span style={{ fontSize: '14px', color: '#334155' }}>In-App Notifications (Notification Inbox)</span>
              </label>

              <label style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={preferences.target_reached_enabled}
                  onChange={(e) => setPreferences({ ...preferences, target_reached_enabled: e.target.checked })}
                />
                <span style={{ fontSize: '14px', color: '#334155' }}>Alert when price reaches or drops below Target Price</span>
              </label>

              <label style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={preferences.new_low_enabled}
                  onChange={(e) => setPreferences({ ...preferences, new_low_enabled: e.target.checked })}
                />
                <span style={{ fontSize: '14px', color: '#334155' }}>Alert on new lowest observed price in rolling 365 days</span>
              </label>

              <label style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={preferences.price_drop_enabled}
                  onChange={(e) => setPreferences({ ...preferences, price_drop_enabled: e.target.checked })}
                />
                <span style={{ fontSize: '14px', color: '#334155' }}>Alert on general price drops</span>
              </label>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: '600', color: '#334155', marginBottom: '6px' }}>
                Minimum Drop Percentage (ignore minor drops below this %)
              </label>
              <input
                type="number"
                min="0"
                max="100"
                step="0.5"
                value={preferences.minimum_drop_percent || 0}
                onChange={(e) => setPreferences({ ...preferences, minimum_drop_percent: parseFloat(e.target.value) || 0 })}
                style={{ width: '120px', padding: '8px 12px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '14px' }}
              />
            </div>

            <button
              type="submit"
              disabled={savingPrefs}
              style={{
                backgroundColor: '#2563eb',
                color: '#ffffff',
                border: 'none',
                padding: '10px 18px',
                borderRadius: '8px',
                fontWeight: '600',
                cursor: savingPrefs ? 'not-allowed' : 'pointer',
                fontSize: '14px',
                alignSelf: 'flex-start',
              }}
            >
              {savingPrefs ? 'Saving...' : 'Save Preferences'}
            </button>
          </form>
        )
      )}
    </div>
  );
};
