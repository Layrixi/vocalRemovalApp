//  UTILS 

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
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function showPopUp(msg, duration = 2200) {
  const t = document.getElementById('pop_up');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), duration);
}

function showFieldTip(msg, anchorEl) {
  const tip = document.getElementById('field_tip');
  tip.textContent = msg.replace(/\\n/g, '\n');
  tip.classList.add('show');
  const rect = anchorEl.getBoundingClientRect();
  tip.style.top  = (rect.bottom + 6) + 'px';
  tip.style.left = rect.left + 'px';
}

function hideFieldTip() {
  document.getElementById('field_tip').classList.remove('show');
}

function download(filename, content) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([content], { type: 'text/plain' }));
  a.download = filename;
  a.click();
}

