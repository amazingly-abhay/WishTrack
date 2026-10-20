import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiRequest } from '../api/client';
import { ItemPreviewResponse, WishlistItem, WishlistCollection } from '../types';
import { ArrowLeft, CheckCircle2, AlertTriangle, Link as LinkIcon } from 'lucide-react';

export const AddItem: React.FC = () => {
  const navigate = useNavigate();
  const [productUrl, setProductUrl] = useState('');
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [preview, setPreview] = useState<ItemPreviewResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Form Fields
  const [wishlists, setWishlists] = useState<WishlistCollection[]>([]);
  const [selectedWishlistId, setSelectedWishlistId] = useState<string>('');
  const [title, setTitle] = useState('');
  const [price, setPrice] = useState<string>('');
  const [targetPrice, setTargetPrice] = useState<string>('');
  const [currency, setCurrency] = useState('INR');
  const [tags, setTags] = useState('');
  const [notes, setNotes] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    apiRequest<WishlistCollection[]>('/wishlists')
      .then((data) => {
        setWishlists(data);
        const def = data.find((w) => w.is_default);
        if (def) setSelectedWishlistId(def.id);
        else if (data.length > 0) setSelectedWishlistId(data[0].id);
      })
      .catch((err) => console.error('Failed to load wishlists:', err));
  }, []);

  const handlePreview = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!productUrl.trim()) return;

    setError(null);
    setIsPreviewing(true);
    try {
      const data = await apiRequest<ItemPreviewResponse>('/items/preview', {
        method: 'POST',
        body: JSON.stringify({ product_url: productUrl.trim() }),
      });
      setPreview(data);
      if (data.title) setTitle(data.title);
      if (data.currency) setCurrency(data.currency);
      if (data.price_minor) setPrice((data.price_minor / 100).toString());
    } catch (err: any) {
      setError(err.message || 'Failed to inspect product URL');
    } finally {
      setIsPreviewing(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !productUrl.trim()) return;

    setError(null);
    setIsSaving(true);
    try {
      const priceMinor = price ? Math.round(parseFloat(price) * 100) : undefined;
      const targetPriceMinor = targetPrice ? Math.round(parseFloat(targetPrice) * 100) : undefined;
      const tagList = tags.split(',').map((t) => t.trim()).filter(Boolean);

      const newItem = await apiRequest<WishlistItem>('/items', {
        method: 'POST',
        body: JSON.stringify({
          product_url: productUrl.trim(),
          title: title.trim(),
          image_url: preview?.image_url || undefined,
          price_minor: priceMinor,
          currency,
          target_price_minor: targetPriceMinor,
          wishlist_id: selectedWishlistId || undefined,
          tags: tagList,
          notes: notes.trim() || undefined,
          source: 'manual',
        }),
      });

      navigate(`/app/items/${newItem.id}`);
    } catch (err: any) {
      setError(err.message || 'Failed to add item to wishlist');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div style={{ maxWidth: '640px', margin: '0 auto' }}>
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
          marginBottom: '16px',
          padding: 0,
        }}
      >
        <ArrowLeft size={16} /> Back to Wishlist
      </button>

      <div style={{ backgroundColor: '#ffffff', padding: 'clamp(16px, 4vw, 32px)', borderRadius: '12px', border: '1px solid #e2e8f0', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
        <h1 style={{ fontSize: 'clamp(20px, 4vw, 24px)', fontWeight: 'bold', margin: '0 0 6px 0', color: '#0f172a' }}>Add Item to Wishlist</h1>
        <p style={{ margin: '0 0 20px 0', color: '#64748b', fontSize: '13px' }}>
          Paste a product URL from any website. Supported sites track automatically; unsupported sites are saved as manual wishlist items.
        </p>

        {error && (
          <div style={{ backgroundColor: '#fef2f2', border: '1px solid #fecaca', color: '#b91c1c', padding: '10px 14px', borderRadius: '8px', fontSize: '13px', marginBottom: '16px' }}>
            {error}
          </div>
        )}

        {/* Step 1: URL Input */}
        <form onSubmit={handlePreview} style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', fontSize: '13px', fontWeight: '600', color: '#334155', marginBottom: '6px' }}>Product URL</label>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            <div style={{ position: 'relative', flex: '1 1 200px', minWidth: '160px' }}>
              <LinkIcon size={16} style={{ position: 'absolute', left: '12px', top: '12px', color: '#94a3b8' }} />
              <input
                type="url"
                required
                value={productUrl}
                onChange={(e) => setProductUrl(e.target.value)}
                placeholder="https://www.example.com/product/..."
                style={{
                  width: '100%',
                  padding: '10px 12px 10px 36px',
                  borderRadius: '8px',
                  border: '1px solid #cbd5e1',
                  fontSize: '14px',
                  boxSizing: 'border-box',
                }}
              />
            </div>
            <button
              type="submit"
              disabled={isPreviewing}
              style={{
                backgroundColor: '#2563eb',
                color: '#ffffff',
                padding: '10px 18px',
                borderRadius: '8px',
                border: 'none',
                fontWeight: '600',
                cursor: isPreviewing ? 'not-allowed' : 'pointer',
                fontSize: '14px',
                whiteSpace: 'nowrap',
                flexGrow: 0,
              }}
            >
              {isPreviewing ? 'Checking...' : 'Inspect URL'}
            </button>
          </div>
        </form>

        {/* Step 2: Confirmation / Manual Form */}
        {preview && (
          <div>
            <div
              style={{
                padding: '12px 16px',
                borderRadius: '8px',
                marginBottom: '20px',
                backgroundColor: preview.is_supported ? '#f0fdf4' : '#fffbeb',
                border: `1px solid ${preview.is_supported ? '#bbf7d0' : '#fef3c7'}`,
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
              }}
            >
              {preview.is_supported ? (
                <>
                  <CheckCircle2 size={18} color="#16a34a" />
                  <span style={{ fontSize: '13px', color: '#15803d' }}>
                    <strong>{preview.retailer_host}</strong> is supported! Automated price tracking is enabled.
                  </span>
                </>
              ) : (
                <>
                  <AlertTriangle size={18} color="#d97706" />
                  <span style={{ fontSize: '13px', color: '#b45309' }}>
                    <strong>{preview.retailer_host}</strong> is not automated yet. You can still save and manually track this item.
                  </span>
                </>
              )}
            </div>

            {/* Preview Banner with Auto-Captured Thumbnail */}
            {preview.image_url && (
              <div style={{ display: 'flex', gap: '14px', alignItems: 'center', padding: '12px', backgroundColor: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0', marginBottom: '16px' }}>
                <img
                  src={preview.image_url}
                  alt="Captured Product"
                  style={{ width: '60px', height: '60px', objectFit: 'contain', borderRadius: '6px', backgroundColor: '#ffffff', border: '1px solid #cbd5e1' }}
                />
                <div>
                  <div style={{ fontSize: '11px', color: '#16a34a', fontWeight: 'bold', textTransform: 'uppercase' }}>Auto-Captured Image</div>
                  <div style={{ fontSize: '13px', color: '#475569', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '400px' }}>
                    {preview.title || 'Product'}
                  </div>
                </div>
              </div>
            )}

            <form onSubmit={handleCreate} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {wishlists.length > 0 && (
                <div>
                  <label style={{ display: 'block', fontSize: '13px', fontWeight: '600', color: '#334155', marginBottom: '6px' }}>
                    Save to Wishlist Collection
                  </label>
                  <select
                    value={selectedWishlistId}
                    onChange={(e) => setSelectedWishlistId(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '10px 12px',
                      borderRadius: '8px',
                      border: '1px solid #cbd5e1',
                      fontSize: '14px',
                      boxSizing: 'border-box',
                      backgroundColor: '#ffffff',
                    }}
                  >
                    {wishlists.map((wl) => (
                      <option key={wl.id} value={wl.id}>
                        {wl.name} {wl.is_default ? '(Default)' : ''}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: '600', color: '#334155', marginBottom: '6px' }}>Product Title *</label>
                <input
                  type="text"
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Sony WH-1000XM5 Headphones"
                  style={{ width: '100%', padding: '10px 12px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '14px', boxSizing: 'border-box' }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 140px), 1fr))', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '13px', fontWeight: '600', color: '#334155', marginBottom: '6px' }}>Current Price ({currency})</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={price}
                    onChange={(e) => setPrice(e.target.value)}
                    placeholder="e.g. 24999.00"
                    style={{ width: '100%', padding: '10px 12px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '14px', boxSizing: 'border-box' }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '13px', fontWeight: '600', color: '#334155', marginBottom: '6px' }}>Target Price ({currency})</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={targetPrice}
                    onChange={(e) => setTargetPrice(e.target.value)}
                    placeholder="Alert when price drops to..."
                    style={{ width: '100%', padding: '10px 12px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '14px', boxSizing: 'border-box' }}
                  />
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: '600', color: '#334155', marginBottom: '6px' }}>Collection / Category</label>
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '8px' }}>
                  {['Audio', 'TV & Appliances', 'Fashion', 'Tech & Gadgets', 'Home & Kitchen', 'Gaming', 'Books'].map((cat) => (
                    <button
                      type="button"
                      key={cat}
                      onClick={() => {
                        const existing = tags.split(',').map((t) => t.trim()).filter(Boolean);
                        if (!existing.includes(cat)) {
                          setTags(existing.length > 0 ? `${existing.join(', ')}, ${cat}` : cat);
                        }
                      }}
                      style={{
                        padding: '5px 10px',
                        borderRadius: '16px',
                        fontSize: '12px',
                        border: '1px solid #cbd5e1',
                        backgroundColor: tags.toLowerCase().includes(cat.toLowerCase()) ? '#eff6ff' : '#ffffff',
                        borderColor: tags.toLowerCase().includes(cat.toLowerCase()) ? '#93c5fd' : '#cbd5e1',
                        color: tags.toLowerCase().includes(cat.toLowerCase()) ? '#1d4ed8' : '#475569',
                        cursor: 'pointer',
                        fontWeight: tags.toLowerCase().includes(cat.toLowerCase()) ? '600' : 'normal',
                      }}
                    >
                      + {cat}
                    </button>
                  ))}
                </div>
                <input
                  type="text"
                  value={tags}
                  onChange={(e) => setTags(e.target.value)}
                  placeholder="e.g. Audio, Tech, Wishlist"
                  style={{ width: '100%', padding: '10px 12px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '14px', boxSizing: 'border-box' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: '600', color: '#334155', marginBottom: '6px' }}>Notes</label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={2}
                  placeholder="Wait for Diwali discount or cashback offer..."
                  style={{ width: '100%', padding: '10px 12px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '14px', boxSizing: 'border-box' }}
                />
              </div>

              <button
                type="submit"
                disabled={isSaving}
                style={{
                  backgroundColor: '#2563eb',
                  color: '#ffffff',
                  padding: '12px',
                  borderRadius: '8px',
                  fontWeight: '600',
                  border: 'none',
                  cursor: isSaving ? 'not-allowed' : 'pointer',
                  fontSize: '15px',
                  marginTop: '8px',
                }}
              >
                {isSaving ? 'Adding Item...' : 'Confirm & Add to Wishlist'}
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  );
};
