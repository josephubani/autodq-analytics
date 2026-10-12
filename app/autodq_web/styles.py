"""Visual system for AutoDQ Studio."""

APP_CSS = r"""
<style>
:root {
  --dq-ink: #eaf6f2;
  --dq-muted: #8fa8a2;
  --dq-panel: rgba(12, 31, 38, 0.82);
  --dq-line: rgba(133, 178, 164, 0.18);
  --dq-green: #2dd4a3;
  --dq-blue: #56a8ff;
}

.stApp {
  background:
    radial-gradient(circle at 82% 8%, rgba(31, 139, 116, 0.17), transparent 28rem),
    radial-gradient(circle at 18% 92%, rgba(48, 105, 180, 0.11), transparent 30rem),
    #071419;
}

[data-testid="stSidebar"] {
  background: rgba(5, 18, 23, 0.97);
  border-right: 1px solid var(--dq-line);
}

[data-testid="stHeader"] { background: transparent; }
[data-testid="stMetric"] {
  background: var(--dq-panel);
  border: 1px solid var(--dq-line);
  border-radius: 16px;
  padding: 0.9rem 1rem;
}

.block-container { max-width: 1480px; padding-top: 1.8rem; }

.dq-brand {
  display: flex;
  align-items: center;
  gap: .75rem;
  margin: .2rem 0 1.25rem;
}
.dq-mark {
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  color: #02130f;
  font-weight: 900;
  background: linear-gradient(135deg, #62f2bd, #2d9fe8);
  box-shadow: 0 10px 32px rgba(45, 212, 163, .2);
}
.dq-brand strong { display: block; font-size: 1.05rem; letter-spacing: -.02em; }
.dq-brand span { color: var(--dq-muted); font-size: .73rem; }

.dq-hero {
  position: relative;
  overflow: hidden;
  padding: clamp(1.6rem, 4vw, 3.5rem);
  border: 1px solid var(--dq-line);
  border-radius: 26px;
  background:
    linear-gradient(125deg, rgba(13, 43, 45, .98), rgba(10, 28, 42, .94));
  box-shadow: 0 30px 90px rgba(0, 0, 0, .28);
  margin-bottom: 1.4rem;
}
.dq-hero::after {
  content: "";
  position: absolute;
  width: 22rem;
  height: 22rem;
  right: -7rem;
  top: -9rem;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(45, 212, 163, .27), transparent 68%);
}
.dq-kicker {
  color: #65e7bd;
  font-size: .75rem;
  font-weight: 800;
  letter-spacing: .14em;
  text-transform: uppercase;
}
.dq-hero h1 {
  max-width: 850px;
  margin: .65rem 0 .75rem;
  color: #f3fbf8;
  font-size: clamp(2.25rem, 5vw, 4.5rem);
  line-height: .98;
  letter-spacing: -.055em;
}
.dq-hero p { max-width: 730px; color: #a8c0bb; font-size: 1.04rem; line-height: 1.65; }

.dq-page-title { margin: 0 0 1.2rem; }
.dq-page-title small {
  display: block;
  color: #55dbb2;
  font-weight: 800;
  letter-spacing: .12em;
  text-transform: uppercase;
  margin-bottom: .35rem;
}
.dq-page-title h1 { margin: 0; font-size: clamp(2rem, 4vw, 3.2rem); letter-spacing: -.045em; }
.dq-page-title p { margin: .45rem 0 0; color: var(--dq-muted); max-width: 760px; }

.dq-card {
  height: 100%;
  padding: 1.15rem 1.2rem;
  border-radius: 17px;
  border: 1px solid var(--dq-line);
  background: var(--dq-panel);
}
.dq-card .eyebrow { color: #62ddb7; font-size: .72rem; font-weight: 800; text-transform: uppercase; letter-spacing: .1em; }
.dq-card h3 { margin: .4rem 0 .45rem; font-size: 1.05rem; }
.dq-card p { margin: 0; color: var(--dq-muted); font-size: .9rem; line-height: 1.55; }

.dq-status {
  display: inline-flex;
  align-items: center;
  gap: .42rem;
  padding: .34rem .62rem;
  border: 1px solid rgba(45, 212, 163, .24);
  border-radius: 999px;
  background: rgba(45, 212, 163, .09);
  color: #76e7c3;
  font-size: .78rem;
  font-weight: 700;
}
.dq-dot { width: 7px; height: 7px; border-radius: 50%; background: #2dd4a3; box-shadow: 0 0 12px #2dd4a3; }
.dq-note { color: var(--dq-muted); font-size: .82rem; line-height: 1.5; }
.dq-divider { height: 1px; background: var(--dq-line); margin: 1rem 0; }

div[data-testid="stButton"] > button,
div[data-testid="stDownloadButton"] > button {
  border-radius: 11px;
  font-weight: 700;
  border-color: rgba(104, 214, 182, .28);
}
div[data-testid="stButton"] > button[kind="primary"] {
  background: linear-gradient(135deg, #27c697, #268ed0);
  border: 0;
  color: #031916;
}

div[data-testid="stDataFrame"] { border: 1px solid var(--dq-line); border-radius: 14px; overflow: hidden; }
code { color: #75e4bd !important; }

@media (max-width: 720px) {
  .block-container { padding: 1rem .85rem 3rem; }
  .dq-hero { border-radius: 20px; }
}
</style>
"""
