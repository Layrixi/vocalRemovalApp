// --  CONFIG --

// Calls backend text wrapping method and returns an array of wrapped lines, or null on failure.
async function wrapTextLine(text, fontSize) {
  try {
    const res = await fetch('/api/wrap-text', {
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
}


// -- VOCAL REMOVAL API --

async function uploadVideo(file) {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch('/api/upload-video', { method: 'POST', body: formData });
  if (!res.ok) throw new Error('Upload failed');
  const data = await res.json();
  if (data.error) throw new Error(data.error);
  return data.filename;
}

document.getElementById('removeVocalsBtn').addEventListener('click', async () => {
  if (!state.uploadedVideoFilename) {
    showPopUp('Load a video first');
    return;
  }
  const btn = document.getElementById('removeVocalsBtn');
  btn.disabled = true;
  btn.textContent = 'Processing...';
  document.getElementById('vocalProcessingHint').style.display = 'block';
  try {
    const res = await fetch('/api/remove-vocals', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filename: state.uploadedVideoFilename })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Processing failed');
    const a = document.createElement('a');
    a.href = data.download_url;
    a.download = '';
    a.click();
    showPopUp('Instrumental ready to download');
  } catch (e) {
    showPopUp('Error: ' + e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Remove Vocals';
    document.getElementById('vocalProcessingHint').style.display = 'none';
  }
});

// -- VIDEO RENDER API --

document.getElementById('renderVideoBtn').addEventListener('click', async () => {
  if (!state.uploadedVideoFilename) {
    showPopUp('Load a video first');
    return;
  }
  const synced = state.lines.filter(l => l.timestamp !== null);
  if (synced.length === 0) {
    showPopUp('Sync at least one line first');
    return;
  }

  const btn = document.getElementById('renderVideoBtn');
  btn.disabled = true;
  btn.textContent = 'Rendering…';
  try {
    const res = await fetch('/api/render-video', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filename: state.uploadedVideoFilename, lines: synced }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Render failed');
    const a = document.createElement('a');
    a.href = data.download_url;
    a.download = '';
    a.click();
    showPopUp('Rendered video ready!');
  } catch (e) {
    showPopUp('Error: ' + e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Render Video';
  }
});
