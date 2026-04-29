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


//applies style to line shown on the overlay
function applyStyleToOverlay(style) {
  const elem      = overlayText;
  const overlay = document.querySelector('.video-lyrics-overlay');

  const fontName = style.font_file
    ? style.font_file.replace(/\\/g, '/').split('/').pop().replace(/\.[^.]+$/, '')
    : 'Arial';

  elem.style.fontFamily       = `"${fontName}", sans-serif`;
  elem.style.color            = style.font_color;
  elem.style.webkitTextStroke = style.outline_width > 0
    ? `${style.outline_width}px ${style.outline_color}` : '0';

  elem.style.fontWeight      = style.bold ? 'bold' : 'normal';
  elem.style.fontStyle       = style.italic ? 'italic' : 'normal';
  elem.style.textDecoration  = [
    style.underline ? 'underline' : '',
    style.strikeout ? 'line-through' : ''
  ].filter(s => s).join(' ');
  elem.style.textDecorationColor = style.font_color;
  elem.style.letterSpacing   = style.letter_spacing + 'px';
  elem.style.transform       = `rotate(${style.angle}deg)`;

  if (style.box) {
    elem.style.backgroundColor = style.box_color;
    elem.style.padding         = style.box_padding + 'px';
  } else {
    elem.style.backgroundColor = 'transparent';
    elem.style.padding         = '0';
  }

  elem.style.textShadow = style.shadow
    ? `${style.shadow_offset}px ${style.shadow_offset}px 0 ${_hex8ToCssColor(style.shadow_color)}`
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
  _setCheck('se_bold',        s.bold);
  _setCheck('se_italic',      s.italic);
  _setCheck('se_underline',   s.underline);
  _setCheck('se_strikeout',   s.strikeout);
  _setField('se_letter_spacing', s.letter_spacing);
  _setField('se_angle',       s.angle);
  _setField('se_encoding',    s.encoding);
  const nonDefaultEncoding = s.encoding !== 1;
  _toggleSection('se_encoding_row', nonDefaultEncoding);
  document.getElementById('se_encoding_toggle').textContent = nonDefaultEncoding ? '▾ Advanced' : '▸ Advanced';

  _setField('se_outline_width', s.outline_width);
  _setColor('se_outline_color', s.outline_color);

  _setCheck('se_box',          s.box);
  _setColor('se_box_color',    s.box_color);
  _setField('se_box_padding',  s.box_padding);

  _setCheck('se_shadow',       s.shadow);
  _setColor('se_shadow_color', s.shadow_color);
  _setField('se_shadow_offset', s.shadow_offset);

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

function _hex8ToCssColor(hex8) {
  const h = hex8.replace('#', '');
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  const a = (parseInt(h.slice(6, 8), 16) / 255).toFixed(3);
  return `rgba(${r}, ${g}, ${b}, ${a})`;
}

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

function _toggleEncodingRow() {
  const row    = document.getElementById('se_encoding_row');
  const toggle = document.getElementById('se_encoding_toggle');
  const visible = row.style.display === 'none';
  row.style.display    = visible ? '' : 'none';
  toggle.textContent   = visible ? '▾ Advanced' : '▸ Advanced';
}

// ── Write inputs → state ──────────────────────────────────────────────────────

function _commitStyle() {
  if (_editingIdx === null) return;
  const s = state.lines[_editingIdx].style;

  const prevWrapVals = _getWrapValues(s);

  const fontFileVal = document.getElementById('se_font_file').value.trim();
  s.font_file   = fontFileVal || null;
  s.font_size   = parseInt(document.getElementById('se_font_size').value)   || 64;
  s.font_color  = _readColor('se_font_color');
  s.bold        = document.getElementById('se_bold').checked;
  s.italic      = document.getElementById('se_italic').checked;
  s.underline   = document.getElementById('se_underline').checked;
  s.strikeout   = document.getElementById('se_strikeout').checked;

  s.letter_spacing = parseInt(document.getElementById('se_letter_spacing').value) || 0;
  s.angle       = parseInt(document.getElementById('se_angle').value) || 0;
  s.encoding    = parseInt(document.getElementById('se_encoding').value) || 1;

  s.outline_width = parseInt(document.getElementById('se_outline_width').value) || 0;
  s.outline_color = _readColor('se_outline_color');

  s.box         = document.getElementById('se_box').checked;
  s.box_color   = _readColor('se_box_color');
  s.box_padding = parseInt(document.getElementById('se_box_padding').value)  || 0;

  s.shadow        = document.getElementById('se_shadow').checked;
  s.shadow_color  = _readColor('se_shadow_color');
  s.shadow_offset = parseInt(document.getElementById('se_shadow_offset').value) || 0;

  s.horizontal_position = document.getElementById('se_horizontal_position').value;
  s.vertical_position   = document.getElementById('se_vertical_position').value;
  s.encoding = parseInt(document.getElementById('se_encoding').value) || 1;

  // Re-wrap if any property that affects text layout changed
  if (_isRewrapNeeded(prevWrapVals, s)) {
    wrapTextLine(state.lines[_editingIdx].text, s).then(lines => {
      if (lines && lines.length > 0) {
        state.lines[_editingIdx].wrappedText = lines;
      }
      updateOverlayAndHighlight();
    });
  } else {
    updateOverlayAndHighlight();
  }
}


// ── Wire up inputs ────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('se_close').addEventListener('click', closeStyleEditor);
  document.getElementById('se_reset').addEventListener('click', () => {
    if (_editingIdx === null) return;
    const prevWrapVals = _getWrapValues(state.lines[_editingIdx].style);
    state.lines[_editingIdx].style = { ...DEFAULT_STYLE };
    openStyleEditor(_editingIdx);
    if (_isRewrapNeeded(prevWrapVals, state.lines[_editingIdx].style)) {
      const line = state.lines[_editingIdx];
      wrapTextLine(line.text, line.style).then(lines => {
        if (lines) line.wrappedText = lines;
        updateOverlayAndHighlight();
      });
    } else {
      updateOverlayAndHighlight();
    }
  });

  document.getElementById('se_apply_all').addEventListener('click', () => {
    if (_editingIdx === null) return;
    _commitStyle();
    const src = state.lines[_editingIdx].style;
    const linesToWrap = state.lines.filter((l, i) =>
      i !== _editingIdx && _isRewrapNeeded(_getWrapValues(l.style), _getWrapValues(src))
    );
    state.lines.forEach((l, i) => { if (i !== _editingIdx) l.style = { ...src }; });
    Promise.all(
      linesToWrap
        .map(line =>
          wrapTextLine(line.text, line.style).then(lines => {
            if (lines) line.wrappedText = lines;
          }).then(() => updateOverlayAndHighlight())
        )
    );
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
