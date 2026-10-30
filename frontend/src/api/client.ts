/**
 * Centralized API client for CampusVoice.
 * - Uses relative /api URLs.
 * - Includes credentials ('include') for Flask-Login session cookies and CSRF bootstrap.
 * - Automatically fetches, validates, and attaches X-CSRFToken for mutating requests.
 * - Keeps CSRF token purely in memory (never localStorage or cookies).
 * - Leaves Content-Type unset for FormData uploads so browser sets boundary.
 * - Refreshes CSRF state and retries at most once when explicitly rejected by CSRF middleware.
 */

let inMemoryCsrfToken: string | null = null;
let activeCsrfBootstrapPromise: Promise<string> | null = null;

/**
 * Fetches a cryptographically signed CSRF token from the server,
 * ensuring the session cookie is established in the browser.
 */
export async function fetchCsrfToken(forceRefresh = false): Promise<string> {
  if (inMemoryCsrfToken && !forceRefresh) {
    return inMemoryCsrfToken;
  }

  // Deduplicate concurrent in-flight token requests
  if (activeCsrfBootstrapPromise && !forceRefresh) {
    return activeCsrfBootstrapPromise;
  }

  activeCsrfBootstrapPromise = (async () => {
    try {
      // Primary endpoint /api/auth/csrf with fallback to /api/auth/csrf-token
      let res = await fetch('/api/auth/csrf', {
        method: 'GET',
        credentials: 'include',
        headers: {
          'Accept': 'application/json',
          'Cache-Control': 'no-cache',
        },
      });

      if (!res.ok && res.status === 404) {
        res = await fetch('/api/auth/csrf-token', {
          method: 'GET',
          credentials: 'include',
          headers: {
            'Accept': 'application/json',
            'Cache-Control': 'no-cache',
          },
        });
      }

      if (res.ok) {
        const data = await res.json();
        inMemoryCsrfToken = data.csrf_token || data.csrfToken || '';
        return inMemoryCsrfToken || '';
      }
      console.warn('Failed to retrieve CSRF token: status', res.status);
    } catch (err) {
      console.warn('Failed to retrieve CSRF token error:', err);
    } finally {
      activeCsrfBootstrapPromise = null;
    }
    return '';
  })();

  return activeCsrfBootstrapPromise;
}

/**
 * Invalidates the in-memory CSRF token.
 * Must be invoked on logout or session boundary changes.
 */
export function clearCsrfToken(): void {
  inMemoryCsrfToken = null;
  activeCsrfBootstrapPromise = null;
}

export async function apiRequest<T = any>(
  endpoint: string,
  options: RequestInit = {},
  isRetry = false
): Promise<T> {
  const method = (options.method || 'GET').toUpperCase();
  const headers = new Headers(options.headers || {});
  const isMutating = ['POST', 'PUT', 'DELETE', 'PATCH'].includes(method);

  // For mutating methods, attach CSRF token header
  if (isMutating) {
    const token = await fetchCsrfToken();
    if (token) {
      headers.set('X-CSRFToken', token);
    }
  }

  // If payload is not FormData, default to application/json
  // Crucial: NEVER manually set Content-Type for FormData uploads
  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(endpoint, {
    ...options,
    headers,
    credentials: 'include',
  });

  const contentType = response.headers.get('content-type') || '';
  let data: any = null;
  if (contentType.includes('application/json')) {
    try {
      data = await response.json();
    } catch {
      data = null;
    }
  } else {
    data = await response.text();
  }

  // Detect explicit CSRF middleware rejection
  const isCsrfError =
    response.status === 400 &&
    data &&
    typeof data === 'object' &&
    (data.code === 'CSRF_ERROR' ||
      (typeof data.error === 'string' && data.error.toLowerCase().includes('csrf')) ||
      (typeof data.message === 'string' && data.message.toLowerCase().includes('csrf')));

  if (isCsrfError && !isRetry && isMutating) {
    // Refresh CSRF state and retry exactly once
    clearCsrfToken();
    await fetchCsrfToken(true);
    return apiRequest<T>(endpoint, options, true);
  }

  if (!response.ok) {
    const errorMessage =
      (data && typeof data === 'object' && (data.error || data.message)) ||
      `Request failed with status ${response.status}`;
    const error = new Error(errorMessage) as any;
    error.status = response.status;
    error.data = data;
    throw error;
  }

  return data as T;
}

export const api = {
  get: <T = any>(url: string) => apiRequest<T>(url, { method: 'GET' }),
  post: <T = any>(url: string, body?: any) =>
    apiRequest<T>(url, {
      method: 'POST',
      body: body instanceof FormData ? body : (body !== undefined ? JSON.stringify(body) : undefined),
    }),
  put: <T = any>(url: string, body?: any) =>
    apiRequest<T>(url, {
      method: 'PUT',
      body: body instanceof FormData ? body : (body !== undefined ? JSON.stringify(body) : undefined),
    }),
  delete: <T = any>(url: string) => apiRequest<T>(url, { method: 'DELETE' }),
};
