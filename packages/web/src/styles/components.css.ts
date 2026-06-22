import { style, globalStyle } from '@vanilla-extract/css';

// ─── Layout ────────────────────────────────────────────────────────────────

export const heroLayout = style({
  display: 'flex',
  justifyContent: 'space-between',
  gap: '18px',
  alignItems: 'flex-start',
  maxWidth: '1180px',
  margin: '0 auto 24px',
});

export const mainLayout = style({
  maxWidth: '1180px',
  margin: '0 auto',
});

export const footerLayout = style({
  maxWidth: '1180px',
  margin: '18px auto 0',
  padding: '0 5px',
  display: 'flex',
  justifyContent: 'space-between',
  gap: '15px',
  fontSize: '13px',
  color: 'var(--muted)',
});

// ─── Typography ────────────────────────────────────────────────────────────

export const eyebrow = style({
  margin: '0 0 8px',
  color: 'var(--leaf)',
  fontSize: '12px',
  fontWeight: '800',
  letterSpacing: '0.14em',
  textTransform: 'uppercase',
});

export const sectionTitle = style({
  margin: '0 0 8px',
  color: 'var(--leaf)',
  fontSize: '12px',
  fontWeight: '800',
  letterSpacing: '0.14em',
  textTransform: 'uppercase',
});

export const cameraLabel = style({
  margin: '0 0 8px',
  color: 'var(--leaf)',
  fontSize: '12px',
  fontWeight: '800',
  letterSpacing: '0.14em',
  textTransform: 'uppercase',
});

export const h1 = style({
  margin: '0 0 8px',
  fontFamily: 'Georgia, "Times New Roman", serif',
  fontSize: 'clamp(42px, 7vw, 66px)',
  fontWeight: '500',
  lineHeight: '1',
});

export const lead = style({
  maxWidth: '640px',
  margin: '0',
  fontSize: '16px',
  lineHeight: '1.65',
  color: 'var(--muted)',
});

export const hint = style({
  margin: '8px 0 0',
  fontSize: '13px',
  lineHeight: '1.5',
  color: 'var(--muted)',
});

export const sensor = style({
  margin: '0',
  fontSize: '13px',
  color: 'var(--muted)',
});

export const cameraMessage = style({
  minHeight: '20px',
  margin: '0 0 15px',
  fontSize: '13px',
  color: 'var(--muted)',
});

export const folderPath = style({
  overflow: 'hidden',
  margin: '0 0 14px',
  fontSize: '12px',
  textOverflow: 'ellipsis',
  whiteSpace: 'nowrap',
  color: 'var(--muted)',
});

// ─── Buttons ───────────────────────────────────────────────────────────────

export const btnPrimary = style({
  background: 'var(--leaf)',
  color: 'white',
  ':active': { background: 'var(--leaf-dark)' },
});

export const btnSecondary = style({
  background: '#e7ebdf',
  color: 'var(--ink)',
});

export const btnGhost = style({
  border: '1px solid var(--line)',
  background: 'var(--card)',
  color: 'var(--leaf)',
});

export const btnDanger = style({
  background: '#f3dfdc',
  color: 'var(--stop)',
});

export const btnMonitor = style({
  border: '1px solid var(--leaf)',
  background: 'transparent',
  color: 'var(--leaf)',
});

export const btnMonitorActive = style({
  background: '#d8efdf',
  color: 'var(--leaf-dark)',
});

export const btnAiMonitor = style({
  border: '1px solid var(--blue)',
  background: 'transparent',
  color: 'var(--blue)',
});

export const btnAiMonitorActive = style({
  background: '#e0edf7',
});

export const btnRemoveCamera = style({
  border: '1px solid var(--line)',
  background: 'transparent',
  color: 'var(--muted)',
});

// ─── Panels ────────────────────────────────────────────────────────────────

export const panel = style({
  border: '1px solid var(--line)',
  borderRadius: '22px',
  background: 'var(--card)',
  boxShadow: 'var(--shadow)',
});

export const controlPanel = style([
  panel,
  {
    display: 'grid',
    gridTemplateColumns: 'minmax(220px, 0.75fr) minmax(260px, 1fr) auto',
    gap: '20px',
    alignItems: 'start',
    padding: '22px 24px',
    marginBottom: '22px',
    '@media': {
      '(max-width: 960px)': { gridTemplateColumns: '1fr' },
    },
  },
]);

export const devicesPanel = style([
  panel,
  {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: '18px',
    padding: '20px 24px',
    marginBottom: '22px',
    '@media': {
      '(max-width: 740px)': { flexDirection: 'column', alignItems: 'stretch' },
    },
  },
]);

export const galleryPanel = style([panel, { marginTop: '22px', padding: '22px' }]);
export const eventReviewPanel = style([panel, { marginTop: '22px', padding: '22px' }]);
export const trainingPanel = style([panel, { marginTop: '22px', padding: '22px' }]);

// ─── Field Mode Panel ──────────────────────────────────────────────────────

export const intervalInputWrap = style({
  display: 'inline-flex',
  gap: '10px',
  alignItems: 'baseline',
});

export const intervalInputField = style({
  width: '120px',
  padding: '9px 12px',
  fontSize: '30px',
  fontWeight: '700',
});

export const autoToggle = style({
  display: 'flex',
  gap: '9px',
  alignItems: 'center',
  borderRadius: '12px',
  background: '#f4f4ee',
  padding: '10px 12px',
  fontWeight: '700',
});

export const autoToggleInput = style({
  width: '20px',
  height: '20px',
  accentColor: 'var(--leaf)',
});

export const fieldBasicGrid = style({
  display: 'grid',
  gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
  gap: '10px',
});

export const advancedFields = style({
  border: '1px solid var(--line)',
  borderRadius: '14px',
  background: '#f8f8f0',
  padding: '10px 12px',
  gridColumn: '1 / -1',
});

export const advancedFieldsSummary = style({
  cursor: 'pointer',
  color: 'var(--leaf)',
  fontWeight: '800',
});

export const advancedGrid = style({
  display: 'grid',
  gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
  gap: '10px',
  marginTop: '10px',
});

export const advancedGridLabel = style({
  display: 'grid',
  gap: '5px',
  color: 'var(--muted)',
  fontSize: '13px',
});

export const advancedGridWide = style({ gridColumn: '1 / -1' });

export const advancedModes = style({
  display: 'grid',
  gap: '8px',
  marginTop: '12px',
});

export const groupActions = style({
  display: 'flex',
  gap: '9px',
  flexWrap: 'wrap',
});

// ─── Device form ───────────────────────────────────────────────────────────

export const deviceForm = style({
  display: 'flex',
  gap: '9px',
  flexWrap: 'wrap',
  width: 'min(480px, 100%)',
  '@media': {
    '(max-width: 740px)': { flexDirection: 'column' },
  },
});

export const deviceFormInput = style({ flex: '1', minWidth: '190px' });

// ─── Camera Grid ───────────────────────────────────────────────────────────

export const cameraGrid = style({
  display: 'grid',
  gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
  gap: '18px',
  '@media': {
    '(max-width: 960px)': { gridTemplateColumns: '1fr' },
  },
});

export const cameraEmpty = style({
  gridColumn: '1 / -1',
  margin: '0',
  border: '1px dashed var(--line)',
  borderRadius: '18px',
  background: 'var(--card)',
  color: 'var(--muted)',
  padding: '36px 18px',
  textAlign: 'center',
});

// ─── Camera Card ───────────────────────────────────────────────────────────

export const cameraCard = style({
  overflow: 'hidden',
  border: '1px solid var(--line)',
  borderRadius: '22px',
  background: 'var(--card)',
  padding: '20px',
  boxShadow: 'var(--shadow)',
});

export const cameraCardNoir = style({ filter: 'sepia(0.15)' });

export const cameraHeader = style({
  display: 'flex',
  justifyContent: 'space-between',
  gap: '12px',
  marginBottom: '12px',
});

export const pill = style({
  height: 'fit-content',
  borderRadius: '999px',
  padding: '7px 11px',
  fontSize: '12px',
  fontWeight: '800',
});

export const pillRunning = style({ background: '#d8efdf', color: 'var(--leaf)' });
export const pillStopped = style({ background: '#ecece6', color: '#687067' });
export const pillOffline = style({ background: '#f3dfdc', color: 'var(--stop)' });

export const cameraBadgesWrap = style({
  display: 'flex',
  gap: '6px',
  flexWrap: 'wrap',
  margin: '8px 0 12px',
});

export const cameraBadge = style({
  height: 'fit-content',
  borderRadius: '999px',
  padding: '7px 11px',
  fontSize: '12px',
  fontWeight: '800',
  background: '#f1f2e9',
  color: 'var(--muted)',
});

// ─── Image Frame ───────────────────────────────────────────────────────────

export const imageFrame = style({
  position: 'relative',
  display: 'grid',
  placeItems: 'center',
  width: '100%',
  aspectRatio: '16 / 9',
  overflow: 'hidden',
  borderRadius: '15px',
  background: '#dde2d7',
  marginBottom: '14px',
  touchAction: 'none',
});

export const imageFrameImg = style({
  display: 'none',
  width: '100%',
  height: '100%',
  objectFit: 'cover',
  userSelect: 'none',
});

export const imageFrameImgReady = style({ display: 'block' });

export const imageFrameEmpty = style({
  margin: '0',
  color: 'var(--muted)',
  fontSize: '14px',
});

export const roiBox = style({
  position: 'absolute',
  display: 'none',
  border: '3px solid #ffcc33',
  borderRadius: '6px',
  background: 'rgba(255, 204, 51, 0.16)',
  boxShadow: '0 0 0 9999px rgba(0, 0, 0, 0.12)',
  pointerEvents: 'none',
  zIndex: 4,
});

export const roiBoxVisible = style({ display: 'block' });

export const monitorRoiBox = style([
  roiBox,
  {
    borderColor: '#49d37a',
    background: 'rgba(73, 211, 122, 0.14)',
  },
]);

// ─── ROI Panel ─────────────────────────────────────────────────────────────

export const roiPanel = style({
  border: '1px solid var(--line)',
  borderRadius: '16px',
  background: '#fafaf3',
  padding: '12px',
  marginBottom: '14px',
});

export const workflowStatus = style({
  display: 'flex',
  flexWrap: 'wrap',
  gap: '10px',
  marginBottom: '10px',
});

export const workflowStatusSpan = style({
  border: '1px solid var(--line)',
  borderRadius: '999px',
  background: '#fffdf2',
  color: 'var(--leaf)',
  fontWeight: '800',
  padding: '8px 12px',
});

export const roiActions = style({
  display: 'flex',
  flexWrap: 'wrap',
  gap: '10px',
  marginBottom: '8px',
});

export const roiStatus = style({
  margin: '7px 0',
  color: 'var(--muted)',
  fontSize: '13px',
  lineHeight: '1.45',
});

export const roiTrackToggle = style({
  display: 'flex',
  gap: '9px',
  alignItems: 'center',
  borderRadius: '12px',
  background: '#f4f4ee',
  padding: '10px 12px',
  fontWeight: '700',
});

export const roiAdvanced = style({
  border: '1px solid var(--line)',
  borderRadius: '14px',
  background: '#f8f8f0',
  padding: '10px 12px',
});

export const roiAdvancedSummary = style({
  cursor: 'pointer',
  color: 'var(--leaf)',
  fontWeight: '800',
});

export const roiDrawer = style({ marginTop: '10px' });

export const roiPreviewWrap = style({
  position: 'relative',
  display: 'grid',
  placeItems: 'center',
  width: '100%',
  aspectRatio: '16 / 9',
  overflow: 'hidden',
  borderRadius: '15px',
  background: '#dde2d7',
  marginBottom: '14px',
  touchAction: 'none',
  cursor: 'crosshair',
});

export const roiPreviewImg = style({
  display: 'none',
  width: '100%',
  height: '100%',
  objectFit: 'cover',
  userSelect: 'none',
  pointerEvents: 'none',
});

export const roiPreviewImgReady = style({ display: 'block' });

export const roiEditorActions = style({
  display: 'grid',
  gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
  gap: '10px',
});

// ─── Metrics ───────────────────────────────────────────────────────────────

export const metrics = style({
  display: 'grid',
  gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
  gap: '8px',
  margin: '0 0 15px',
});

export const metricsCell = style({
  borderRadius: '11px',
  background: '#f4f4ee',
  padding: '10px',
});

export const metricsDt = style({
  color: 'var(--muted)',
  fontSize: '11px',
});

export const metricsDd = style({
  overflow: 'hidden',
  margin: '5px 0 0',
  fontSize: '15px',
  fontWeight: '800',
  textOverflow: 'ellipsis',
  whiteSpace: 'nowrap',
});

export const cardActions = style({
  display: 'grid',
  gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
  gap: '10px',
  '@media': {
    '(max-width: 740px)': { gridTemplateColumns: '1fr' },
  },
});

// ─── Gallery ───────────────────────────────────────────────────────────────

export const galleryHeader = style({
  display: 'flex',
  justifyContent: 'space-between',
  gap: '18px',
  marginBottom: '16px',
  '@media': {
    '(max-width: 740px)': { flexDirection: 'column', alignItems: 'stretch' },
  },
});

export const gallerySwitch = style({
  display: 'flex',
  gap: '9px',
  flexWrap: 'wrap',
  alignItems: 'flex-start',
  borderRadius: '14px',
  background: '#f1f2e9',
  padding: '5px',
});

export const collectionSwitch = style({
  display: 'flex',
  gap: '9px',
  flexWrap: 'wrap',
  alignItems: 'flex-start',
  borderRadius: '14px',
  background: '#f1f2e9',
  padding: '5px',
});

export const galleryTab = style({
  minHeight: '42px',
  background: 'transparent',
  color: 'var(--muted)',
  fontSize: '14px',
  padding: '0 14px',
});

export const galleryTabSelected = style({
  background: 'var(--leaf)',
  color: 'white',
});

export const collectionTab = style({
  minHeight: '42px',
  background: 'transparent',
  color: 'var(--muted)',
  fontSize: '14px',
  padding: '0 14px',
});

export const collectionTabSelected = style({
  background: 'var(--leaf)',
  color: 'white',
});

export const folderSummary = style({
  display: 'flex',
  gap: '14px',
  alignItems: 'center',
  borderBottom: '1px solid var(--line)',
  paddingBottom: '14px',
  marginBottom: '15px',
  color: 'var(--muted)',
  fontSize: '14px',
  flexWrap: 'wrap',
});

export const galleryGrid = style({
  display: 'grid',
  gridTemplateColumns: 'repeat(4, minmax(0, 1fr))',
  gap: '12px',
  '@media': {
    '(max-width: 960px)': { gridTemplateColumns: 'repeat(2, minmax(0, 1fr))' },
  },
});

export const galleryEmpty = style({
  gridColumn: '1 / -1',
  margin: '0',
  borderRadius: '13px',
  background: '#f4f4ee',
  color: 'var(--muted)',
  padding: '28px 18px',
  textAlign: 'center',
});

export const galleryItem = style({
  overflow: 'hidden',
  border: '1px solid var(--line)',
  borderRadius: '14px',
  background: 'white',
});

export const galleryItemImg = style({
  display: 'block',
  width: '100%',
  aspectRatio: '4 / 3',
  background: '#dde2d7',
  objectFit: 'cover',
});

export const galleryDetail = style({
  display: 'grid',
  gap: '4px',
  padding: '9px 10px 7px',
  color: 'var(--muted)',
  fontSize: '12px',
});

export const labelBadge = style({
  display: 'inline-flex',
  width: 'fit-content',
  margin: '0 10px 10px',
  borderRadius: '999px',
  padding: '4px 9px',
  fontSize: '12px',
  fontWeight: '700',
});

export const labelPositive = style({ background: '#d8efdf', color: 'var(--leaf-dark)' });
export const labelNegative = style({ background: '#f0e9dc', color: '#745a28' });
export const labelUnclear = style({ background: '#eef0f4', color: '#4c5668' });

export const reviewActions = style({
  display: 'grid',
  gridTemplateColumns: '1fr 1fr',
  gap: '8px',
  padding: '0 10px 10px',
});

export const downloadLink = style({
  display: 'inline-flex',
  alignItems: 'center',
  minHeight: '38px',
  fontSize: '14px',
  color: 'var(--leaf)',
  textDecoration: 'none',
});

export const downloadLinkDisabled = style({
  pointerEvents: 'none',
  opacity: 0.55,
});

export const deleteImageBtn = style({
  minHeight: '38px',
  fontSize: '14px',
  background: '#fff5f3',
  color: 'var(--stop)',
  border: 0,
  borderRadius: '8px',
  width: '100%',
  marginBottom: '4px',
  cursor: 'pointer',
});

// ─── Events ────────────────────────────────────────────────────────────────

export const eventGrid = style({
  display: 'grid',
  gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
  gap: '12px',
  '@media': {
    '(max-width: 960px)': { gridTemplateColumns: '1fr' },
  },
});

export const eventBulkBar = style({
  display: 'flex',
  gap: '8px',
  alignItems: 'center',
  flexWrap: 'wrap',
  margin: '0 0 14px',
});

export const eventDeleteOption = style({
  display: 'inline-flex',
  alignItems: 'center',
  gap: '6px',
  minHeight: '38px',
  color: 'var(--muted)',
  fontSize: '13px',
});

export const eventDeleteMessage = style({
  margin: '0 0 14px',
  borderRadius: '8px',
  background: '#f4f4ee',
  color: 'var(--ink)',
  padding: '10px 12px',
  fontSize: '13px',
});

export const eventItem = style({
  overflow: 'hidden',
  border: '1px solid var(--line)',
  borderRadius: '14px',
  background: 'white',
});

export const eventSelectLabel = style({
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
  padding: '8px 10px',
  borderBottom: '1px solid var(--line)',
  color: 'var(--muted)',
  fontSize: '13px',
});

export const eventMeta = style({
  display: 'grid',
  gap: '4px',
  padding: '9px 10px 7px',
  color: 'var(--muted)',
  fontSize: '12px',
});

export const categoryBadge = style({
  display: 'inline-flex',
  width: 'fit-content',
  borderRadius: '999px',
  fontWeight: '800',
  padding: '5px 9px',
});

export const categoryPositive = style({ background: '#d8efdf', color: 'var(--leaf-dark)' });
export const categoryNegative = style({ background: '#f0e9dc', color: '#745a28' });
export const categoryUnclear = style({ background: '#eef0f4', color: '#4c5668' });

export const eventReviewForm = style({
  display: 'grid',
  gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
  gap: '10px',
  padding: '10px',
  borderTop: '1px solid var(--line)',
});

export const eventReviewActions = style({
  gridColumn: '1 / -1',
  display: 'grid',
  gridTemplateColumns: 'repeat(3, minmax(0, 1fr))',
  gap: '8px',
});

export const quickLabelPositive = style({ background: '#d8efdf', color: 'var(--leaf-dark)' });
export const quickLabelNegative = style({ background: '#f0e9dc', color: '#745a28' });
export const quickLabelUnclear = style({ background: '#eef0f4', color: '#4c5668' });
export const quickLabelSelected = style({ outline: '3px solid var(--leaf)', outlineOffset: '2px' });

// ─── Training ──────────────────────────────────────────────────────────────

export const trainingMetrics = style({
  display: 'grid',
  gridTemplateColumns: 'repeat(4, minmax(0, 1fr))',
  gap: '8px',
  marginBottom: '14px',
  '@media': {
    '(max-width: 740px)': { gridTemplateColumns: '1fr' },
  },
});

export const trainingMetricsCell = style({
  borderRadius: '11px',
  background: '#f4f4ee',
  padding: '10px',
});

export const galleryItemSelected = style({
  outline: '4px solid var(--leaf)',
  outlineOffset: '-4px',
});

export const eventItemSelected = style({
  outline: '4px solid var(--leaf)',
  outlineOffset: '-4px',
});

