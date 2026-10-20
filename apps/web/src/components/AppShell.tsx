import React, { useState, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { apiRequest } from '../api/client';
import { Heart, PlusCircle, LogOut, Bell } from 'lucide-react';

export const AppShell: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [unreadCount, setUnreadCount] = useState<number>(0);

  useEffect(() => {
    const fetchUnread = async () => {
      try {
        const data = await apiRequest<{ total: number }>('/notifications?unread_only=true');
        setUnreadCount(data.total);
      } catch {
        // silent fallback
      }
    };
    if (user) {
      fetchUnread();
    }
  }, [user, location.pathname]);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const navItems = [
    { label: 'Wishlist', path: '/app/wishlist', icon: Heart },
    { label: 'Add Item', path: '/app/items/new', icon: PlusCircle },
    { label: 'Notifications', path: '/app/notifications', icon: Bell, badge: unreadCount },
  ];

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', backgroundColor: '#f8fafc', color: '#0f172a', fontFamily: 'system-ui, -apple-system, sans-serif' }}>
      {/* Top Header */}
      <header
        style={{
          backgroundColor: '#ffffff',
          borderBottom: '1px solid #e2e8f0',
          padding: '12px 16px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          position: 'sticky',
          top: 0,
          zIndex: 100,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '18px', fontWeight: 'bold', color: '#2563eb' }}>WishTrack</span>
          <span style={{ fontSize: '11px', backgroundColor: '#dbeafe', color: '#1e40af', padding: '1px 6px', borderRadius: '10px', fontWeight: '600' }}>
            PWA
          </span>
        </div>

        {/* Desktop Nav */}
        <nav className="desktop-nav" style={{ gap: '16px', alignItems: 'center' }}>
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  textDecoration: 'none',
                  color: active ? '#2563eb' : '#475569',
                  fontWeight: active ? '600' : '400',
                  padding: '6px 12px',
                  borderRadius: '6px',
                  backgroundColor: active ? '#eff6ff' : 'transparent',
                  position: 'relative',
                  fontSize: '14px',
                }}
              >
                <Icon size={18} />
                <span>{item.label}</span>
                {item.badge !== undefined && item.badge > 0 && (
                  <span
                    style={{
                      backgroundColor: '#ef4444',
                      color: '#ffffff',
                      fontSize: '11px',
                      fontWeight: 'bold',
                      padding: '1px 6px',
                      borderRadius: '10px',
                    }}
                  >
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* User / Logout */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {user && (
            <span
              className="mobile-hide"
              style={{
                fontSize: '13px',
                color: '#64748b',
                maxWidth: '160px',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {user.display_name || user.email}
            </span>
          )}
          <button
            onClick={handleLogout}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              padding: '6px 10px',
              borderRadius: '6px',
              border: '1px solid #cbd5e1',
              backgroundColor: '#ffffff',
              cursor: 'pointer',
              fontSize: '13px',
              color: '#475569',
            }}
            title="Log out"
          >
            <LogOut size={15} />
            <span className="mobile-hide">Logout</span>
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="main-container" style={{ flex: 1, maxWidth: '1200px', margin: '0 auto', width: '100%' }}>
        {children}
      </main>

      {/* Fixed Mobile Bottom Navigation Bar */}
      <nav
        className="mobile-bottom-nav"
        style={{
          position: 'fixed',
          bottom: 0,
          left: 0,
          right: 0,
          backgroundColor: '#ffffff',
          borderTop: '1px solid #e2e8f0',
          justifyContent: 'space-around',
          alignItems: 'center',
          padding: '8px 0 calc(8px + env(safe-area-inset-bottom, 0px)) 0',
          zIndex: 999,
          boxShadow: '0 -2px 10px rgba(0,0,0,0.06)',
        }}
      >
        {navItems.map((item) => {
          const Icon = item.icon;
          const active = location.pathname === item.path;
          return (
            <Link
              key={item.path}
              to={item.path}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '3px',
                textDecoration: 'none',
                color: active ? '#2563eb' : '#64748b',
                fontSize: '11px',
                fontWeight: active ? '700' : '500',
                position: 'relative',
                padding: '4px 12px',
              }}
            >
              <div style={{ position: 'relative' }}>
                <Icon size={20} strokeWidth={active ? 2.5 : 2} />
                {item.badge !== undefined && item.badge > 0 && (
                  <span
                    style={{
                      position: 'absolute',
                      top: '-4px',
                      right: '-8px',
                      backgroundColor: '#ef4444',
                      color: '#ffffff',
                      fontSize: '10px',
                      fontWeight: 'bold',
                      padding: '1px 5px',
                      borderRadius: '8px',
                      lineHeight: '1',
                    }}
                  >
                    {item.badge}
                  </span>
                )}
              </div>
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Desktop Footer */}
      <footer
        className="mobile-hide"
        style={{
          borderTop: '1px solid #e2e8f0',
          padding: '16px 24px',
          textAlign: 'center',
          fontSize: '13px',
          color: '#94a3b8',
          backgroundColor: '#ffffff',
        }}
      >
        WishTrack &copy; {new Date().getFullYear()} &bull; 365-Day Price Tracking &bull; Non-intrusive & Secure
      </footer>
    </div>
  );
};
