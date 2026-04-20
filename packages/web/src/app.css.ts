import { style } from "@vanilla-extract/css";

export const appShell = style({
  minHeight: "100vh",
  display: "grid",
  placeItems: "center",
  padding: "24px",
  background:
    "radial-gradient(circle at top, rgb(219 234 254), rgb(248 250 252) 50%, rgb(226 232 240))",
  fontFamily: '"IBM Plex Sans", "Segoe UI", sans-serif',
});

export const card = style({
  width: "min(420px, 100%)",
  padding: "24px",
  borderRadius: "20px",
  background: "rgb(255 255 255 / 0.82)",
  boxShadow: "0 18px 60px rgb(15 23 42 / 0.12)",
  backdropFilter: "blur(12px)",
});

export const label = style({
  margin: 0,
  fontSize: "12px",
  textTransform: "uppercase",
  letterSpacing: "0.16em",
  color: "rgb(71 85 105)",
});

export const title = style({
  margin: "12px 0 8px",
  fontSize: "32px",
  lineHeight: 1.1,
  color: "rgb(15 23 42)",
});

export const value = style({
  margin: 0,
  fontSize: "16px",
  color: "rgb(51 65 85)",
});
