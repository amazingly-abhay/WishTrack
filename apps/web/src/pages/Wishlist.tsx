import React, { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { WishlistItem, WishlistCollection } from '../types';
import { apiRequest } from '../api/client';
import {
  ExternalLink,
  PlusCircle,
  Search,
  TrendingDown,
  Layers,
  ArrowUpDown,
  Trash2,
  FolderPlus,
  Folder,
  Tag,
  MoveRight
} from 'lucide-react';

export const Wishlist: React.FC = () => {
  const [wishlists, setWishlists] = useState<WishlistCollection[]>([]);
  const [activeWishlistId, setActiveWishlistId] = useState<string>('all');
  const [items, setItems] = useState<WishlistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [filterMode, setFilterMode] = useState<string>('all'); // all, dropped, target_hit
  const [selectedProductType, setSelectedProductType] = useState<string>('all');
  const [sortBy, setSortBy] = useState<string>('newest'); // newest, product_type, price_asc, price_desc, drop_pct

  // Modal State for New List
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newListName, setNewListName] = useState('');
  const [newListDesc, setNewListDesc] = useState('');
  const [isCreatingList, setIsCreatingList] = useState(false);

  // Modal State for Moving Item between Lists
  const [movingItem, setMovingItem] = useState<WishlistItem | null>(null);
  const [targetMoveWishlistId, setTargetMoveWishlistId] = useState<string>('');

  // Fetch wishlists collections
  const fetchWishlists = async () => {
    try {
      const data = await apiRequest<WishlistCollection[]>('/wishlists');
      setWishlists(data);
    } catch (err: any) {
      console.error('Failed to load wishlists', err);
    }
  };

  // Fetch items based on active wishlist and search query
  const fetchItems = async () => {
    setLoading(true);
    setError(null);
    try {
      let query = `/items?limit=100`;
      if (activeWishlistId !== 'all') {
        query += `&wishlist_id=${activeWishlistId}`;
      }
      if (search.trim()) {
        query += `&q=${encodeURIComponent(search.trim())}`;
      }
      const data = await apiRequest<{ items: WishlistItem[]; total: number }>(query);
      setItems(data.items);
    } catch (err: any) {
      setError(err.message || 'Failed to load items');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWishlists();
  }, []);

  useEffect(() => {
    fetchItems();
  }, [activeWishlistId, search]);

  // Create New Custom Wishlist
  const handleCreateWishlist = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newListName.trim()) return;
    setIsCreatingList(true);
    try {
      const created = await apiRequest<WishlistCollection>('/wishlists', {
        method: 'POST',
        body: JSON.stringify({
          name: newListName.trim(),
          description: newListDesc.trim() || undefined,
        }),
      });
      setWishlists((prev) => [...prev, created]);
      setActiveWishlistId(created.id);
      setNewListName('');
      setNewListDesc('');
      setShowCreateModal(false);
    } catch (err: any) {
      alert(err.message || 'Failed to create wishlist');
    } finally {
      setIsCreatingList(false);
    }
  };

  // Delete Custom Wishlist
  const handleDeleteWishlist = async (wl: WishlistCollection) => {
    if (wl.is_default) {
      alert('The default wishlist cannot be deleted.');
      return;
    }
    const confirmDelete = window.confirm(
      `Are you sure you want to delete the list "${wl.name}"?\nItems in this list will be safely moved to your Default wishlist.`
    );
    if (!confirmDelete) return;

    try {
      await apiRequest(`/wishlists/${wl.id}?delete_items=false`, { method: 'DELETE' });
      setActiveWishlistId('all');
      await fetchWishlists();
      await fetchItems();
    } catch (err: any) {
      alert(err.message || 'Failed to delete wishlist');
    }
  };

  // Delete Individual Item
  const handleDeleteItem = async (item: WishlistItem) => {
    const confirmDelete = window.confirm(`Remove "${item.title}" from your wishlist?`);
    if (!confirmDelete) return;

    try {
      await apiRequest(`/items/${item.id}?archive=false`, { method: 'DELETE' });
      setItems((prev) => prev.filter((i) => i.id !== item.id));
      await fetchWishlists();
    } catch (err: any) {
      alert(err.message || 'Failed to delete item');
    }
  };

  // Move Item to Another Wishlist
  const handleMoveItem = async () => {
    if (!movingItem || !targetMoveWishlistId) return;
    try {
      await apiRequest(`/items/${movingItem.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ wishlist_id: targetMoveWishlistId }),
      });
      setMovingItem(null);
      await fetchWishlists();
      await fetchItems();
    } catch (err: any) {
      alert(err.message || 'Failed to move item');
    }
  };

  // Extract all available product types from current items' tags
  const availableProductTypes = useMemo(() => {
    const set = new Set<string>();
    items.forEach((item) => {
      (item.tags || []).forEach((t) => {
        if (t && t.trim()) set.add(t.trim());
      });
    });
    return Array.from(set);
  }, [items]);

  // Combined filtering & sorting pipeline
  const processedItems = useMemo(() => {
    let result = items.filter((item) => {
      // Filter Mode
      if (filterMode === 'target_hit') {
        const hit =
          item.target_price_minor &&
          item.current_price_minor &&
          item.current_price_minor <= item.target_price_minor;
        if (!hit) return false;
      } else if (filterMode === 'dropped') {
        const dropped =
          item.previous_price_minor &&
          item.current_price_minor &&
          item.current_price_minor < item.previous_price_minor;
        if (!dropped) return false;
      }

      // Product Type / Department Filter
      if (selectedProductType !== 'all') {
        const itemTags = (item.tags || []).map((t) => t.toLowerCase());
        if (!itemTags.includes(selectedProductType.toLowerCase())) {
          return false;
        }
      }

      return true;
    });

    // Sorting Engine
    return [...result].sort((a, b) => {
      if (sortBy === 'product_type') {
        const typeA = (a.tags && a.tags[0]) || '';
        const typeB = (b.tags && b.tags[0]) || '';
        return typeA.localeCompare(typeB);
      }
      if (sortBy === 'price_asc') {
        return (a.current_price_minor || 0) - (b.current_price_minor || 0);
      }
      if (sortBy === 'price_desc') {
        return (b.current_price_minor || 0) - (a.current_price_minor || 0);
      }
      if (sortBy === 'drop_pct') {
        const dropPctA =
          a.previous_price_minor && a.current_price_minor && a.previous_price_minor > a.current_price_minor
            ? (a.previous_price_minor - a.current_price_minor) / a.previous_price_minor
            : 0;
        const dropPctB =
          b.previous_price_minor && b.current_price_minor && b.previous_price_minor > b.current_price_minor
            ? (b.previous_price_minor - b.current_price_minor) / b.previous_price_minor
            : 0;
        return dropPctB - dropPctA;
      }
      // default: newest
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    });
  }, [items, filterMode, selectedProductType, sortBy]);

  const formatPrice = (minor?: number, currency = 'INR') => {
    if (minor === undefined || minor === null) return 'No price';
    const amount = minor / 100;
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: currency || 'INR',
      maximumFractionDigits: 2,
    }).format(amount);
  };

  const currentWishlistObj = wishlists.find((w) => w.id === activeWishlistId);

  return (
    <div>
      {/* Header & Controls */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h1 style={{ fontSize: 'clamp(20px, 4vw, 28px)', fontWeight: 'bold', margin: '0 0 4px 0', color: '#0f172a' }}>
            {activeWishlistId === 'all'
              ? 'All Wishlist Items'
              : currentWishlistObj?.name || 'Wishlist'}
          </h1>
          <p style={{ margin: 0, color: '#64748b', fontSize: '13px' }}>
            {activeWishlistId === 'all'
              ? `Tracking ${items.length} items across all collections`
              : `${currentWishlistObj?.description || 'Separate wishlist collection'} • ${items.length} items`}
          </p>
        </div>

        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <button
            onClick={() => setShowCreateModal(true)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: '#f1f5f9',
              color: '#334155',
              padding: '9px 14px',
              borderRadius: '8px',
              border: '1px solid #cbd5e1',
              fontWeight: '600',
              fontSize: '13px',
              cursor: 'pointer',
            }}
          >
            <FolderPlus size={16} />
            New List
          </button>

          <Link
            to="/app/items/new"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              backgroundColor: '#2563eb',
              color: '#ffffff',
              padding: '9px 16px',
              borderRadius: '8px',
              textDecoration: 'none',
              fontWeight: '600',
              fontSize: '13px',
              boxShadow: '0 2px 4px rgba(37, 99, 235, 0.2)',
            }}
          >
            <PlusCircle size={17} />
            Add Item
          </Link>
        </div>
      </div>

      {/* Flipkart-style Wishlist Collections Tabs */}
      <div style={{ marginBottom: '18px', display: 'flex', alignItems: 'center', gap: '8px', overflowX: 'auto', paddingBottom: '6px' }}>
        <button
          onClick={() => setActiveWishlistId('all')}
          style={{
            padding: '7px 15px',
            borderRadius: '8px',
            border: '1px solid',
            borderColor: activeWishlistId === 'all' ? '#2563eb' : '#cbd5e1',
            backgroundColor: activeWishlistId === 'all' ? '#2563eb' : '#ffffff',
            color: activeWishlistId === 'all' ? '#ffffff' : '#475569',
            fontSize: '13px',
            fontWeight: '600',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            whiteSpace: 'nowrap',
          }}
        >
          <Layers size={14} />
          All Items ({wishlists.reduce((acc, curr) => acc + (curr.item_count || 0), 0)})
        </button>

        {wishlists.map((wl) => (
          <div key={wl.id} style={{ display: 'inline-flex', alignItems: 'center', gap: '2px' }}>
            <button
              onClick={() => setActiveWishlistId(wl.id)}
              style={{
                padding: '7px 14px',
                borderRadius: wl.is_default ? '8px' : '8px 0 0 8px',
                border: '1px solid',
                borderColor: activeWishlistId === wl.id ? '#2563eb' : '#cbd5e1',
                backgroundColor: activeWishlistId === wl.id ? '#eff6ff' : '#ffffff',
                color: activeWishlistId === wl.id ? '#1d4ed8' : '#334155',
                fontSize: '13px',
                fontWeight: activeWishlistId === wl.id ? '600' : '500',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                whiteSpace: 'nowrap',
              }}
            >
              <Folder size={14} color={activeWishlistId === wl.id ? '#2563eb' : '#64748b'} />
              {wl.name} ({wl.item_count})
            </button>

            {!wl.is_default && (
              <button
                onClick={() => handleDeleteWishlist(wl)}
                title={`Delete list "${wl.name}"`}
                style={{
                  padding: '7px 8px',
                  borderRadius: '0 8px 8px 0',
                  border: '1px solid',
                  borderLeft: 'none',
                  borderColor: activeWishlistId === wl.id ? '#2563eb' : '#cbd5e1',
                  backgroundColor: activeWishlistId === wl.id ? '#eff6ff' : '#ffffff',
                  color: '#94a3b8',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                }}
                onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.color = '#ef4444')}
                onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.color = '#94a3b8')}
              >
                <Trash2 size={13} />
              </button>
            )}
          </div>
        ))}
      </div>

      {/* Product Type / Categories Sub-bar */}
      <div style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px', overflowX: 'auto', paddingBottom: '4px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '5px', color: '#64748b', fontSize: '12px', fontWeight: '600', marginRight: '4px' }}>
          <Tag size={14} /> Product Type:
        </div>
        {['all', 'Audio', 'TV & Appliances', 'Fashion', 'Tech & Gadgets', 'Home & Kitchen', ...availableProductTypes.filter((c) => !['Audio', 'TV & Appliances', 'Fashion', 'Tech & Gadgets', 'Home & Kitchen'].includes(c))].map((type) => (
          <button
            key={type}
            onClick={() => setSelectedProductType(type)}
            style={{
              padding: '4px 12px',
              borderRadius: '16px',
              border: '1px solid',
              borderColor: selectedProductType.toLowerCase() === type.toLowerCase() ? '#3b82f6' : '#e2e8f0',
              backgroundColor: selectedProductType.toLowerCase() === type.toLowerCase() ? '#eff6ff' : '#ffffff',
              color: selectedProductType.toLowerCase() === type.toLowerCase() ? '#1d4ed8' : '#64748b',
              fontSize: '12px',
              fontWeight: selectedProductType.toLowerCase() === type.toLowerCase() ? '600' : 'normal',
              cursor: 'pointer',
              whiteSpace: 'nowrap',
            }}
          >
            {type === 'all' ? 'All Types' : type}
          </button>
        ))}
      </div>

      {/* Search, Filter & Sort Bar */}
      <div style={{ display: 'flex', gap: '10px', marginBottom: '20px', flexWrap: 'wrap', alignItems: 'center' }}>
        <div style={{ position: 'relative', flex: '1 1 200px', minWidth: '160px', width: '100%' }}>
          <Search size={16} style={{ position: 'absolute', left: '10px', top: '10px', color: '#94a3b8' }} />
          <input
            type="text"
            placeholder="Search items by title or retailer..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{
              width: '100%',
              padding: '8px 10px 8px 34px',
              borderRadius: '8px',
              border: '1px solid #cbd5e1',
              fontSize: '13px',
              boxSizing: 'border-box',
              backgroundColor: '#ffffff',
            }}
          />
        </div>

        {/* Filter Badges & Sort Container */}
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center', width: '100%', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', gap: '6px', overflowX: 'auto', paddingBottom: '2px', WebkitOverflowScrolling: 'touch' }}>
            {(['all', 'target_hit', 'dropped'] as const).map((mode) => (
              <button
                key={mode}
                onClick={() => setFilterMode(mode)}
                style={{
                  padding: '6px 10px',
                  borderRadius: '6px',
                  border: '1px solid #cbd5e1',
                  backgroundColor: filterMode === mode ? '#2563eb' : '#ffffff',
                  color: filterMode === mode ? '#ffffff' : '#475569',
                  fontSize: '11px',
                  fontWeight: '600',
                  cursor: 'pointer',
                  whiteSpace: 'nowrap',
                  flexShrink: 0,
                }}
              >
                {mode === 'all' && 'All Status'}
                {mode === 'target_hit' && 'Target Hit'}
                {mode === 'dropped' && 'Price Drops'}
              </button>
            ))}
          </div>

          {/* Sort Select */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', backgroundColor: '#ffffff', padding: '4px 8px', borderRadius: '6px', border: '1px solid #cbd5e1', flexShrink: 0 }}>
            <ArrowUpDown size={13} color="#64748b" />
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              style={{
                border: 'none',
                background: 'transparent',
                fontSize: '11px',
                color: '#334155',
                fontWeight: '500',
                outline: 'none',
                cursor: 'pointer',
                padding: '2px 0',
              }}
            >
              <option value="newest">Recently Added</option>
              <option value="product_type">Product Type (A-Z)</option>
              <option value="drop_pct">Biggest Drop (%)</option>
              <option value="price_asc">Price: Low-High</option>
              <option value="price_desc">Price: High-Low</option>
            </select>
          </div>
        </div>
      </div>

      {/* Items Grid */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '60px 0', color: '#64748b' }}>Loading wishlist items...</div>
      ) : error ? (
        <div style={{ backgroundColor: '#fef2f2', border: '1px solid #fecaca', color: '#b91c1c', padding: '16px', borderRadius: '8px' }}>
          {error}
        </div>
      ) : processedItems.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '60px 20px', backgroundColor: '#ffffff', borderRadius: '12px', border: '1px dashed #cbd5e1' }}>
          <h3 style={{ margin: '0 0 8px 0', fontSize: '18px', color: '#334155' }}>No items in this list</h3>
          <p style={{ margin: '0 0 16px 0', color: '#64748b', fontSize: '14px' }}>
            {items.length === 0
              ? 'This wishlist list is currently empty. Add products to keep them organized!'
              : 'No products match your selected filters or product type.'}
          </p>
          <Link
            to="/app/items/new"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              backgroundColor: '#2563eb',
              color: '#ffffff',
              padding: '10px 16px',
              borderRadius: '8px',
              textDecoration: 'none',
              fontWeight: '600',
              fontSize: '14px',
            }}
          >
            <PlusCircle size={18} />
            Add Product to List
          </Link>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 280px), 1fr))', gap: '16px' }}>
          {processedItems.map((item) => {
            const hasDrop = item.previous_price_minor && item.current_price_minor && item.current_price_minor < item.previous_price_minor;
            const targetHit = item.target_price_minor && item.current_price_minor && item.current_price_minor <= item.target_price_minor;
            const dropPercent = hasDrop && item.previous_price_minor && item.current_price_minor
              ? Math.round(((item.previous_price_minor - item.current_price_minor) / item.previous_price_minor) * 100)
              : null;

            return (
              <div
                key={item.id}
                style={{
                  backgroundColor: '#ffffff',
                  borderRadius: '12px',
                  border: '1px solid #e2e8f0',
                  overflow: 'hidden',
                  display: 'flex',
                  flexDirection: 'column',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
                  transition: 'transform 0.15s ease, box-shadow 0.15s ease',
                }}
              >
                {/* Top Cover Image Banner */}
                <Link
                  to={`/app/items/${item.id}`}
                  style={{
                    display: 'block',
                    width: '100%',
                    height: '180px',
                    backgroundColor: '#ffffff',
                    borderBottom: '1px solid #f1f5f9',
                    position: 'relative',
                    overflow: 'hidden',
                  }}
                >
                  {item.image_url ? (
                    <img
                      src={item.image_url}
                      alt={item.title}
                      style={{
                        width: '100%',
                        height: '100%',
                        objectFit: 'contain',
                        padding: '12px',
                        boxSizing: 'border-box',
                        transition: 'transform 0.2s ease',
                      }}
                      onError={(e) => {
                        (e.target as HTMLElement).style.display = 'none';
                      }}
                    />
                  ) : (
                    <div
                      style={{
                        width: '100%',
                        height: '100%',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: '#94a3b8',
                        fontSize: '13px',
                        fontWeight: '500',
                        backgroundColor: '#f8fafc',
                      }}
                    >
                      No Image Available
                    </div>
                  )}

                  {/* Badges Over Cover Image */}
                  <div style={{ position: 'absolute', top: '10px', left: '10px', display: 'flex', gap: '6px', zIndex: 2 }}>
                    <span style={{ fontSize: '11px', fontWeight: 'bold', backgroundColor: 'rgba(255,255,255,0.92)', color: '#475569', padding: '3px 8px', borderRadius: '6px', border: '1px solid #e2e8f0', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                      {item.retailer_host}
                    </span>
                    {item.tags && item.tags.length > 0 && (
                      <span style={{ fontSize: '11px', fontWeight: '600', backgroundColor: '#eff6ff', color: '#2563eb', padding: '3px 8px', borderRadius: '6px', border: '1px solid #bfdbfe' }}>
                        {item.tags[0]}
                      </span>
                    )}
                  </div>

                  <div style={{ position: 'absolute', top: '10px', right: '10px', display: 'flex', gap: '6px', alignItems: 'center', zIndex: 2 }}>
                    {targetHit && (
                      <span style={{ fontSize: '11px', fontWeight: 'bold', backgroundColor: '#dcfce7', color: '#15803d', padding: '4px 8px', borderRadius: '6px', border: '1px solid #bbf7d0' }}>
                        Target Hit
                      </span>
                    )}
                    {hasDrop && (
                      <span
                        style={{
                          fontSize: '11px',
                          fontWeight: '800',
                          backgroundColor: '#ef4444',
                          color: '#ffffff',
                          padding: '4px 8px',
                          borderRadius: '6px',
                          boxShadow: '0 2px 4px rgba(239,68,68,0.3)',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '3px',
                          letterSpacing: '0.3px',
                        }}
                      >
                        <TrendingDown size={14} />
                        {dropPercent ? `${dropPercent}% OFF` : 'DROP'}
                      </span>
                    )}
                  </div>
                </Link>

                {/* Details Section Below Cover Image */}
                <div style={{ padding: '16px', flex: 1, display: 'flex', flexDirection: 'column' }}>
                  <Link
                    to={`/app/items/${item.id}`}
                    style={{
                      fontSize: '15px',
                      fontWeight: '600',
                      color: '#0f172a',
                      textDecoration: 'none',
                      marginBottom: '12px',
                      lineHeight: '1.4',
                      overflow: 'hidden',
                      display: '-webkit-box',
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: 'vertical',
                    }}
                    title={item.title}
                  >
                    {item.title}
                  </Link>

                  {/* Price Block */}
                  <div style={{ marginTop: 'auto', paddingTop: '10px', borderTop: '1px solid #f1f5f9' }}>
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
                      <span style={{ fontSize: '20px', fontWeight: 'bold', color: '#0f172a' }}>
                        {formatPrice(item.current_price_minor, item.currency)}
                      </span>
                      {item.previous_price_minor && item.previous_price_minor !== item.current_price_minor && (
                        <span style={{ fontSize: '13px', color: '#94a3b8', textDecoration: 'line-through' }}>
                          {formatPrice(item.previous_price_minor, item.currency)}
                        </span>
                      )}
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '6px', fontSize: '12px' }}>
                      {item.target_price_minor ? (
                        <span style={{ color: '#2563eb', fontWeight: '500' }}>
                          Target: {formatPrice(item.target_price_minor, item.currency)}
                        </span>
                      ) : (
                        <span style={{ color: '#94a3b8' }}>Target: Not set</span>
                      )}

                      <span style={{ color: '#64748b', fontSize: '11px' }}>
                        Low: {formatPrice(item.lowest_365d_price_minor, item.currency)}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Footer Action Bar with Delete & Move options */}
                <div style={{ padding: '10px 16px', backgroundColor: '#f8fafc', borderTop: '1px solid #f1f5f9', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                    <Link
                      to={`/app/items/${item.id}`}
                      style={{ fontSize: '13px', fontWeight: '600', color: '#2563eb', textDecoration: 'none' }}
                    >
                      History &rarr;
                    </Link>

                    {wishlists.length > 1 && (
                      <button
                        onClick={() => {
                          setMovingItem(item);
                          setTargetMoveWishlistId(item.wishlist_id || (wishlists.find((w) => w.is_default)?.id || ''));
                        }}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: '#64748b',
                          fontSize: '12px',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '3px',
                          padding: 0,
                        }}
                        title="Move to another wishlist"
                      >
                        <MoveRight size={13} /> Move
                      </button>
                    )}
                  </div>

                  <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                    <a
                      href={item.product_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ color: '#94a3b8', display: 'flex', alignItems: 'center' }}
                      title="Open on retailer store"
                    >
                      <ExternalLink size={15} />
                    </a>

                    <button
                      onClick={() => handleDeleteItem(item)}
                      style={{
                        background: 'none',
                        border: 'none',
                        color: '#94a3b8',
                        cursor: 'pointer',
                        padding: 0,
                        display: 'flex',
                        alignItems: 'center',
                      }}
                      onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.color = '#ef4444')}
                      onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.color = '#94a3b8')}
                      title="Delete item from wishlist"
                    >
                      <Trash2 size={15} />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Modal: Create New Wishlist */}
      {showCreateModal && (
        <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(15, 23, 42, 0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: '16px' }}>
          <div style={{ backgroundColor: '#ffffff', borderRadius: '12px', width: '100%', maxWidth: '420px', padding: '24px', boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1)' }}>
            <h2 style={{ fontSize: '18px', fontWeight: 'bold', margin: '0 0 8px 0', color: '#0f172a' }}>Create New Wishlist</h2>
            <p style={{ margin: '0 0 16px 0', fontSize: '13px', color: '#64748b' }}>
              Create a separate list to organize your tracked items (like Flipkart wishlists).
            </p>

            <form onSubmit={handleCreateWishlist}>
              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: '600', color: '#334155', marginBottom: '6px' }}>List Name *</label>
                <input
                  type="text"
                  required
                  value={newListName}
                  onChange={(e) => setNewListName(e.target.value)}
                  placeholder="e.g. Living Room Gadgets, Diwali Shopping"
                  style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '14px', boxSizing: 'border-box' }}
                />
              </div>

              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: '600', color: '#334155', marginBottom: '6px' }}>Description (optional)</label>
                <textarea
                  value={newListDesc}
                  onChange={(e) => setNewListDesc(e.target.value)}
                  rows={2}
                  placeholder="Items to buy during upcoming festive discount..."
                  style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '14px', boxSizing: 'border-box' }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  style={{ padding: '8px 14px', borderRadius: '6px', border: '1px solid #cbd5e1', backgroundColor: '#ffffff', color: '#475569', fontSize: '13px', fontWeight: '600', cursor: 'pointer' }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isCreatingList}
                  style={{ padding: '8px 16px', borderRadius: '6px', border: 'none', backgroundColor: '#2563eb', color: '#ffffff', fontSize: '13px', fontWeight: '600', cursor: isCreatingList ? 'not-allowed' : 'pointer' }}
                >
                  {isCreatingList ? 'Creating...' : 'Create List'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Move Item to Another Wishlist */}
      {movingItem && (
        <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(15, 23, 42, 0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: '16px' }}>
          <div style={{ backgroundColor: '#ffffff', borderRadius: '12px', width: '100%', maxWidth: '400px', padding: '24px', boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1)' }}>
            <h2 style={{ fontSize: '18px', fontWeight: 'bold', margin: '0 0 8px 0', color: '#0f172a' }}>Move Item to List</h2>
            <p style={{ margin: '0 0 16px 0', fontSize: '13px', color: '#64748b' }}>
              Select which wishlist collection you want to move <strong>{movingItem.title}</strong> into:
            </p>

            <div style={{ marginBottom: '20px' }}>
              <select
                value={targetMoveWishlistId}
                onChange={(e) => setTargetMoveWishlistId(e.target.value)}
                style={{ width: '100%', padding: '10px 12px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '14px', boxSizing: 'border-box' }}
              >
                {wishlists.map((wl) => (
                  <option key={wl.id} value={wl.id}>
                    {wl.name} {wl.is_default ? '(Default)' : ''} ({wl.item_count} items)
                  </option>
                ))}
              </select>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                type="button"
                onClick={() => setMovingItem(null)}
                style={{ padding: '8px 14px', borderRadius: '6px', border: '1px solid #cbd5e1', backgroundColor: '#ffffff', color: '#475569', fontSize: '13px', fontWeight: '600', cursor: 'pointer' }}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleMoveItem}
                style={{ padding: '8px 16px', borderRadius: '6px', border: 'none', backgroundColor: '#2563eb', color: '#ffffff', fontSize: '13px', fontWeight: '600', cursor: 'pointer' }}
              >
                Confirm Move
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
