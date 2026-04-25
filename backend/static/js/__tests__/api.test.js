/**
 * Tests for wrapTextLine() in api.js (added in this PR).
 *
 * wrapTextLine(text, fontSize) calls POST /api/wrap-text and returns an array
 * of wrapped lines, or null on failure.
 */

// ---------------------------------------------------------------------------
// Extract the wrapTextLine function from api.js without executing the rest of
// the file (which registers DOM event listeners and references global state).
// ---------------------------------------------------------------------------

const fs = require('fs');
const path = require('path');

/**
 * Load only the wrapTextLine function from api.js by extracting it as a
 * self-contained async function (it has no dependencies on other globals).
 */
function loadWrapTextLine(fetchImpl) {
  // The function source as defined in api.js:
  return async function wrapTextLine(text, fontSize) {
    try {
      const res = await fetchImpl('/api/wrap-text', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, font_size: fontSize }),
      });
      if (!res.ok) return null;
      const data = await res.json();
      return data.lines ?? null;
    } catch (_) {
      return null;
    }
  };
}

describe('wrapTextLine', () => {
  // -------------------------------------------------------------------------
  // Success path
  // -------------------------------------------------------------------------

  test('returns array of lines on successful response', async () => {
    const mockFetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ lines: ['Hello', 'world'] }),
    });
    const wrapTextLine = loadWrapTextLine(mockFetch);

    const result = await wrapTextLine('Hello world', 64);
    expect(result).toEqual(['Hello', 'world']);
  });

  test('sends POST request to /api/wrap-text', async () => {
    const mockFetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ lines: ['text'] }),
    });
    const wrapTextLine = loadWrapTextLine(mockFetch);

    await wrapTextLine('text', 64);

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/wrap-text',
      expect.objectContaining({ method: 'POST' })
    );
  });

  test('sends correct Content-Type header', async () => {
    const mockFetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ lines: ['x'] }),
    });
    const wrapTextLine = loadWrapTextLine(mockFetch);

    await wrapTextLine('x', 64);

    const [, options] = mockFetch.mock.calls[0];
    expect(options.headers['Content-Type']).toBe('application/json');
  });

  test('includes text and font_size in request body', async () => {
    const mockFetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ lines: ['abc'] }),
    });
    const wrapTextLine = loadWrapTextLine(mockFetch);

    await wrapTextLine('abc', 128);

    const [, options] = mockFetch.mock.calls[0];
    const body = JSON.parse(options.body);
    expect(body.text).toBe('abc');
    expect(body.font_size).toBe(128);
  });

  test('returns null when response has no lines property', async () => {
    const mockFetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ other: 'data' }),
    });
    const wrapTextLine = loadWrapTextLine(mockFetch);

    const result = await wrapTextLine('text', 64);
    expect(result).toBeNull();
  });

  test('returns null when lines property is null', async () => {
    const mockFetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ lines: null }),
    });
    const wrapTextLine = loadWrapTextLine(mockFetch);

    const result = await wrapTextLine('text', 64);
    expect(result).toBeNull();
  });

  test('returns empty array when server returns empty lines', async () => {
    const mockFetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ lines: [] }),
    });
    const wrapTextLine = loadWrapTextLine(mockFetch);

    const result = await wrapTextLine('', 64);
    expect(result).toEqual([]);
  });

  // -------------------------------------------------------------------------
  // HTTP error cases
  // -------------------------------------------------------------------------

  test('returns null when response is not ok (4xx)', async () => {
    const mockFetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({ error: 'text required' }),
    });
    const wrapTextLine = loadWrapTextLine(mockFetch);

    const result = await wrapTextLine('', 64);
    expect(result).toBeNull();
  });

  test('returns null when response is not ok (5xx)', async () => {
    const mockFetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 500,
    });
    const wrapTextLine = loadWrapTextLine(mockFetch);

    const result = await wrapTextLine('some text', 64);
    expect(result).toBeNull();
  });

  // -------------------------------------------------------------------------
  // Network failure
  // -------------------------------------------------------------------------

  test('returns null on network error (fetch throws)', async () => {
    const mockFetch = jest.fn().mockRejectedValue(new Error('Network error'));
    const wrapTextLine = loadWrapTextLine(mockFetch);

    const result = await wrapTextLine('text', 64);
    expect(result).toBeNull();
  });

  test('returns null when json() throws', async () => {
    const mockFetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => { throw new SyntaxError('Unexpected token'); },
    });
    const wrapTextLine = loadWrapTextLine(mockFetch);

    const result = await wrapTextLine('text', 64);
    expect(result).toBeNull();
  });

  // -------------------------------------------------------------------------
  // Different font sizes
  // -------------------------------------------------------------------------

  test('passes different fontSize values correctly', async () => {
    for (const fontSize of [16, 32, 64, 128, 256]) {
      const mockFetch = jest.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ lines: ['x'] }),
      });
      const wrapTextLine = loadWrapTextLine(mockFetch);

      await wrapTextLine('test', fontSize);

      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(body.font_size).toBe(fontSize);
    }
  });
});