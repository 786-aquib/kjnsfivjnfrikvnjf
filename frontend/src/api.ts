import {useEffect, useState} from 'react';

export function useApi<T>(url: string | null) {
  const [state, setState] = useState<{url: string; data: T | null; error: string | null}>({url: '', data: null, error: null});
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!url) {
      setState({url: '', data: null, error: null});
      return;
    }
    let isCancelled = false;
    const controller = new AbortController();
    setState({url, data: null, error: null});

    fetch(url, {signal: controller.signal})
      .then(async response => {
        const text = await response.text();
        let body: any = null;
        try {
          body = text ? JSON.parse(text) : {};
        } catch {
          if (!response.ok) {
            throw new Error(`Server returned error ${response.status}: ${response.statusText || 'Unexpected response'}`);
          }
          throw new Error('Server returned an invalid JSON response format.');
        }

        if (!response.ok) {
          let message = 'The request could not be completed. Check the selected dates and time.';
          if (typeof body?.detail === 'string') {
            message = body.detail;
          } else if (Array.isArray(body?.detail)) {
            message = body.detail.map((e: any) => e.msg || e.message || String(e)).join('; ');
          } else if (typeof body?.message === 'string') {
            message = body.message;
          }
          throw new Error(message);
        }
        return body as T;
      })
      .then(data => {
        if (!isCancelled) {
          setState({url, data, error: null});
        }
      })
      .catch(error => {
        if (error.name !== 'AbortError' && !isCancelled) {
          setState({url, data: null, error: error instanceof Error ? error.message : 'Unable to load data.'});
        }
      });

    return () => {
      isCancelled = true;
      controller.abort();
    };
  }, [url, attempt]);

  return {
    data: url && state.url === url ? state.data : null,
    error: url && state.url === url ? state.error : null,
    retry: () => setAttempt(n => n + 1),
  };
}

export const number = (value: number | null | undefined, digits = 0): string => {
  if (value == null || typeof value !== 'number' || !Number.isFinite(value)) return '—';
  try {
    return new Intl.NumberFormat('en-GB', {maximumFractionDigits: digits}).format(value);
  } catch {
    return '—';
  }
};

export const clock = (value: string | null | undefined): string => {
  if (!value) return '—';
  try {
    const d = new Date(value);
    if (isNaN(d.getTime())) return '—';
    return new Intl.DateTimeFormat('en-GB', {timeZone: 'Europe/London', hour: '2-digit', minute: '2-digit'}).format(d);
  } catch {
    return '—';
  }
};

export const dateLabel = (value: string | null | undefined): string => {
  if (!value) return '—';
  try {
    const d = new Date(value.length === 10 ? value + 'T12:00:00Z' : value);
    if (isNaN(d.getTime())) return '—';
    return new Intl.DateTimeFormat('en-GB', {timeZone: 'Europe/London', day: 'numeric', month: 'short', year: 'numeric'}).format(d);
  } catch {
    return '—';
  }
};

