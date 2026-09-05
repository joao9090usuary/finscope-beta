"""Sistema visual compartilhado da área autenticada do Revo."""

from __future__ import annotations

from datetime import date
from html import escape
from typing import Iterable, Mapping

import streamlit as st


THEMES = {
    "dark": {
        "canvas": "#07111f", "sidebar": "#061324", "surface": "#0c192b",
        "surface_strong": "#102038", "surface_soft": "rgba(14,29,49,.78)",
        "border": "rgba(148,163,184,.18)", "border_strong": "rgba(148,163,184,.31)",
        "text": "#f4f7fb", "muted": "#9dacc0", "subtle": "#708199",
        "input": "#0e1d31", "grid": "#2a3a50", "shadow": "rgba(2,6,23,.24)",
    },
    "light": {
        "canvas": "#f3f6fb", "sidebar": "#ffffff", "surface": "#ffffff",
        "surface_strong": "#f8fafc", "surface_soft": "rgba(255,255,255,.94)",
        "border": "rgba(51,65,85,.14)", "border_strong": "rgba(51,65,85,.24)",
        "text": "#102037", "muted": "#607087", "subtle": "#8290a3",
        "input": "#f8fafc", "grid": "#d8e1ec", "shadow": "rgba(15,23,42,.08)",
    },
}

ACCENTS = {
    "green": "#34d399", "red": "#ff6b5f", "blue": "#5b8ff9",
    "violet": "#665cff", "amber": "#fbbf24", "cyan": "#39c4df",
}

APP_STYLES = r"""
<style>
*,*::before,*::after{box-sizing:border-box}
html{scroll-behavior:smooth}
html,body,#root,[data-testid="stApp"],[data-testid="stAppViewContainer"],[data-testid="stMain"]{
 width:100%!important;max-width:100%!important;min-height:100%!important}
html,body,[data-testid="stAppViewContainer"],[data-testid="stMain"]{overflow-x:clip!important}
[data-testid="stAppViewContainer"]{
 background:radial-gradient(circle at 78% -20%,rgba(91,143,249,.07),transparent 34rem),var(--fs-canvas)!important;
 color:var(--fs-text)!important;transition:background-color 180ms ease,color 180ms ease}
section.main,.stMain,[data-testid="stMain"],[data-testid="stMain"]>div,[data-testid="stMainBlockContainer"],.stMainBlockContainer,.block-container{
 width:100%!important;max-width: none!important;margin-left:0!important;margin-right:0!important}
[data-testid="stMainBlockContainer"],.stMainBlockContainer,.block-container{
 padding:4.2rem clamp(1rem,2vw,2rem) 2.25rem!important}
[data-testid="stMainBlockContainer"]>[data-testid="stVerticalBlock"]{gap:.9rem!important}
[data-testid="stMainBlockContainer"]>[data-testid="stVerticalBlock"]>*{
 animation:fs-section-enter 420ms var(--fs-ease) both}
[data-testid="stMainBlockContainer"]>[data-testid="stVerticalBlock"]>*:nth-child(2){animation-delay:35ms}
[data-testid="stMainBlockContainer"]>[data-testid="stVerticalBlock"]>*:nth-child(3){animation-delay:70ms}
[data-testid="stMainBlockContainer"]>[data-testid="stVerticalBlock"]>*:nth-child(4){animation-delay:105ms}
[data-testid="stHeader"]{height:3.2rem!important;background:color-mix(in srgb,var(--fs-canvas) 88%,transparent)!important;
 border-bottom:1px solid var(--fs-border)!important;backdrop-filter:blur(16px) saturate(130%)}
[data-testid="stHeader"] [data-testid="stToolbar"]{opacity:.86}
[data-testid="stAppDeployButton"],[data-testid="stMainMenu"]{display:none!important}
[data-testid="stDecoration"],[data-testid="stStatusWidget"],footer{display:none!important}

[data-testid="stSidebar"]{width:14rem!important;min-width:14rem!important;border-right:1px solid var(--fs-border)!important;
 background:radial-gradient(circle at 0 0,rgba(91,143,249,.09),transparent 20rem),var(--fs-sidebar)!important;
 box-shadow:8px 0 30px var(--fs-shadow);transition:width 210ms var(--fs-ease),min-width 210ms var(--fs-ease),background-color 180ms ease}
[data-testid="stSidebar"][aria-expanded="false"]{width:0!important;min-width:0!important;max-width:0!important;border-right:0!important;box-shadow:none!important}
[data-testid="stSidebar"]>div:first-child{padding-top:.85rem}
[data-testid="stSidebarContent"]{padding:.25rem .7rem 1rem!important}
[data-testid="stSidebarUserContent"]>[data-testid="stVerticalBlock"]{min-height:calc(100dvh - 4.2rem);display:flex!important;flex-direction:column!important;gap:.24rem!important}
[data-testid="stSidebarNav"]{padding-top:.2rem}
[data-testid="stSidebarNav"] a,[data-testid="stSidebarNav"] button{min-height:2.7rem;margin:.08rem 0;border-radius:7px!important;
 color:var(--fs-muted)!important;font-weight:540!important;transition:color 150ms ease,background-color 150ms ease,transform 150ms ease}
[data-testid="stSidebarNav"] a:hover,[data-testid="stSidebarNav"] button:hover{color:var(--fs-text)!important;
 background:color-mix(in srgb,var(--fs-blue) 10%,transparent)!important;transform:translateX(2px)}
[data-testid="stSidebarNav"] a[aria-current="page"]{color:var(--fs-text)!important;
 background:linear-gradient(90deg,rgba(54,109,239,.25),rgba(102,92,255,.15))!important;
 box-shadow:inset 2px 0 0 var(--fs-blue),inset 0 0 0 1px rgba(91,143,249,.14)}
[data-testid="stSidebarNav"] [data-testid="stNavSectionHeader"]{margin-top:.65rem;color:var(--fs-subtle)!important;
 font-size:.69rem!important;font-weight:720!important;letter-spacing:.09em;text-transform:uppercase}
[data-testid="stSidebar"] [data-testid="stPageLink"] a{min-height:2.72rem;margin:.05rem 0;padding:.55rem .68rem!important;
 border:1px solid transparent;border-radius:7px!important;color:var(--fs-muted)!important;font-weight:560!important;
 transition:color 150ms ease,background-color 150ms ease,transform 150ms ease,border-color 150ms ease}
[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover{color:var(--fs-text)!important;background:color-mix(in srgb,var(--fs-blue) 10%,transparent)!important;transform:translateX(2px)}
[data-testid="stSidebar"] [data-testid="stPageLink"] a p,[data-testid="stSidebar"] [data-testid="stPageLink"] a [data-testid="stIconMaterial"]{color:var(--fs-muted)!important}
[data-testid="stSidebar"] [data-testid="stPageLink"] a[aria-current="page"]{color:var(--fs-text)!important;
 background:linear-gradient(90deg,rgba(54,109,239,.25),rgba(102,92,255,.15))!important;
 border-color:rgba(91,143,249,.16);box-shadow:inset 2px 0 0 var(--fs-blue)}
[data-testid="stSidebar"] [data-testid="stPageLink"] a[aria-current="page"] p,
[data-testid="stSidebar"] [data-testid="stPageLink"] a[aria-current="page"] [data-testid="stIconMaterial"]{color:var(--fs-text)!important}
.fs-nav-section{margin:.72rem .65rem .2rem;color:var(--fs-subtle);font-size:.64rem;font-weight:740;letter-spacing:.105em;text-transform:uppercase}
[data-testid="stSidebarCollapsedControl"]{position:fixed!important;top:.42rem!important;left:.55rem!important;z-index:1002!important}
[data-testid="stSidebarCollapsedControl"] button,[data-testid="stSidebarCollapseButton"] button{width:2.35rem!important;height:2.35rem!important;
 border:1px solid var(--fs-border)!important;border-radius:7px!important;background:var(--fs-surface-soft)!important;
 color:var(--fs-text)!important;box-shadow:0 8px 22px var(--fs-shadow)!important;backdrop-filter:blur(15px)}
[data-testid="stSidebarCollapsedControl"] button [data-testid="stIconMaterial"],[data-testid="stSidebarCollapseButton"] button [data-testid="stIconMaterial"]{color:var(--fs-text)!important}

[data-testid="stMain"] h1,[data-testid="stMain"] h2,[data-testid="stMain"] h3,[data-testid="stMain"] h4{
 color:var(--fs-text)!important;letter-spacing:-.032em}
.fs-page-header{display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:start;gap:1.5rem;min-height:4.75rem;
 padding:.1rem 0 .75rem;animation:fs-enter 320ms var(--fs-ease) both}
.fs-page-header__main{min-width:0}.fs-page-header__eyebrow{display:block;margin-bottom:.2rem;color:var(--fs-blue);
 font-size:.68rem;font-weight:760;letter-spacing:.105em;text-transform:uppercase}
.fs-page-header h1{margin:0!important;color:var(--fs-text);font-family:Manrope,Inter,system-ui,sans-serif;
 font-size:clamp(1.72rem,2.3vw,2.35rem)!important;font-weight:720;line-height:1.08}
.fs-page-header__highlight{background:linear-gradient(105deg,#059669,#34d399 62%,#86efac);background-clip:text;
 -webkit-background-clip:text;color:transparent;-webkit-text-fill-color:transparent}
.fs-page-header p{max-width:52rem;margin:.35rem 0 0;color:var(--fs-muted);font-size:.9rem;line-height:1.5}
.fs-page-header__utility{display:flex;align-items:center;gap:.72rem;padding-top:.1rem;color:var(--fs-muted);font-size:.76rem;white-space:nowrap}
.fs-page-header__avatar{display:grid;place-items:center;width:2rem;height:2rem;border-radius:50%;background:linear-gradient(135deg,var(--fs-blue),var(--fs-violet));
 color:white;font-size:.7rem;font-weight:760}.fs-page-header__divider{width:1px;height:1.75rem;background:var(--fs-border)}
.fs-section-label{margin:1rem 0 .05rem;color:var(--fs-muted);font-size:.69rem;font-weight:720;letter-spacing:.085em;text-transform:uppercase}

.fs-kpi-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.85rem;margin:.05rem 0 .25rem}
.fs-kpi-card{position:relative;display:grid;grid-template-columns:minmax(0,1fr) 3.15rem;align-items:center;min-height:8.15rem;
 padding:1rem 1.05rem;overflow:hidden;border:1px solid var(--fs-border);border-radius:var(--fs-radius);
 background:linear-gradient(145deg,color-mix(in srgb,var(--fs-surface-strong) 88%,transparent),var(--fs-surface));
 box-shadow:0 12px 30px var(--fs-shadow);animation:fs-card-enter 520ms var(--fs-ease) both;
 transition:transform 180ms var(--fs-ease),border-color 180ms ease,background-color 180ms ease,box-shadow 180ms ease}
.fs-kpi-card:nth-child(2){animation-delay:55ms}.fs-kpi-card:nth-child(3){animation-delay:110ms}.fs-kpi-card:nth-child(4){animation-delay:165ms}
.fs-kpi-card::after{content:"";position:absolute;inset:0 0 auto;height:1px;opacity:.72;
 background:linear-gradient(90deg,transparent,color-mix(in srgb,var(--accent) 62%,white),transparent);transform:scaleX(.25);
 transform-origin:left;animation:fs-accent-sweep 760ms 180ms var(--fs-ease) both;pointer-events:none}
.fs-kpi-card:hover{transform:translateY(-2px);border-color:var(--fs-border-strong)}
.fs-kpi-card__label{color:var(--fs-muted);font-size:.79rem;font-weight:560}
.fs-kpi-card__value{margin-top:.52rem;color:var(--fs-text);font-size:clamp(1.25rem,1.7vw,1.7rem);font-weight:700;
 line-height:1.05;letter-spacing:-.035em;font-variant-numeric:tabular-nums;white-space:nowrap}
.fs-kpi-card__delta{margin-top:.52rem;color:var(--fs-muted);font-size:.71rem}.fs-kpi-card__delta--positive{color:var(--fs-green)}
.fs-kpi-card__delta--negative{color:var(--fs-coral)}
.fs-kpi-card__icon{display:grid;place-items:center;width:3rem;height:3rem;border:1px solid color-mix(in srgb,var(--accent) 42%,transparent);
 border-radius:10px;background:color-mix(in srgb,var(--accent) 24%,transparent);color:var(--accent);box-shadow:inset 0 1px 0 rgba(255,255,255,.12)}
.material-symbols-rounded{font-family:"Material Symbols Rounded"!important;font-weight:normal!important;font-style:normal!important;
 font-size:1.25rem;line-height:1;letter-spacing:normal;text-transform:none;white-space:nowrap;word-wrap:normal;direction:ltr;
 -webkit-font-feature-settings:"liga";font-feature-settings:"liga";font-variation-settings:"FILL" 0,"wght" 430,"GRAD" 0,"opsz" 24}
.fs-kpi-card__icon .material-symbols-rounded{font-size:1.55rem}

[data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"],[data-testid="stMain"] [data-testid="stForm"],
[data-testid="stMain"] [data-testid="stMetric"],[data-testid="stMain"] [data-testid="stExpander"],[data-testid="stMain"] [data-testid="stChatMessage"]{
 border-color:var(--fs-border)!important;border-radius:var(--fs-radius)!important;background:var(--fs-surface)!important;box-shadow:none!important;
 transition:background-color 180ms ease,border-color 180ms ease,color 180ms ease,box-shadow 180ms ease}
[data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"]{padding:clamp(.9rem,1.4vw,1.15rem)!important}
[data-testid="stMain"] [data-testid="stMetric"]{width:100%;min-height:7.6rem;padding:.95rem 1rem!important;overflow:hidden;
 animation:fs-card-enter 500ms var(--fs-ease) both;transition:transform 180ms var(--fs-ease),border-color 180ms ease,box-shadow 180ms ease}
[data-testid="stMain"] [data-testid="stMetric"]:hover{transform:translateY(-2px);border-color:var(--fs-border-strong)!important}
[data-testid="stMain"] [data-testid="stMetricLabel"]{color:var(--fs-muted)!important;font-size:.78rem;font-weight:560}
[data-testid="stMain"] [data-testid="stMetricValue"]{color:var(--fs-text)!important;font-variant-numeric:tabular-nums;letter-spacing:-.035em}
[data-testid="stMain"] [data-testid="stMetricDelta"]{font-size:.71rem}
[data-testid="stMain"] [data-testid="stDataFrame"],[data-testid="stMain"] [data-testid="stVegaLiteChart"]{width:100%!important;max-width:100%!important;overflow:hidden;
 border:1px solid var(--fs-border);border-radius:7px;background:var(--fs-surface)!important;transition:background-color 180ms ease,border-color 180ms ease}
[data-testid="stMain"] [data-testid="stVegaLiteChart"]{animation:fs-chart-enter 680ms var(--fs-ease) both;transform-origin:50% 100%;isolation:isolate}
[data-testid="stMain"] [data-testid="stVegaLiteChart"]>div{width:100%!important;max-width:100%!important;background:var(--fs-surface)!important}
[data-testid="stMain"] [data-testid="stVegaLiteChart"] canvas,
[data-testid="stMain"] [data-testid="stVegaLiteChart"] svg{display:block;max-width:100%!important;animation:fs-chart-content 760ms 80ms var(--fs-ease) both}
[data-testid="stMain"] [data-testid="stTabs"] [role="tablist"]{width:fit-content;max-width:100%;padding:.18rem;overflow-x:auto;
 border:1px solid var(--fs-border);border-radius:7px;background:var(--fs-surface-strong)}
[data-testid="stMain"] [data-testid="stTabs"] [role="tab"]{min-height:2.35rem;border-radius:5px}
[data-testid="stMain"] [role="tabpanel"]{margin-top:.6rem}
[data-testid="stMain"] [data-testid="stAlert"]{border-radius:7px!important;border-width:1px!important;box-shadow:none!important}
[data-baseweb="input"]>div,[data-baseweb="textarea"]>div,[data-baseweb="select"]>div,[data-baseweb="base-input"]{
 border-color:var(--fs-border)!important;border-radius:7px!important;background:var(--fs-input)!important;color:var(--fs-text)!important}
[data-baseweb="input"] input,[data-baseweb="textarea"] textarea,[data-baseweb="select"] input,[data-baseweb="base-input"] input{
 color:var(--fs-text)!important;-webkit-text-fill-color:var(--fs-text)!important}
[data-testid="stSelectbox"] .react-aria-ComboBox>div{border-color:var(--fs-border)!important;background:var(--fs-input)!important;color:var(--fs-text)!important}
[data-testid="stSelectbox"] input{color:var(--fs-text)!important;-webkit-text-fill-color:var(--fs-text)!important}
[data-testid="stSelectbox"] input:disabled{opacity:.66!important}
[data-testid="stMain"] .stButton>button,[data-testid="stMain"] .stDownloadButton>button,[data-testid="stMain"] .stLinkButton>a,
[data-testid="stSidebar"] .stButton>button{min-height:2.5rem;border-radius:7px!important;font-weight:620;transition:transform 150ms ease,border-color 150ms ease}
[data-testid="stMain"] .stButton>button:hover,[data-testid="stMain"] .stDownloadButton>button:hover,[data-testid="stMain"] .stLinkButton>a:hover,
[data-testid="stSidebar"] .stButton>button:hover{transform:translateY(-1px)}
[data-testid="stMain"] .stButton>button:active,[data-testid="stMain"] .stDownloadButton>button:active,
[data-testid="stMain"] .stLinkButton>a:active,[data-testid="stSidebar"] .stButton>button:active{transform:translateY(0) scale(.985)}
[data-testid="stMain"] button[kind="secondary"],[data-testid="stSidebar"] button[kind="secondary"],
[data-testid="stMain"] button[kind="tertiary"],[data-testid="stSidebar"] button[kind="tertiary"]{
 border-color:var(--fs-border)!important;background:var(--fs-surface)!important;color:var(--fs-text)!important}
[data-testid="stMain"] button:disabled,[data-testid="stSidebar"] button:disabled{border-color:var(--fs-border)!important;
 background:var(--fs-surface-strong)!important;color:var(--fs-subtle)!important;opacity:.72!important}

[data-baseweb="popover"],[data-baseweb="popover"]>div,[role="listbox"],[role="menu"],
[data-testid="stPopoverBody"],[data-testid="stTooltipContent"],[role="tooltip"]{
 border-color:var(--fs-border)!important;background:var(--fs-surface)!important;color:var(--fs-text)!important;box-shadow:0 18px 48px var(--fs-shadow)!important}
[data-baseweb="popover"] p,[data-baseweb="popover"] span,[role="listbox"] li,[role="menu"] li,[role="tooltip"] *{color:var(--fs-text)!important}
[data-baseweb="calendar"],[data-baseweb="calendar"]>div{background:var(--fs-surface)!important;color:var(--fs-text)!important}
[data-testid="stMain"] code,[data-testid="stMain"] pre{border-color:var(--fs-border)!important;background:var(--fs-surface-strong)!important;color:var(--fs-text)!important}
[data-testid="stProgress"]>div>div,[data-testid="stProgress"] [role="progressbar"]{background-color:color-mix(in srgb,var(--fs-blue) 18%,var(--fs-surface-strong))!important}
#vg-tooltip-element,.vg-tooltip{border:1px solid var(--fs-border-strong)!important;border-radius:7px!important;
 background:var(--fs-surface)!important;color:var(--fs-text)!important;box-shadow:0 14px 34px var(--fs-shadow)!important}
#vg-tooltip-element td,.vg-tooltip td,.vg-tooltip .key,.vg-tooltip .value{color:var(--fs-text)!important}

.revo-brand{display:flex;align-items:center;gap:.58rem;margin:.05rem .35rem 1.05rem;color:var(--fs-text);font-family:Manrope,Inter,sans-serif;font-size:1.2rem;font-weight:780;letter-spacing:-.03em}
.revo-brand img{width:2rem;height:2rem;object-fit:contain;filter:drop-shadow(0 .35rem .8rem color-mix(in srgb,var(--fs-blue) 22%,transparent))}
.st-key-sidebar_account{margin-top:auto!important;padding-top:.8rem;border-top:1px solid var(--fs-border)}
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p{color:var(--fs-text)!important}
[data-testid="stSidebar"] .stMarkdownBadge{color:var(--fs-text)!important;background:color-mix(in srgb,var(--fs-blue) 14%,transparent)!important}
.revo-user-card{margin:.7rem 0 .65rem;padding:.8rem .75rem;border:1px solid var(--fs-border);border-radius:7px;background:var(--fs-surface-soft)}
.revo-user-label{display:block;margin-bottom:.18rem;color:var(--fs-muted);font-size:.64rem;font-weight:720;letter-spacing:.085em;text-transform:uppercase}
.revo-user-name{display:block;overflow-wrap:anywhere;background:linear-gradient(105deg,#059669,#34d399 62%,#86efac);background-clip:text;
 -webkit-background-clip:text;color:transparent;-webkit-text-fill-color:transparent;font-size:.96rem;font-weight:720;letter-spacing:-.02em}
.fs-empty-chart{display:grid;min-height:16.5rem;place-items:center;padding:1.25rem;border:1px dashed var(--fs-border-strong);border-radius:7px;
 background:repeating-linear-gradient(0deg,transparent 0 45px,color-mix(in srgb,var(--fs-grid) 45%,transparent) 46px),var(--fs-surface-strong);
 color:var(--fs-muted);text-align:center}.fs-empty-chart .material-symbols-rounded{display:block;margin:0 auto .55rem;color:var(--fs-blue);font-size:2rem}
.st-key-home_primary_grid [data-testid="stVerticalBlockBorderWrapper"],.st-key-dashboard_primary_grid [data-testid="stVerticalBlockBorderWrapper"]{min-height:22.5rem}
.st-key-home_lower_grid [data-testid="stVerticalBlockBorderWrapper"],.st-key-dashboard_lower_grid [data-testid="stVerticalBlockBorderWrapper"]{min-height:16.5rem}
.st-key-home_toolbar,.st-key-dashboard_toolbar,.st-key-finance_toolbar,.st-key-investments_toolbar,.st-key-planning_toolbar{padding:.72rem .82rem!important;
 border:1px solid var(--fs-border);border-radius:var(--fs-radius);background:var(--fs-surface-soft)}
div[role="dialog"]{overflow:hidden;border:1px solid var(--fs-border-strong)!important;border-radius:10px!important;
 background:color-mix(in srgb,var(--fs-surface) 94%,transparent)!important;color:var(--fs-text)!important;
 box-shadow:0 26px 80px var(--fs-shadow)!important;backdrop-filter:blur(22px) saturate(125%);
 animation:fs-dialog-enter 260ms var(--fs-ease) both}
[data-testid="stToast"]{border:1px solid var(--fs-border-strong)!important;border-radius:7px!important;background:var(--fs-surface)!important;color:var(--fs-text)!important}
@keyframes fs-enter{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
@keyframes fs-section-enter{from{opacity:0;transform:translateY(7px)}to{opacity:1;transform:translateY(0)}}
@keyframes fs-panel-enter{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
@keyframes fs-card-enter{from{opacity:0;transform:translateY(12px) scale(.985)}to{opacity:1;transform:translateY(0) scale(1)}}
@keyframes fs-accent-sweep{from{opacity:0;transform:scaleX(.25)}to{opacity:.72;transform:scaleX(1)}}
@keyframes fs-chart-enter{from{opacity:0;transform:translateY(14px) scale(.985)}to{opacity:1;transform:translateY(0) scale(1)}}
@keyframes fs-chart-content{from{opacity:.18;clip-path:inset(12% 0 0 0)}to{opacity:1;clip-path:inset(0 0 0 0)}}
@keyframes fs-dialog-enter{from{opacity:0;transform:translateY(10px) scale(.985)}to{opacity:1;transform:translateY(0) scale(1)}}

@media(hover:hover) and (pointer:fine){
 .fs-kpi-card:hover,[data-testid="stMain"] [data-testid="stMetric"]:hover{box-shadow:0 16px 36px var(--fs-shadow)}
 [data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"]:has([data-testid="stVegaLiteChart"]):hover{border-color:var(--fs-border-strong)!important}}

@media(max-width:1100px){
 .fs-kpi-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
 .st-key-home_primary_grid [data-testid="stHorizontalBlock"],.st-key-home_lower_grid [data-testid="stHorizontalBlock"],
 .st-key-dashboard_primary_grid [data-testid="stHorizontalBlock"],.st-key-dashboard_lower_grid [data-testid="stHorizontalBlock"]{flex-direction:column!important}
 .st-key-home_primary_grid [data-testid="stColumn"],.st-key-home_lower_grid [data-testid="stColumn"],
 .st-key-dashboard_primary_grid [data-testid="stColumn"],.st-key-dashboard_lower_grid [data-testid="stColumn"]{width:100%!important;min-width:0!important;flex:1 1 100%!important}}
@media(max-width:900px){
 [data-testid="stMainBlockContainer"],.stMainBlockContainer,.block-container{padding:calc(4rem + env(safe-area-inset-top,0px)) .8rem calc(2rem + env(safe-area-inset-bottom,0px))!important}
 [data-testid="stSidebar"]{width:min(18.5rem,88vw)!important;min-width:min(18.5rem,88vw)!important}
 [data-testid="stMain"] input,[data-testid="stMain"] textarea,[data-testid="stMain"] select{font-size:16px!important}
 .fs-page-header{grid-template-columns:minmax(0,1fr);min-height:auto;gap:.5rem}.fs-page-header__utility{padding-top:0}
 .fs-page-header__divider,.fs-page-header__date{display:none}
 [data-testid="stMain"] [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]){display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr));gap:.65rem!important}
 [data-testid="stMain"] [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"])>[data-testid="stColumn"]{width:100%!important;min-width:0!important;flex:none!important}}
@media(min-width:901px) and (max-width:1180px){
 [data-testid="stSidebar"]{width:12.5rem!important;min-width:12.5rem!important}
 [data-testid="stMainBlockContainer"],.stMainBlockContainer,.block-container{padding-inline:1rem!important}
 .st-key-home_toolbar,.st-key-dashboard_toolbar,.st-key-finance_toolbar,.st-key-investments_toolbar,.st-key-planning_toolbar{
  flex-wrap:wrap!important;align-items:flex-end!important}
 .st-key-home_toolbar>*,.st-key-dashboard_toolbar>*,.st-key-finance_toolbar>*,.st-key-investments_toolbar>*,.st-key-planning_toolbar>*{
  min-width:min(100%,12rem)!important}}
@media(max-width:620px){
 [data-testid="stMainBlockContainer"],.stMainBlockContainer,.block-container{padding-inline:.6rem!important}
 .fs-page-header h1{font-size:1.65rem!important}.fs-page-header p{font-size:.84rem}.fs-kpi-grid{gap:.55rem}
 .fs-kpi-card{grid-template-columns:minmax(0,1fr) 2.35rem;min-height:6.55rem;padding:.72rem .68rem}
 .fs-kpi-card__icon{width:2.2rem;height:2.2rem;border-radius:7px}.fs-kpi-card__icon .material-symbols-rounded{font-size:1.15rem}
 .fs-kpi-card__label{font-size:.67rem}.fs-kpi-card__value{margin-top:.35rem;font-size:clamp(1rem,5vw,1.28rem)}
 .fs-kpi-card__delta{margin-top:.35rem;font-size:.62rem}
 [data-testid="stMain"] [data-testid="stMetric"]{min-height:6.7rem;padding:.75rem .8rem!important}
 [data-testid="stMain"] [data-testid="stMetricLabel"]{font-size:.7rem}[data-testid="stMain"] [data-testid="stMetricValue"]{font-size:1.25rem}
 .st-key-home_primary_grid [data-testid="stVerticalBlockBorderWrapper"],.st-key-dashboard_primary_grid [data-testid="stVerticalBlockBorderWrapper"]{min-height:auto}
 [data-testid="stMain"] [data-testid="stVegaLiteChart"]{min-width:0!important}
 [data-testid="stMain"] [data-testid="stVegaLiteChart"] canvas,[data-testid="stMain"] [data-testid="stVegaLiteChart"] svg{width:100%!important;height:auto!important}}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{scroll-behavior:auto!important;animation-duration:.01ms!important;animation-iteration-count:1!important;transition-duration:.01ms!important}}
</style>
"""


def theme_name() -> str:
    return "light" if st.session_state.get("theme_light", False) else "dark"


def chart_theme() -> dict[str, str]:
    colors = THEMES[theme_name()]
    return {
        "text": colors["text"],
        "muted": colors["muted"],
        "grid": colors["grid"],
        "surface": colors["surface"],
        "surface_soft": colors["surface_strong"],
        "border": colors["border_strong"],
    }


def inject_app_styles() -> None:
    colors = THEMES[theme_name()]
    variables = f"""<style>:root{{--fs-canvas:{colors['canvas']};--fs-sidebar:{colors['sidebar']};
    --fs-surface:{colors['surface']};--fs-surface-strong:{colors['surface_strong']};--fs-surface-soft:{colors['surface_soft']};
    --fs-border:{colors['border']};--fs-border-strong:{colors['border_strong']};--fs-text:{colors['text']};--fs-muted:{colors['muted']};
    --fs-subtle:{colors['subtle']};--fs-input:{colors['input']};--fs-grid:{colors['grid']};--fs-shadow:{colors['shadow']};
    --fs-green:{ACCENTS['green']};--fs-coral:{ACCENTS['red']};--fs-blue:{ACCENTS['blue']};--fs-violet:{ACCENTS['violet']};
    --fs-amber:{ACCENTS['amber']};--fs-radius:8px;--fs-ease:cubic-bezier(.22,.78,.28,1);color-scheme:{theme_name()}}}</style>"""
    st.html(variables + APP_STYLES)


def page_header(title: str, description: str, *, eyebrow: str, meta: str | None = None) -> None:
    user = st.session_state.get("user") or {}
    user_name = str(user.get("name", "Conta"))
    initials = "".join(part[0] for part in user_name.split()[:2]).upper() or "FS"
    shown_meta = meta or date.today().strftime("%d/%m/%Y")
    safe_title = escape(title)
    first_name = escape(user_name.split()[0]) if user_name.split() else ""
    if first_name and safe_title.endswith(first_name):
        safe_title = safe_title[: -len(first_name)] + f'<span class="fs-page-header__highlight">{first_name}</span>'
    st.html(f"""<header class="fs-page-header"><div class="fs-page-header__main">
    <span class="fs-page-header__eyebrow">{escape(eyebrow)}</span><h1>{safe_title}</h1><p>{escape(description)}</p></div>
    <div class="fs-page-header__utility" aria-label="Contexto da conta"><span class="fs-page-header__date">{escape(shown_meta)}</span>
    <span class="fs-page-header__divider" aria-hidden="true"></span><span class="fs-page-header__avatar" aria-hidden="true">{escape(initials)}</span>
    <span>{escape(user_name)}</span></div></header>""")


def metric_card_grid(cards: Iterable[Mapping[str, str]]) -> None:
    rendered: list[str] = []
    for card in cards:
        accent = ACCENTS.get(card.get("tone", "blue"), ACCENTS["blue"])
        delta_tone = card.get("delta_tone", "neutral")
        delta_class = f" fs-kpi-card__delta--{delta_tone}" if delta_tone in {"positive", "negative"} else ""
        rendered.append(f"""<article class="fs-kpi-card" style="--accent:{accent}"><div>
        <div class="fs-kpi-card__label">{escape(card.get('label',''))}</div><div class="fs-kpi-card__value">{escape(card.get('value',''))}</div>
        <div class="fs-kpi-card__delta{delta_class}">{escape(card.get('delta',''))}</div></div>
        <span class="fs-kpi-card__icon" aria-hidden="true"><span class="material-symbols-rounded">{escape(card.get('icon','monitoring'))}</span></span></article>""")
    st.html(f'<section class="fs-kpi-grid">{"".join(rendered)}</section>')


def empty_chart_state(message: str, *, icon: str = "monitoring") -> None:
    st.html(f'<div class="fs-empty-chart"><div><span class="material-symbols-rounded">{escape(icon)}</span>{escape(message)}</div></div>')


def section_label(label: str) -> None:
    st.html(f'<p class="fs-section-label">{escape(label)}</p>')
