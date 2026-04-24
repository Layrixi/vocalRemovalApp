//  LYRICS LOADING 

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

// splits the text by newlines into plain lyric lines.
async function parseAndRenderLyrics() {
  const raw = lyricsRaw.value.trim();
  if (!raw) return;

  state.lines = raw.split('\n')
    .map(l => l.trim())
    .filter(l => l.length > 0)
    .map(l => ({ text: l, timestamp: null, style: { ...DEFAULT_STYLE } }));

  // Wait for backend-accurate wrap before rendering so overlay is correct from the start
  await Promise.all(
    state.lines.map(line =>
      wrapTextLine(line.text, line.style.font_size).then(lines => {
        if (lines) line.wrappedText = lines;
      })
    )
  );

  renderLyricsList();
  renderMarkers();
  showPopUp(`Parsed ${state.lines.length} lines`);
}

//could be handled by backend, but works for now.
//Renders the list of lyric lines and their timestamps, sets up click handlers for selecting lines and removing timestamps.
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

    el.addEventListener('click', () => {
      selectLine(i);
      openStyleEditor(i);
    });
    lyricsList.appendChild(el);
  });

  // Remove timestamp x handlers
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

// shows instructions above the timeline, changes based on whether a line is active or not.
function updateInstructions() {
    //line selected, display instructions and pill block with the text
  if (state.activeLineIdx !== null && state.lines[state.activeLineIdx]) {
    const line = state.lines[state.activeLineIdx];
    instructionText.textContent = 'Click anywhere on the timeline to set timestamp for:';
    activePill.textContent = `"${line.text}"`;
    activePill.style.display = 'block';
    //line not selected, display generic instructions and hide pill block
  } else {
    instructionText.textContent = 'Select a lyric line on the left, then click the timeline to assign its start time.';
    activePill.style.display = 'none';
  }
}

// assigns the timestamp to the line, then advances to the next unsynced line
// also flashes the synced line and handles edge cases like all lines synced or reaching the end of the list.
function assignTimestamp(idx, time) {
  state.lines[idx].timestamp = parseFloat(time.toFixed(6));
  // Auto-advance to next unsynced line (forward first, then wrap)
  let next = idx + 1;
  while (next < state.lines.length && state.lines[next].timestamp !== null) next++;
  
  if (next < state.lines.length) {
    state.activeLineIdx = next;
  } else {
    const firstUnsynced = state.lines.findIndex(l => l.timestamp === null);
    if (firstUnsynced === -1) {
      state.activeLineIdx = null;
      showPopUp('All lines synced! 🎉');
    } else {
      // Wrap around to first unsynced line earlier in the list
      state.activeLineIdx = firstUnsynced;
    }
  }

  renderLyricsList();
  renderMarkers();
  updateStats();

  // Flash the line that was just synced
  const el = lyricsList.children[idx];
  if (el) {
    el.classList.add('line-flash');
    setTimeout(() => el.classList.remove('line-flash'), 600);
  }
}

//  STATS 
//simple sync and unsynced count
function updateStats() {
  const synced = state.lines.filter(l => l.timestamp !== null).length;
  syncedCount.textContent = synced;
  remainingCount.textContent = state.lines.length - synced;
}
