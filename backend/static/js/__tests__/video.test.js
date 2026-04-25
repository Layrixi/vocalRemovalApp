/**
 * Tests for the overlay rendering change in video.js (this PR).
 *
 * The key change:
 *   Before: overlayText.innerHTML = wrapText(line.text, line.style?.font_size).map(escHtml).join('<br>');
 *   After:  overlayText.innerHTML = (synced[0].wrappedText ?? [synced[0].text]).map(escHtml).join('<br>');
 *
 * This means:
 *   - If line.wrappedText exists, it is used directly.
 *   - If line.wrappedText is absent/undefined/null, [line.text] is used as fallback.
 *   - The old wrapText() client-side function is no longer called.
 */

// ---------------------------------------------------------------------------
// Helper: reproduce the overlay innerHTML logic extracted from video.js
// ---------------------------------------------------------------------------

function escHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

/**
 * Replicate the overlay rendering expression from the updated video.js:
 *   (synced[0].wrappedText ?? [synced[0].text]).map(escHtml).join('<br>')
 */
function renderOverlayHtml(line) {
  return (line.wrappedText ?? [line.text]).map(escHtml).join('<br>');
}

describe('overlay rendering – wrappedText usage', () => {

  test('uses wrappedText array when present', () => {
    const line = {
      text: 'original text',
      wrappedText: ['wrapped line 1', 'wrapped line 2'],
    };
    const html = renderOverlayHtml(line);
    expect(html).toBe('wrapped line 1<br>wrapped line 2');
  });

  test('falls back to [text] when wrappedText is undefined', () => {
    const line = { text: 'fallback text' };
    const html = renderOverlayHtml(line);
    expect(html).toBe('fallback text');
  });

  test('falls back to [text] when wrappedText is null', () => {
    const line = { text: 'fallback text', wrappedText: null };
    const html = renderOverlayHtml(line);
    expect(html).toBe('fallback text');
  });

  test('single-element wrappedText renders without <br>', () => {
    const line = { text: 'original', wrappedText: ['single line'] };
    const html = renderOverlayHtml(line);
    expect(html).toBe('single line');
    expect(html).not.toContain('<br>');
  });

  test('three-line wrappedText joins with <br>', () => {
    const line = {
      text: 'original',
      wrappedText: ['line one', 'line two', 'line three'],
    };
    const html = renderOverlayHtml(line);
    expect(html).toBe('line one<br>line two<br>line three');
  });

  test('HTML special chars in wrappedText are escaped', () => {
    const line = {
      text: 'safe',
      wrappedText: ['<b>bold</b>', 'a & b'],
    };
    const html = renderOverlayHtml(line);
    expect(html).toBe('&lt;b&gt;bold&lt;/b&gt;<br>a &amp; b');
  });

  test('HTML special chars in fallback text are escaped', () => {
    const line = { text: '<script>alert(1)</script>' };
    const html = renderOverlayHtml(line);
    expect(html).toBe('&lt;script&gt;alert(1)&lt;/script&gt;');
  });

  test('empty wrappedText array renders nothing', () => {
    const line = { text: 'original', wrappedText: [] };
    const html = renderOverlayHtml(line);
    expect(html).toBe('');
  });

  test('wrappedText with empty strings produces empty <br> segments', () => {
    const line = { text: 'x', wrappedText: ['first', '', 'third'] };
    const html = renderOverlayHtml(line);
    expect(html).toBe('first<br><br>third');
  });
});

// ---------------------------------------------------------------------------
// Tests verifying video.js source no longer calls wrapText()
// ---------------------------------------------------------------------------

describe('video.js source – wrapText removed from overlay path', () => {
  const videoSrc = require('fs').readFileSync(
    require('path').join(__dirname, '..', 'video.js'),
    'utf8'
  );

  test('overlay rendering uses wrappedText property, not wrapText()', () => {
    // The updated line must reference wrappedText
    expect(videoSrc).toMatch(/wrappedText/);
  });

  test('wrapText() call is not present in video.js', () => {
    // The old call wrapText(synced[0].text, …) must be gone
    expect(videoSrc).not.toMatch(/\bwrapText\s*\(/);
  });
});