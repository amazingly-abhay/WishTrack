export interface User {
  id: string;
  email: string;
  display_name?: string;
  is_active: boolean;
  created_at: string;
}

export interface WishlistCollection {
  id: string;
  name: string;
  description?: string;
  is_default: boolean;
  item_count: number;
  created_at: string;
  updated_at: string;
}

export interface WishlistItem {
  id: string;
  wishlist_id?: string;
  title: string;
  product_url: string;
  canonical_url: string;
  retailer_host: string;
  image_url?: string;
  currency?: string;
  current_price_minor?: number;
  previous_price_minor?: number;
  lowest_365d_price_minor?: number;
  lowest_365d_at?: string;
  target_price_minor?: number;
  tracking_mode: 'automatic' | 'manual' | 'unsupported' | 'paused';
  tracking_status: 'active' | 'degraded' | 'failed' | 'paused';
  is_favorite: boolean;
  is_archived: boolean;
  tags: string[];
  notes?: string;
  last_checked_at?: string;
  next_check_at?: string;
  created_at: string;
  updated_at: string;
}

export interface PriceObservation {
  id: number;
  item_id: string;
  observed_at: string;
  price_minor: number;
  currency: string;
  availability: string;
  source: string;
  raw_price_text?: string;
  created_at: string;
}

export interface HistorySummary {
  item_id: string;
  currency: string;
  current_price_minor?: number;
  previous_price_minor?: number;
  change_amount?: number;
  change_percent?: number;
  lowest_365d_price_minor?: number;
  lowest_365d_at?: string;
  target_price_minor?: number;
  target_reached: boolean;
  observation_count: number;
}

export interface ItemPreviewResponse {
  product_url: string;
  canonical_url: string;
  retailer_host: string;
  is_supported: boolean;
  title?: string;
  image_url?: string;
  price_minor?: number;
  currency?: string;
  availability?: string;
}
