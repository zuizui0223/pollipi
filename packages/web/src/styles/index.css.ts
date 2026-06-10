import { globalStyle } from '@vanilla-extract/css';

globalStyle(':root', {
  vars: {
    '--bg': '#f3f3ec',
    '--card': '#fffef9',
    '--ink': '#102820',
    '--muted': '#617168',
    '--line': '#dce0d4',
    '--leaf': '#217052',
    '--leaf-dark': '#15533b',
    '--warm': '#e2ad45',
    '--stop': '#be5046',
    '--blue': '#2f6f9f',
    '--shadow': '0 12px 34px rgba(22, 43, 33, 0.08)',
  },
});

globalStyle('*', { boxSizing: 'border-box' });

globalStyle('html, body', {
  margin: 0,
  minHeight: '100%',
  background: 'var(--bg)',
  color: 'var(--ink)',
  fontFamily: '-apple-system, BlinkMacSystemFont, "Hiragino Sans", "Yu Gothic", sans-serif',
});

globalStyle('body', {
  padding: `
    calc(env(safe-area-inset-top) + 22px)
    calc(env(safe-area-inset-right) + 22px)
    calc(env(safe-area-inset-bottom) + 20px)
    calc(env(safe-area-inset-left) + 22px)
  `.trim(),
});

globalStyle('button, input, select, textarea', { font: 'inherit' });

globalStyle('button', {
  minHeight: '46px',
  border: '0',
  borderRadius: '14px',
  padding: '0 18px',
  fontSize: '15px',
  fontWeight: '700',
  cursor: 'pointer',
  touchAction: 'manipulation',
});

globalStyle('button:disabled', { cursor: 'default', opacity: 0.6 });

globalStyle('input, select, textarea', {
  border: '1px solid var(--line)',
  borderRadius: '12px',
  background: 'white',
  color: 'var(--ink)',
  padding: '10px 12px',
  fontSize: '15px',
});

globalStyle('textarea', { minHeight: '78px', resize: 'vertical' });

globalStyle('[hidden]', { display: 'none !important' });

globalStyle('h2, h3', { margin: '0 0 8px' });
globalStyle('h2', { fontSize: '23px' });
globalStyle('h3', { fontSize: '17px' });
