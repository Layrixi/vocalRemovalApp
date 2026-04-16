// STYLE EDITOR
// Slide-in panel that lets the user configure per-line ASS TextStyle values.
// Updates state.lines[idx].style on every input change.

let _editingIdx = null;

// ── Apply a style object to the live video overlay ──────────────────────────

const _OVERLAY_POS = {
  bottom: { top: '',    bottom: '14%', transform: 'translateX(-50%)',      alignItems: 'flex-end'   },
  center: { top: '50%', bottom: '',   transform: 'translate(-50%, -50%)', alignItems: 'center'     },
  top:    { top: '14%', bottom: '',   transform: 'translateX(-50%)',      alignItems: 'flex-start' },
};

function applyStyleToOverlay(style) {
  const elem      = overlayText;
  const overlay = document.querySelector('.video-lyrics-overlay');

  const fontName = style.font_file
    ? style.font_file.replace(/\\/g, '/').split('/').pop().replace(/\.[^.]+$/, '')
    : 'Comic Sans MS';

  elem.style.fontFamily       = `"${fontName}", sans-serif`;
  elem.style.color            = style.font_color;
  elem.style.webkitTextStroke = style.border_width > 0
    ? `${style.border_width}px ${style.border_color}` : '0';

  if (style.box) {
    elem.style.backgroundColor = style.box_color;
    elem.style.padding         = style.box_padding + 'px';
  } else {
    elem.style.backgroundColor = 'transparent';
    elem.style.padding         = '0';
  }

  elem.style.textShadow = style.shadow
    ? `${style.shadow_x}px ${style.shadow_y}px 0 ${style.shadow_color}`
    : 'none';

  elem.style.textAlign = style.horizontal_position;

  // Scale font size
  const videoH = video.clientHeight || 360;
  elem.style.fontSize = (style.font_size / state.wrapConfig.play_res_y * videoH) + 'px';

  // Reposition overlay container
  if (overlay) {
    const pos = _OVERLAY_POS[style.vertical_position] || _OVERLAY_POS.bottom;
    overlay.style.top        = pos.top;
    overlay.style.bottom     = pos.bottom;
    overlay.style.transform  = pos.transform;
    overlay.style.alignItems = pos.alignItems;
  }
}

// ── Open / close ──────────────────────────────────────────────────────────────

function openStyleEditor(idx) {
  _editingIdx = idx;
  const s = state.lines[idx].style;

  //label
  document.getElementById('se_line_label').textContent =
    `Line ${idx + 1} · "${state.lines[idx].text.slice(0, 36)}${state.lines[idx].text.length > 36 ? '…' : ''}"`;

  // Populate every field from the line's style
  _setField('se_font_file',   s.font_file || '');
  _setField('se_font_size',   s.font_size);
  _setColor('se_font_color',  s.font_color);

  _setField('se_border_width', s.border_width);
  _setColor('se_border_color', s.border_color);

  _setCheck('se_box',          s.box);
  _setColor('se_box_color',    s.box_color);
  _setField('se_box_padding',  s.box_padding);

  _setCheck('se_shadow',       s.shadow);
  _setColor('se_shadow_color', s.shadow_color);
  _setField('se_shadow_x',     s.shadow_x);
  _setField('se_shadow_y',     s.shadow_y);

  _setField('se_horizontal_position', s.horizontal_position);
  _setField('se_vertical_position',   s.vertical_position);

  _toggleSection('se_box_fields',    s.box);
  _toggleSection('se_shadow_fields', s.shadow);

  document.getElementById('stylePanel').classList.add('open');
}

function closeStyleEditor() {
  document.getElementById('stylePanel').classList.remove('open');
  _editingIdx = null;
}

// ── Field helpers ─────────────────────────────────────────────────────────────

// #RRGGBBAA → { rgb: '#RRGGBB', alpha: 0-255 }
function _splitColor(hex8) {
  const h = hex8.replace('#', '');
  return { rgb: '#' + h.slice(0, 6), alpha: parseInt(h.slice(6, 8), 16) };
}

// '#RRGGBB' + 0-255 → '#RRGGBBAA'
function _joinColor(rgb, alpha) {
  return rgb + Math.round(alpha).toString(16).padStart(2, '0').toUpperCase();
}

function _setField(id, val) {
  const elem = document.getElementById(id);
  if (elem) elem.value = val;
}

function _setCheck(id, val) {
  const elem = document.getElementById(id);
  if (elem) elem.checked = val;
}

function _setColor(baseId, hex8) {
  const { rgb, alpha } = _splitColor(hex8);
  _setField(baseId + '_rgb',   rgb);
  _setField(baseId + '_alpha', alpha);
  _updateAlphaLabel(baseId, alpha);
}

function _updateAlphaLabel(baseId, alpha) {
  const elem = document.getElementById(baseId + '_pct');
  if (elem) elem.textContent = Math.round(alpha / 255 * 100) + '%';
}

function _readColor(baseId) {
  const rgb   = document.getElementById(baseId + '_rgb').value;
  const alpha = parseInt(document.getElementById(baseId + '_alpha').value);
  return _joinColor(rgb, alpha);
}

function _toggleSection(sectionId, visible) {
  const elem = document.getElementById(sectionId);
  if (elem) elem.style.display = visible ? '' : 'none';
}

// ── Write inputs → state ──────────────────────────────────────────────────────

function _commitStyle() {
  if (_editingIdx === null) return;
  const s = state.lines[_editingIdx].style;

  const fontFileVal = document.getElementById('se_font_file').value.trim();
  s.font_file   = fontFileVal || null;
  s.font_size   = parseInt(document.getElementById('se_font_size').value)   || 64;
  s.font_color  = _readColor('se_font_color');

  s.border_width = parseInt(document.getElementById('se_border_width').value) || 0;
  s.border_color = _readColor('se_border_color');

  s.box         = document.getElementById('se_box').checked;
  s.box_color   = _readColor('se_box_color');
  s.box_padding = parseInt(document.getElementById('se_box_padding').value)  || 0;

  s.shadow       = document.getElementById('se_shadow').checked;
  s.shadow_color = _readColor('se_shadow_color');
  s.shadow_x     = parseInt(document.getElementById('se_shadow_x').value)   || 0;
  s.shadow_y     = parseInt(document.getElementById('se_shadow_y').value)   || 0;

  s.horizontal_position = document.getElementById('se_horizontal_position').value;
  s.vertical_position   = document.getElementById('se_vertical_position').value;

  // Live-preview on the overlay if this line is currently displayed
  const t = video.currentTime;
  const active = state.lines
    .filter(l => l.timestamp !== null && l.timestamp <= t)
    .sort((a, b) => b.timestamp - a.timestamp)[0];
  if (active && state.lines.indexOf(active) === _editingIdx) {
    applyStyleToOverlay(s);
  }
}

// ── Wire up inputs ────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('se_close').addEventListener('click', closeStyleEditor);

  document.getElementById('se_reset').addEventListener('click', () => {
    if (_editingIdx === null) return;
    state.lines[_editingIdx].style = { ...DEFAULT_STYLE };
    openStyleEditor(_editingIdx);
  });

  document.getElementById('se_apply_all').addEventListener('click', () => {
    if (_editingIdx === null) return;
    _commitStyle();
    const src = state.lines[_editingIdx].style;
    state.lines.forEach((l, i) => { if (i !== _editingIdx) l.style = { ...src }; });
    showPopUp('Style applied to all lines');
  });

  // Every input / select commits to state immediately
  document.querySelectorAll('#stylePanel input, #stylePanel select').forEach(elem => {
    elem.addEventListener('input', () => {
      if (elem.id.endsWith('_alpha'))  _updateAlphaLabel(elem.id.replace('_alpha', ''), parseInt(elem.value));
      if (elem.id === 'se_box')        _toggleSection('se_box_fields',    elem.checked);
      if (elem.id === 'se_shadow')     _toggleSection('se_shadow_fields', elem.checked);
      _commitStyle();
    });
  });

  // Field tooltips — show on hover over any label with data-tip inside the style panel
  document.getElementById('stylePanel').addEventListener('mouseover', e => {
    const label = e.target.closest('label[data-tip]');
    if (label) showFieldTip(label.dataset.tip, label);
  });
  document.getElementById('stylePanel').addEventListener('mouseout', e => {
    if (e.target.closest('label[data-tip]')) hideFieldTip();
  });
});
