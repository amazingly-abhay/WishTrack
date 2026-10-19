const API_BASE = '/api/v1';

export class ApiError extends Error {
  code: string;
  status: number;

  constructor(code: string, message: string, status: number) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

export function getAuthToken(): string | null {
  return localStorage.getItem('wishtrack_access_token');
}

export function setAuthTokens(access: string, refresh: string) {
  localStorage.setItem('wishtrack_access_token', access);
  localStorage.setItem('wishtrack_refresh_token', refresh);
}

export function clearAuthTokens() {
  localStorage.removeItem('wishtrack_access_token');
  localStorage.removeItem('wishtrack_refresh_token');
}

export async function apiRequest<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = getAuthToken();
  const headers = new Headers(options.headers || {});
  
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  if (!headers.has('Content-Type') && options.body && typeof options.body === 'string') {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorData = { error: { code: 'UNKNOWN_ERROR', message: 'An unexpected error occurred' } };
    try {
      errorData = await response.json();
    } catch {
      // Non-json response
    }
    throw new ApiError(
      errorData.error?.code || 'API_ERROR',
      errorData.error?.message || response.statusText,
      response.status
    );
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}
