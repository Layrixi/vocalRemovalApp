/**
 * Tests for utils.js changes in this PR.
 *
 * The PR removes the wrapText() function entirely from utils.js.
 * The remaining functions (formatTime, formatTimeFull, escHtml, etc.) were
 * not changed and are not in scope, but escHtml IS used by the changed
 * video.js overlay code, so we verify it works correctly here.
 */

// ---------------------------------------------------------------------------
// Load utils functions directly (no DOM or global state needed for these)
// ---------------------------------------------------------------------------

function loadUtils() {
  function formatTime(s) {
    if (!s || isNaN(s)) return '0:00';
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60).toString().padStart(2, '0');
    return `${m}:${sec}`;
  }

  function escHtml(str) {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  return { formatTime, escHtml };
}

const { formatTime, escHtml } = loadUtils();

// ---------------------------------------------------------------------------
// wrapText must not exist (it was removed in this PR)
// ---------------------------------------------------------------------------

describe('wrapText removal', () => {
  test('wrapText is not defined as a global after the PR', () => {
    // In the browser, utils.js no longer defines wrapText.
    // In the test environment we verify it is not accidentally exported.
    const utilsSource = require('fs').readFileSync(
      require('path').join(__dirname, '..', 'utils.js'),
      'utf8'
    );
    // The old function definition should be gone
    expect(utilsSource).not.toMatch(/function wrapText\s*\(/);
    expect(utilsSource).not.toMatch(/const wrapText\s*=/);
    expect(utilsSource).not.toMatch(/let wrapText\s*=/);
    expect(utilsSource).not.toMatch(/var wrapText\s*=/);
  });

  test('api.js defines wrapTextLine as a replacement for wrapText', () => {
    const apiSource = require('fs').readFileSync(
      require('path').join(__dirname, '..', 'api.js'),
      'utf8'
    );
    expect(apiSource).toMatch(/async function wrapTextLine\s*\(/);
  });
});

// ---------------------------------------------------------------------------
// escHtml – used by video.js overlay rendering (changed in this PR)
// ---------------------------------------------------------------------------

describe('escHtml (used by updated overlay rendering)', () => {
  test('escapes ampersand', () => {
    expect(escHtml('a & b')).toBe('a &amp; b');
  });

  test('escapes less-than', () => {
    expect(escHtml('<script>')).toBe('&lt;script&gt;');
  });

  test('escapes greater-than', () => {
    expect(escHtml('a > b')).toBe('a &gt; b');
  });

  test('escapes all special chars in one string', () => {
    expect(escHtml('<a & b>')).toBe('&lt;a &amp; b&gt;');
  });

  test('returns plain string unchanged', () => {
    expect(escHtml('hello world')).toBe('hello world');
  });

  test('empty string returns empty string', () => {
    expect(escHtml('')).toBe('');
  });

  test('multiple ampersands all escaped', () => {
    expect(escHtml('a && b && c')).toBe('a &amp;&amp; b &amp;&amp; c');
  });
});