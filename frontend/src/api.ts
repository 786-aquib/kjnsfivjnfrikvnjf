import {useEffect, useState} from 'react';

export function useApi<T>(url: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!url) {
      setData(null);
      setError(null);
      setLoading(false);
      return;
    }
    let isCancelled = false;
    const controller = new AbortController();
    setLoading(true);

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
      .then(result => {
        if (!isCancelled) {
          setData(result);
          setError(null);
          setLoading(false);
        }
      })
      .catch(err => {
        if (err.name !== 'AbortError' && !isCancelled) {
          setError(err instanceof Error ? err.message : 'Unable to load data.');
          setLoading(false);
        }
      });

    return () => {
      isCancelled = true;
      controller.abort();
    };
  }, [url, attempt]);

  return {
    data,
    error,
    loading,
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

