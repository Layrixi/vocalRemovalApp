//  VIDEO LOADING 

videoDropZone.addEventListener('click', () => document.getElementById('videoFileInput').click());
document.getElementById('videoFileInput').addEventListener('change', e => {
  const f = e.target.files[0];
  if (f) loadVideo(f);
});

videoDropZone.addEventListener('dragover', e => {
  e.preventDefault();
  videoDropZone.style.borderColor = 'var(--amber)';
});
videoDropZone.addEventListener('dragleave', () => { videoDropZone.style.borderColor = ''; });
videoDropZone.addEventListener('drop', e => {
  e.preventDefault();
  videoDropZone.style.borderColor = '';
  const f = e.dataTransfer.files[0];
  if (f && f.type.startsWith('video/')) loadVideo(f);
});

// Loads the video file into the player and sends it to the backend
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
    showPopUp('Video loaded — ' + formatTime(video.duration));
  }, { once: true });

  state.uploadedVideoFilename = null;
  uploadVideo(file)
    .catch(() => { showPopUp('Server upload failed'); return null; })
    .then(filename => {
      if (!filename) return null;
      state.uploadedVideoFilename = filename;
      showPopUp('Video uploaded to server');})
    .then(result => {
      if (result === null) return;
      // Re-wrap all lines now that we have accurate video dimensions
      if (state.lines.length > 0) {
        return Promise.all(
          state.lines.map(line =>
            wrapTextLine(line.text, line.style.font_size)
              .then(lines => { if (lines) line.wrappedText = lines; })
              .catch(() => { showPopUp('Failed to wrap text'); })
          )
        );
      }
    });
    return null;
}

//  TIMELINE INTERACTION 
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

document.addEventListener('mouseup', () => {
  if (isDragging) isDragging = false;
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

//  PLAYBACK 
playBtn.addEventListener('click', () => {
  if (video.paused) { video.play(); playBtn.textContent = '⏸'; }
  else { video.pause(); playBtn.textContent = '▶'; }
});

video.addEventListener('ended', () => { playBtn.textContent = '▶'; });

video.addEventListener('timeupdate', () => {
  updatePlayhead(video.currentTime);
  updateTimeDisplay();
  updateOverlayAndHighlight();
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

//  SPEED 
speedBtn.addEventListener('click', () => {
  state.speedIdx = (state.speedIdx + 1) % state.speeds.length;
  const spd = state.speeds[state.speedIdx];
  video.playbackRate = spd;
  speedBtn.textContent = spd + '×';
});

//  OVERLAY + HIGHLIGHT 
function updateOverlayAndHighlight() {
  const t = video.currentTime;
  // sorted for lookup on which line to show onthe overlay
  const synced = state.lines
    .filter(l => l.timestamp !== null && l.timestamp <= t)
    .sort((a, b) => b.timestamp - a.timestamp);

  if (synced.length > 0) {
    // show the line on the video overlay, wrapped to match TextBurner output|| with fallback to raw unwrapped text in case there's no already wrapped text (shouldn't happen)
    overlayText.innerHTML = (synced[0].wrappedText ?? [synced[0].text]).map(escHtml).join('<br>');
    overlayText.classList.add('visible');
    // apply this line's per-line style
    if (synced[0].style) applyStyleToOverlay(synced[0].style);
    
    //highlight the active line in the list
    const idx = state.lines.indexOf(synced[0]);
    lyricsList.querySelectorAll('.lyric-line').forEach((el, i) => {
      el.style.outline = i === idx ? '1px solid var(--amber)' : '';
    });
  } else {
    overlayText.classList.remove('visible');
  }
}

//  MARKERS ON TIMELINE 
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

//  TICK MARKS 
function drawTicks() {
  const canvas = tickCanvas;
  const wrap = timelineWrap;
  canvas.width = wrap.clientWidth;
  canvas.height = 14;
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  if (!state.videoDuration) return;

  // to change depending on zoom level
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

window.addEventListener('resize', () => {
  drawTicks();
  updateOverlayAndHighlight();
});
