// ── LYRICS LOADING ──

document.getElementById('lyricsUploadZone').addEventListener('click', () =>
  document.getElementById('lyricsFileInput').click());

document.getElementById('lyricsFileInput').addEventListener('change', e => {
  const f = e.target.files[0];
  if (!f) return;
  const reader = new FileReader();
  reader.onload = ev => {
    lyricsRaw.value = ev.target.result;
    parseAndRenderLyrics();
  };
  reader.readAsText(f);
});

document.getElementById('parseLyricsBtn').addEventListener('click', parseAndRenderLyrics);
document.getElementById('clearLyricsBtn').addEventListener('click', () => {
  lyricsRaw.value = '';
  state.lines = [];
  state.activeLineIdx = null;
  renderLyricsList();
  renderMarkers();
});

// skip LRC and SRT handling for now, todo lated
// splits the text by newlines, deletes LRC and SRT metadata.
function parseAndRenderLyrics() {
  const raw = lyricsRaw.value.trim();
  if (!raw) return;

  // Detect LRC format [mm:ss.xx]
  const lrcPattern = /\[(\d+):(\d+\.\d+)\]\s*(.*)/;
  const lines = raw.split('\n')
    .map(l => l.trim())
    .filter(l => l.length > 0 && !l.startsWith('[ti:') && !l.startsWith('[ar:'));

  state.lines = lines.map(l => {
    const m = l.match(lrcPattern);
    if (m) {
      const secs = parseFloat(m[1]) * 60 + parseFloat(m[2]);
      return { text: m[3], timestamp: secs };
    }
    // SRT: strip timing lines
    if (/^\d+$/.test(l) || /\d{2}:\d{2}:\d{2},\d{3}/.test(l) || /-->/.test(l)) return null;
    return { text: l.replace(/\[.*?\]/g, '').trim(), timestamp: null };
  }).filter(l => l && l.text.length > 0);

  renderLyricsList();
  renderMarkers();
  showPopUp(`Parsed ${state.lines.length} lines`);
}

//could be handled by backend, but works for now.
function renderLyricsList() {
  lyricsList.innerHTML = '';
  state.lines.forEach((line, i) => {
    const el = document.createElement('div');
    el.className = 'lyric-line' +
      (line.timestamp !== null ? ' synced' : '') +
      (state.activeLineIdx === i ? ' active' : '');
    el.dataset.idx = i;

    el.innerHTML = `
      <span class="line-index">${String(i + 1).padStart(2, '0')}</span>
      <span class="line-text">${escHtml(line.text)}</span>
      <span class="line-timestamp">${line.timestamp !== null ? formatTime(line.timestamp) : ''}</span>
      ${line.timestamp !== null ? `<span class="remove-ts" data-idx="${i}" title="Remove timestamp">✕</span>` : ''}
    `;

    el.addEventListener('click', () => selectLine(i));
    lyricsList.appendChild(el);
  });

  // Remove timestamp handlers
  lyricsList.querySelectorAll('.remove-ts').forEach(btn => {
    btn.addEventListener('click', e => {
      e.stopPropagation();
      const idx = parseInt(btn.dataset.idx);
      state.lines[idx].timestamp = null;
      renderLyricsList();
      renderMarkers();
      updateStats();
    });
  });

  lineCount.textContent = state.lines.length + ' line' + (state.lines.length !== 1 ? 's' : '');
  updateInstructions();
  updateStats();
}

function selectLine(idx) {
  state.activeLineIdx = idx;
  renderLyricsList();
  const el = lyricsList.children[idx];
  if (el) el.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  updateInstructions();
}

function updateInstructions() {
  if (state.activeLineIdx !== null && state.lines[state.activeLineIdx]) {
    const line = state.lines[state.activeLineIdx];
    instructionText.textContent = 'Click anywhere on the timeline to set timestamp for:';
    activePill.textContent = `"${line.text}"`;
    activePill.style.display = 'block';
  } else {
    instructionText.textContent = 'Select a lyric line on the left, then click the timeline to assign its start time.';
    activePill.style.display = 'none';
  }
}

function assignTimestamp(idx, time) {
  state.lines[idx].timestamp = parseFloat(time.toFixed(3));
  // Flash effect
  syncFlash.style.display = 'block';
  setTimeout(() => syncFlash.style.display = 'none', 600);

  // Auto-advance to next unsynced line
  let next = idx + 1;
  while (next < state.lines.length && state.lines[next].timestamp !== null) next++;
  if (next < state.lines.length) {
    state.activeLineIdx = next;
  } else {
    state.activeLineIdx = null;
    showPopUp('All lines synced! 🎉');
  }

  renderLyricsList();
  renderMarkers();
  updateStats();
}

// ── STATS ──
function updateStats() {
  const synced = state.lines.filter(l => l.timestamp !== null).length;
  syncedCount.textContent = synced;
  remainingCount.textContent = state.lines.length - synced;
}
