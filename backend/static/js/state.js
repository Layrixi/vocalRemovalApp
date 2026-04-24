//  STATE 

// Mirrors Python's TextStyle dataclass defaults.
// Overwritten on load by /api/style/default — kept here as safe fallback.
let DEFAULT_STYLE = {
  font_file:           null,
  font_size:           64,
  font_color:          '#FFFFFFFF',
  box:                 false,
  box_color:           '#000000FF',
  box_padding:         1,
  shadow:              false,
  shadow_color:        '#000000FF',
  shadow_offset:       1,
  outline_width:       1,
  outline_color:       '#000000FF',
  vertical_position:   'center',
  horizontal_position: 'center',
  bold:                false,
  italic:              false,
  //those two accept only -1 or 0 at the backend. -1=True, 0=False
  underline:           false,
  strikeout:           false,
  // _____________
  letter_spacing:      0, //px
  angle:               0, //degrees
  encoding:            1,   // ASS encoding value; 1 = OS default (most cases UTF-8)

};

const state = {
  lines: [],         // { text, timestamp: null|seconds }
  activeLineIdx: null,
  videoDuration: 0,
  uploadedVideoFilename: null,
  speeds: [0.25, 0.5, 0.75, 1, 1.25, 1.5, 2],
  speedIdx: 3,
  wrapConfig: { font_size: 64, char_width_ratio: 0.5, play_res_x: 1920, play_res_y: 1080 },
};

//  ELEMENTS 
const video            = document.getElementById('mainVideo');
const playBtn          = document.getElementById('playBtn');
const timeDisplay      = document.getElementById('timeDisplay');
const timelineWrap     = document.getElementById('timelineWrap');
const timelineProgress = document.getElementById('timelineProgress');
const playhead         = document.getElementById('playhead');
const hoverTime        = document.getElementById('hoverTime');
const lyricsList       = document.getElementById('lyricsList');
const lyricsRaw        = document.getElementById('lyricsRaw');
const lineCount        = document.getElementById('lineCount');
const activePill       = document.getElementById('activePill');
const instructionText  = document.getElementById('instructionText');
const overlayText      = document.getElementById('overlayText');
const syncFlash        = document.getElementById('syncFlash');
const speedBtn         = document.getElementById('speedBtn');
const tickCanvas       = document.getElementById('tickCanvas');
const videoDropZone    = document.getElementById('videoDropZone');
const videoWrapper     = document.getElementById('videoWrapper');
const syncedCount      = document.getElementById('syncedCount');
const remainingCount   = document.getElementById('remainingCount');
