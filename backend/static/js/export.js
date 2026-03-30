//  EXPORT 

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
  showPopUp('LRC exported!');
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
  showPopUp('SRT exported!');
}
