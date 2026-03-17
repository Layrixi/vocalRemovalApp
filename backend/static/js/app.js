// ── STATE ──
const state = {
  lines: [],         // { text, timestamp: null|seconds }
  activeLineIdx: null,
  videoDuration: 0,
  speeds: [0.25, 0.5, 0.75, 1, 1.25, 1.5, 2],
  speedIdx: 3,
};

// ── ELEMENTS ──
const video         = document.getElementById('mainVideo');
const playBtn       = document.getElementById('playBtn');
const timeDisplay   = document.getElementById('timeDisplay');
const timelineWrap  = document.getElementById('timelineWrap');
const timelineProgress = document.getElementById('timelineProgress');
const playhead      = document.getElementById('playhead');
const hoverTime     = document.getElementById('hoverTime');
const lyricsList    = document.getElementById('lyricsList');
const lyricsRaw     = document.getElementById('lyricsRaw');
const lineCount     = document.getElementById('lineCount');
const activePill    = document.getElementById('activePill');
const instructionText = document.getElementById('instructionText');
const overlayText   = document.getElementById('overlayText');
const syncFlash     = document.getElementById('syncFlash');
const speedBtn      = document.getElementById('speedBtn');
const tickCanvas    = document.getElementById('tickCanvas');
const videoDropZone = document.getElementById('videoDropZone');
const videoWrapper  = document.getElementById('videoWrapper');
const syncedCount   = document.getElementById('syncedCount');
const remainingCount= document.getElementById('remainingCount');

// ── VIDEO LOADING ──
videoDropZone.addEventListener('click', () => document.getElementById('videoFileInput').click());
document.getElementById('videoFileInput').addEventListener('change', e => {
  const f = e.target.files[0];
  if (f) loadVideo(f);
});

videoDropZone.addEventListener('dragover', e => { e.preventDefault(); videoDropZone.style.borderColor = 'var(--amber)'; });
videoDropZone.addEventListener('dragleave', () => { videoDropZone.style.borderColor = ''; });
videoDropZone.addEventListener('drop', e => {
  e.preventDefault();
  videoDropZone.style.borderColor = '';
  const f = e.dataTransfer.files[0];
  if (f && f.type.startsWith('video/')) loadVideo(f);
});

function loadVideo(file) {
  const url = URL.createObjectURL(file);
  video.src = url;
  videoDropZone.style.display = 'none';
  videoWrapper.style.display = 'flex';
  video.load();
  video.addEventListener('loadedmetadata', () => {
    state.videoDuration = video.duration;
    updateTimeDisplay();
    drawTicks();
    renderMarkers();
    showToast('Video loaded — ' + formatTime(video.duration));
  }, { once: true });
}

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
  showToast(`Parsed ${state.lines.length} lines`);
}

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
  // Scroll into view
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

// ── TIMELINE INTERACTION ──
let isDragging = false;

timelineWrap.addEventListener('mousemove', e => {
  const pct = getTimelinePct(e);
  const t = pct * state.videoDuration;
  hoverTime.style.left = (pct * 100) + '%';
  hoverTime.textContent = formatTime(t);
  hoverTime.style.opacity = '1';
});

timelineWrap.addEventListener('mouseleave', () => {
  hoverTime.style.opacity = '0';
});

timelineWrap.addEventListener('mousedown', e => {
  isDragging = true;
  seekAndMaybeSync(e);
});

document.addEventListener('mousemove', e => {
  if (isDragging) seekTo(getTimelinePct(e) * state.videoDuration);
});

document.addEventListener('mouseup', e => {
  if (isDragging) {
    isDragging = false;
  }
});

timelineWrap.addEventListener('click', e => {
  const pct = getTimelinePct(e);
  const t = pct * state.videoDuration;
  if (state.activeLineIdx !== null && state.videoDuration > 0) {
    assignTimestamp(state.activeLineIdx, t);
  }
  seekTo(t);
});

function seekAndMaybeSync(e) {
  const pct = getTimelinePct(e);
  const t = pct * state.videoDuration;
  seekTo(t);
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
    showToast('All lines synced! 🎉');
  }

  renderLyricsList();
  renderMarkers();
  updateStats();
}

function getTimelinePct(e) {
  const rect = timelineWrap.getBoundingClientRect();
  return Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
}

function seekTo(t) {
  if (!state.videoDuration) return;
  t = Math.max(0, Math.min(state.videoDuration, t));
  video.currentTime = t;
  updatePlayhead(t);
  updateTimeDisplay();
}

// ── PLAYBACK ──
playBtn.addEventListener('click', () => {
  if (video.paused) { video.play(); playBtn.textContent = '⏸'; }
  else { video.pause(); playBtn.textContent = '▶'; }
});

video.addEventListener('ended', () => { playBtn.textContent = '▶'; });

video.addEventListener('timeupdate', () => {
  updatePlayhead(video.currentTime);
  updateTimeDisplay();
  updateOverlay();
  highlightCurrentLine();
});

function updatePlayhead(t) {
  if (!state.videoDuration) return;
  const pct = (t / state.videoDuration) * 100;
  playhead.style.left = pct + '%';
  timelineProgress.style.width = pct + '%';
}

function updateTimeDisplay() {
  const cur = formatTimeFull(video.currentTime);
  const tot = formatTime(state.videoDuration);
  timeDisplay.textContent = cur + ' / ' + tot;
}

// ── SPEED ──
speedBtn.addEventListener('click', () => {
  state.speedIdx = (state.speedIdx + 1) % state.speeds.length;
  const spd = state.speeds[state.speedIdx];
  video.playbackRate = spd;
  speedBtn.textContent = spd + '×';
});

// ── OVERLAY ──
function updateOverlay() {
  const t = video.currentTime;
  const synced = state.lines
    .filter(l => l.timestamp !== null && l.timestamp <= t)
    .sort((a, b) => b.timestamp - a.timestamp);

  // Check next line to hide current
  const nextSynced = state.lines
    .filter(l => l.timestamp !== null && l.timestamp > t)
    .sort((a, b) => a.timestamp - b.timestamp)[0];

  if (synced.length > 0) {
    const cur = synced[0];
    // Hide if next line starts very soon (0.1s buffer)
    overlayText.textContent = cur.text;
    overlayText.classList.add('visible');
  } else {
    overlayText.classList.remove('visible');
  }
}

function highlightCurrentLine() {
  const t = video.currentTime;
  const synced = state.lines
    .filter(l => l.timestamp !== null && l.timestamp <= t)
    .sort((a, b) => b.timestamp - a.timestamp);

  if (synced.length > 0) {
    const cur = synced[0];
    const idx = state.lines.indexOf(cur);
    const els = lyricsList.querySelectorAll('.lyric-line');
    els.forEach((el, i) => {
      el.style.outline = i === idx ? '1px solid var(--amber)' : '';
    });
  }
}

// ── MARKERS ON TIMELINE ──
function renderMarkers() {
  timelineWrap.querySelectorAll('.lyric-marker').forEach(m => m.remove());
  if (!state.videoDuration) return;

  state.lines.forEach((line, i) => {
    if (line.timestamp === null) return;
    const pct = (line.timestamp / state.videoDuration) * 100;
    const marker = document.createElement('div');
    marker.className = 'lyric-marker';
    marker.style.left = pct + '%';
    marker.dataset.label = line.text.substring(0, 12);
    marker.title = `[${formatTime(line.timestamp)}] ${line.text}`;
    marker.addEventListener('click', e => {
      e.stopPropagation();
      seekTo(line.timestamp);
      selectLine(i);
    });
    timelineWrap.appendChild(marker);
  });
}

// ── TICK MARKS ──
function drawTicks() {
  const canvas = tickCanvas;
  const wrap = timelineWrap;
  canvas.width = wrap.clientWidth;
  canvas.height = 14;
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  if (!state.videoDuration) return;

  // Choose tick interval
  let interval = 1;
  if (state.videoDuration > 120) interval = 10;
  else if (state.videoDuration > 60) interval = 5;

  ctx.strokeStyle = 'rgba(107,104,120,0.6)';
  ctx.fillStyle = 'rgba(107,104,120,0.8)';
  ctx.font = '8px Syne Mono, monospace';
  ctx.textAlign = 'center';

  for (let t = 0; t <= state.videoDuration; t += interval) {
    const x = (t / state.videoDuration) * canvas.width;
    ctx.beginPath();
    ctx.moveTo(x, 8); ctx.lineTo(x, 14);
    ctx.stroke();
    if (t % (interval * 2) === 0 || interval === 1) {
      ctx.fillText(formatTime(t), x, 7);
    }
  }
}

window.addEventListener('resize', drawTicks);

// ── KEYBOARD SHORTCUTS ──
document.addEventListener('keydown', e => {
  // Space = play/pause
  if (e.code === 'Space' && document.activeElement !== lyricsRaw) {
    e.preventDefault();
    if (video.paused) { video.play(); playBtn.textContent = '⏸'; }
    else { video.pause(); playBtn.textContent = '▶'; }
  }
  // M = mark current time for active line
  if (e.code === 'KeyM' && state.activeLineIdx !== null && state.videoDuration) {
    assignTimestamp(state.activeLineIdx, video.currentTime);
  }
  // Arrow keys: step through lines
  if (e.code === 'ArrowDown' && document.activeElement !== lyricsRaw) {
    e.preventDefault();
    const next = state.activeLineIdx === null ? 0 : Math.min(state.lines.length - 1, state.activeLineIdx + 1);
    selectLine(next);
  }
  if (e.code === 'ArrowUp' && document.activeElement !== lyricsRaw) {
    e.preventDefault();
    const prev = state.activeLineIdx === null ? 0 : Math.max(0, state.activeLineIdx - 1);
    selectLine(prev);
  }
  // Left/Right: nudge video
  if (e.code === 'ArrowLeft' && document.activeElement !== lyricsRaw) {
    e.preventDefault();
    seekTo(video.currentTime - (e.shiftKey ? 5 : 1));
  }
  if (e.code === 'ArrowRight' && document.activeElement !== lyricsRaw) {
    e.preventDefault();
    seekTo(video.currentTime + (e.shiftKey ? 5 : 1));
  }
});

// ── EXPORT ──
document.getElementById('exportBtn').addEventListener('click', exportLRC);
document.getElementById('exportSrtBtn').addEventListener('click', exportSRT);

function exportLRC() {
  const sorted = [...state.lines].filter(l => l.timestamp !== null)
    .sort((a, b) => a.timestamp - b.timestamp);
  const content = sorted.map(l => {
    const mins = Math.floor(l.timestamp / 60).toString().padStart(2, '0');
    const secs = (l.timestamp % 60).toFixed(2).padStart(5, '0');
    return `[${mins}:${secs}]${l.text}`;
  }).join('\n');
  download('lyrics.lrc', content);
  showToast('LRC exported!');
}

function exportSRT() {
  const sorted = [...state.lines].filter(l => l.timestamp !== null)
    .sort((a, b) => a.timestamp - b.timestamp);
  const content = sorted.map((l, i) => {
    const start = toSRTTime(l.timestamp);
    const end = toSRTTime(sorted[i + 1] ? sorted[i + 1].timestamp - 0.1 : l.timestamp + 3);
    return `${i + 1}\n${start} --> ${end}\n${l.text}\n`;
  }).join('\n');
  download('lyrics.srt', content);
  showToast('SRT exported!');
}

function toSRTTime(s) {
  const h = Math.floor(s / 3600).toString().padStart(2, '0');
  const m = Math.floor((s % 3600) / 60).toString().padStart(2, '0');
  const sec = Math.floor(s % 60).toString().padStart(2, '0');
  const ms = Math.round((s % 1) * 1000).toString().padStart(3, '0');
  return `${h}:${m}:${sec},${ms}`;
}

function download(filename, content) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([content], { type: 'text/plain' }));
  a.download = filename;
  a.click();
}

// ── STATS ──
function updateStats() {
  const synced = state.lines.filter(l => l.timestamp !== null).length;
  syncedCount.textContent = synced;
  remainingCount.textContent = state.lines.length - synced;
}

// ── UTILS ──
function formatTime(s) {
  if (!s || isNaN(s)) return '0:00';
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60).toString().padStart(2, '0');
  return `${m}:${sec}`;
}

function formatTimeFull(s) {
  if (!s || isNaN(s)) return '0:00.0';
  const m = Math.floor(s / 60);
  const sec = (s % 60).toFixed(1).padStart(4, '0');
  return `${m}:${sec}`;
}

function escHtml(str) {
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function showToast(msg, duration = 2200) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), duration);
}

// ── INIT ──
updateInstructions();