import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Activity, AlertCircle, AlertTriangle, ArrowRight, ArrowUpRight,
  Bell, BookOpen, Bookmark, Check, CheckCircle2, ChevronDown,
  ChevronLeft, ChevronRight, CircleHelp, Clock3, Copy, FileCheck2,
  FileSearch, FileText, FolderOpen, Gauge, Info,
  LayoutDashboard, LifeBuoy, ListChecks, LoaderCircle, LockKeyhole,
  Menu, MessageSquareText, MoreHorizontal, Plus, Printer, RefreshCw, Search,
  Send, Settings, ShieldAlert, ShieldCheck, Sparkles, Trash2, Upload, UploadCloud, X,
} from 'lucide-react';
import { api } from './services/api.js';
import { I18nProvider, translateUiText, useT } from './i18n.js';

const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, group: 'WORKSPACE' },
  { id: 'analyze', label: 'Analyze agreement', icon: FileSearch, group: 'WORKSPACE' },
  { id: 'documents', label: 'My documents', icon: FolderOpen, group: 'LIBRARY' },
  { id: 'reports', label: 'Risk reports', icon: ShieldAlert, group: 'LIBRARY' },
  { id: 'saved', label: 'Saved analyses', icon: Bookmark, group: 'LIBRARY' },
];

const LABELS = {
  security_deposit: 'Security deposit', rent_escalation: 'Rent increase', lock_in_period: 'Lock-in period',
  termination: 'Termination', notice_period: 'Notice period', service_bond: 'Service bond',
  training_cost_recovery: 'Training cost recovery', salary_deductions: 'Salary deductions',
  confidentiality: 'Confidentiality', owner_entry_inspection: 'Landlord access',
  maintenance_repairs: 'Repairs & maintenance', utilities_and_charges: 'Utilities & charges',
  subletting_guests: 'Guests & subletting', document_retention: 'Document retention',
  payment_terms: 'Payment terms', dispute_resolution: 'Dispute resolution', governing_law: 'Governing law',
  eviction_default: 'Default & eviction', tenant_verification: 'Tenant verification',
  handover_inventory: 'Handover & inventory', non_compete: 'Non-compete',
  property_specifications: 'Property specifications and changes', title_and_encumbrances: 'Title and encumbrances',
  possession_handover: 'Possession and handover', booking_payment: 'Booking and purchase payments',
  cancellation_refund: 'Cancellation and refund', registration_charges: 'Registration, stamp duty and charges',
  other: 'Other clause',
};

const DOC_LABELS = {
  rent_agreement: 'Rental agreement', offer_and_bond: 'Employment offer & bond',
  property_purchase: 'Property purchase agreement',
  unknown: 'Agreement',
};

const LANGUAGE_OPTIONS = [
  { value: 'en', label: 'English' },
  { value: 'hi', label: 'Hindi (हिन्दी)' },
  { value: 'hinglish', label: 'Hinglish (Roman Hindi)' },
  { value: 'mr', label: 'Marathi (मराठी)' },
  { value: 'gu', label: 'Gujarati (ગુજરાતી)' },
  { value: 'bn', label: 'Bengali (বাংলা)' },
  { value: 'as', label: 'Assamese (অসমীয়া)' },
  { value: 'pa', label: 'Punjabi (ਪੰਜਾਬੀ)' },
  { value: 'or', label: 'Odia (ଓଡ଼ିଆ)' },
  { value: 'th', label: 'Thai (ไทย)' },
  { value: 'ta', label: 'Tamil (தமிழ்)' },
  { value: 'te', label: 'Telugu (తెలుగు)' },
  { value: 'kn', label: 'Kannada (ಕನ್ನಡ)' },
  { value: 'ml', label: 'Malayalam (മലയാളം)' },
  { value: 'ur', label: 'Urdu (اردو)' },
  { value: 'ar', label: 'Arabic (العربية)' },
  { value: 'ne', label: 'Nepali (नेपाली)' },
  { value: 'es', label: 'Spanish' },
  { value: 'fr', label: 'French' },
  { value: 'de', label: 'German' },
  { value: 'pt', label: 'Portuguese' },
  { value: 'zh', label: 'Chinese' },
  { value: 'ja', label: 'Japanese' },
  { value: 'id', label: 'Indonesian' },
  { value: 'it', label: 'Italian' },
  { value: 'nl', label: 'Dutch' },
  { value: 'ru', label: 'Russian' },
  { value: 'tr', label: 'Turkish' },
  { value: 'vi', label: 'Vietnamese' },
  { value: 'ko', label: 'Korean' },
  { value: 'pl', label: 'Polish' },
  { value: 'uk', label: 'Ukrainian' },
  { value: 'el', label: 'Greek' },
  { value: 'he', label: 'Hebrew' },
  { value: 'fa', label: 'Persian' },
  { value: 'fi', label: 'Finnish' },
  { value: 'sv', label: 'Swedish' },
  { value: 'af', label: 'Afrikaans' },
  { value: 'ca', label: 'Catalan' },
  { value: 'cs', label: 'Czech' },
  { value: 'da', label: 'Danish' },
  { value: 'eo', label: 'Esperanto' },
  { value: 'et', label: 'Estonian' },
  { value: 'hr', label: 'Croatian' },
  { value: 'hu', label: 'Hungarian' },
  { value: 'lt', label: 'Lithuanian' },
  { value: 'lv', label: 'Latvian' },
  { value: 'ms', label: 'Malay' },
  { value: 'no', label: 'Norwegian' },
  { value: 'ro', label: 'Romanian' },
  { value: 'sk', label: 'Slovak' },
  { value: 'sl', label: 'Slovenian' },
  { value: 'sq', label: 'Albanian' },
];

const SOURCE_LANGUAGE_OPTIONS = [
  { value: 'auto', label: 'Auto-detect language' },
  ...LANGUAGE_OPTIONS,
];
const languageLabel = (code) => LANGUAGE_OPTIONS.find((item) => item.value === code)?.label || 'English';

const cx = (...parts) => parts.filter(Boolean).join(' ');
const cap = (value = '') => String(value).replaceAll('_', ' ').replace(/\b\w/g, (char) => char.toUpperCase());
const clauseName = (item) => item?.heading || LABELS[item?.primary] || cap(item?.primary) || 'Agreement clause';
const docName = (report) => report?.display_doc_type || DOC_LABELS[report?.doc_type] || cap(report?.doc_type || 'Agreement');
const dateLabel = (value) => {
  if (!value) return 'Date unavailable';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value).slice(0, 10) : new Intl.DateTimeFormat('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }).format(date);
};
const timeLabel = (value) => {
  if (!value) return 'Recently';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Recently';
  const days = Math.max(0, Math.floor((Date.now() - date.getTime()) / 86400000));
  if (days === 0) return 'Today';
  if (days === 1) return 'Yesterday';
  if (days < 7) return `${days} days ago`;
  return dateLabel(value);
};
const riskLevel = (value) => ['red', 'amber', 'green'].includes(value) ? value : 'green';
const riskLabel = (value) => ({ red: 'High risk', amber: 'Medium risk', green: 'Low risk' })[riskLevel(value)];
const formatCount = (value) => Number(value || 0).toLocaleString('en-IN');
const reportScore = (report) => Number(report?.summary?.risk_score ?? 0);

function RiskBadge({ risk = 'green', children }) {
  const t = useT();
  const value = riskLevel(risk);
  return <span className={`risk-badge risk-${value}`}><span className="risk-dot" />{t(children || riskLabel(value))}</span>;
}

function IconBox({ icon: Icon, tone = 'blue', size = 18 }) {
  return <span className={`icon-box tone-${tone}`}><Icon size={size} strokeWidth={1.9} /></span>;
}

function EmptyState({ icon: Icon = FileSearch, title, description, action, onAction }) {
  const t = useT();
  return <div className="empty-state">
    <div className="empty-icon"><Icon size={25} /></div>
    <h3>{t(title)}</h3><p>{t(description)}</p>
    {action && <button className="button button-primary" onClick={onAction}><Plus size={16} />{t(action)}</button>}
  </div>;
}

function Sidebar({ view, setView, open, onClose, reportCount = 0 }) {
  const t = useT();
  const groups = ['WORKSPACE', 'LIBRARY'];
  return <>
    <div className={cx('sidebar-scrim', open && 'is-visible')} onClick={onClose} />
    <aside className={cx('sidebar', open && 'sidebar-open')}>
      <div className="brand-row">
        <div className="brand-mark"><ShieldCheck size={21} strokeWidth={2.3} /></div>
        <div className="brand-copy"><strong>ClauseLens</strong><span>{t('Legal AI workspace')}</span></div>
        <button className="icon-button sidebar-close" aria-label={t('Close navigation')} onClick={onClose}><X size={19} /></button>
      </div>
      <button className="button button-primary sidebar-new" onClick={() => { setView('analyze'); onClose(); }}><Plus size={17} />{t('New analysis')}</button>
      <nav className="side-nav" aria-label={t('Main navigation')}>
        {groups.map((group) => <div className="nav-group" key={group}>
          <div className="nav-group-label">{t(group)}</div>
          {NAV_ITEMS.filter((item) => item.group === group).map(({ id, label, icon: Icon }) => (
            <button key={id} className={cx('nav-item', view === id || (view === 'report' && id === 'reports') ? 'nav-item-active' : '')} onClick={() => { setView(id); onClose(); }}>
              <Icon size={17} strokeWidth={1.9} /><span>{t(label)}</span>
              {id === 'reports' && reportCount > 0 && <span className="nav-count">{reportCount > 99 ? '99+' : reportCount}</span>}
            </button>
          ))}
        </div>)}
      </nav>
      <div className="sidebar-bottom">
        <button className={cx('nav-item', view === 'help' && 'nav-item-active')} onClick={() => { setView('help'); onClose(); }}><LifeBuoy size={17} /><span>{t('Help & support')}</span></button>
        <button className={cx('nav-item', view === 'privacy' && 'nav-item-active')} onClick={() => { setView('privacy'); onClose(); }}><LockKeyhole size={17} /><span>{t('Privacy & security')}</span></button>
        <div className="sidebar-profile">
          <div className="profile-avatar">CL</div>
          <div className="profile-text"><strong>{t('Local workspace')}</strong><span>{t('Private by default')}</span></div>
          <ShieldCheck size={16} className="profile-shield" />
        </div>
      </div>
    </aside>
  </>;
}

function Topbar({ onMenu, view, setView, query, setQuery, uiLanguage, onUiLanguageChange, reports, onOpenReport }) {
  const t = useT();
  const [searchOpen, setSearchOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const searchRef = useRef(null);
  const matches = useMemo(() => {
    if (!query.trim()) return [];
    return reports.filter((r) => `${r.title || ''} ${r.doc_type || ''} ${r.report_id || ''}`.toLowerCase().includes(query.toLowerCase())).slice(0, 5);
  }, [query, reports]);
  useEffect(() => { if (searchOpen) searchRef.current?.focus(); }, [searchOpen]);
  return <header className="topbar">
    <div className="topbar-left">
      <button className="icon-button mobile-menu" aria-label={t('Open navigation')} onClick={onMenu}><Menu size={21} /></button>
      <div className="breadcrumbs"><span>{t('Workspace')}</span><ChevronRight size={14} /><strong>{t(view === 'report' ? 'Analysis report' : view === 'analyze' ? 'Analyze agreement' : cap(view))}</strong></div>
    </div>
    <div className="topbar-actions">
      <div className={cx('global-search', searchOpen && 'search-expanded')}>
        <Search size={16} />
        <input value={query} onChange={(e) => setQuery(e.target.value)} onFocus={() => setSearchOpen(true)} onBlur={() => setTimeout(() => { setSearchOpen(false); }, 180)} ref={searchRef} placeholder={t('Search documents, clauses…')} aria-label={t('Search documents')} />
        <kbd>⌘ K</kbd>
        {searchOpen && query.trim() && <div className="search-popover">
          <div className="popover-label">{t('DOCUMENTS')}</div>
          {matches.length ? matches.map((item) => <button key={item.report_id} className="search-result" onMouseDown={(e) => e.preventDefault()} onClick={() => { onOpenReport(item.report_id); setQuery(''); setSearchOpen(false); }}>
            <FileText size={16} /><span><strong>{item.title || t(docName(item))}</strong><small>{dateLabel(item.created_utc)}</small></span><RiskBadge risk={item.overall_risk} />
          </button>) : <div className="search-empty">{t('No matching documents found.')}</div>}
          <button className="search-view-all" onMouseDown={(e) => e.preventDefault()} onClick={() => { setView('documents'); setSearchOpen(false); }}>{t('View all documents')} <ArrowRight size={14} /></button>
        </div>}
      </div>
      <div className="language-switch" role="group" aria-label={t('Interface language')}>
        <button type="button" className={uiLanguage === 'en' ? 'selected' : ''} aria-pressed={uiLanguage === 'en'} onClick={() => onUiLanguageChange('en')} title={t('English interface')}>EN</button>
        <button type="button" className={uiLanguage === 'hi' ? 'selected' : ''} aria-pressed={uiLanguage === 'hi'} onClick={() => onUiLanguageChange('hi')} title={t('Hindi interface')}>HI</button>
      </div>
      <div className="relative-control">
        <button className="icon-button top-icon" aria-label={t('Notifications')} onClick={() => setNotificationsOpen((v) => !v)}><Bell size={18} /><span className="notification-dot" /></button>
        {notificationsOpen && <div className="small-popover notification-popover"><strong>{t("You're all caught up")}</strong><p>{t('New analysis updates will appear here.')}</p><button onClick={() => setNotificationsOpen(false)}>{t('Dismiss')}</button></div>}
      </div>
      <button className="icon-button top-icon help-top" aria-label={t('Help')} onClick={() => setView('help')}><CircleHelp size={18} /></button>
      <button className="button button-primary top-new" onClick={() => setView('analyze')}><Plus size={16} /><span>{t('New analysis')}</span></button>
      <div className="mini-avatar" title="Local workspace">CL</div>
    </div>
  </header>;
}

function PageHeading({ eyebrow, title, description, action, onAction, actionIcon: ActionIcon = Plus }) {
  const t = useT();
  return <div className="page-heading">
    <div><div className="eyebrow">{t(eyebrow)}</div><h1>{t(title)}</h1>{description && <p>{t(description)}</p>}</div>
    {action && <button className="button button-primary heading-action" onClick={onAction}><ActionIcon size={16} />{t(action)}</button>}
  </div>;
}

function StatCard({ icon: Icon, label, value, detail, tone = 'blue', trend }) {
  const t = useT();
  return <div className="stat-card">
    <div className="stat-card-top"><IconBox icon={Icon} tone={tone} /><span className="stat-label">{t(label)}</span>{trend && <span className="stat-trend"><ArrowUpRight size={13} />{trend}</span>}</div>
    <div className="stat-value">{value}</div><div className="stat-detail">{t(detail)}</div>
  </div>;
}

function RiskDistribution({ summary }) {
  const t = useT();
  const counts = summary?.counts || {};
  const red = Number(counts.red || 0); const amber = Number(counts.amber || 0); const green = Number(counts.green || 0);
  const total = red + amber + green;
  const pct = (number) => total ? `${number / total * 100}%` : '0%';
  return <div className="distribution-card card">
    <div className="card-heading"><div><h3>{t('Clause risk distribution')}</h3><p>{t('Risk levels across assessed clauses')}</p></div><span className="small-muted">{total} {t('assessed')}</span></div>
    <div className="distribution-bar" role="img" aria-label={`${red} high risk, ${amber} medium risk, ${green} low risk clauses`}>
      {total > 0 ? <><span className="bar-red" style={{ width: pct(red) }} /><span className="bar-amber" style={{ width: pct(amber) }} /><span className="bar-green" style={{ width: pct(green) }} /></> : <span className="bar-empty" />}
    </div>
    <div className="distribution-legend">
      <div><span className="legend-dot dot-red" /><div><strong>{red}</strong><small>{summary?.display_risk_labels?.red || t('High risk')}</small></div><span className="legend-percent">{pct(red)}</span></div>
      <div><span className="legend-dot dot-amber" /><div><strong>{amber}</strong><small>{summary?.display_risk_labels?.amber || t('Medium risk')}</small></div><span className="legend-percent">{pct(amber)}</span></div>
      <div><span className="legend-dot dot-green" /><div><strong>{green}</strong><small>{summary?.display_risk_labels?.green || t('Low risk')}</small></div><span className="legend-percent">{pct(green)}</span></div>
    </div>
  </div>;
}

function ReportList({ reports, loading, onOpen, onDelete, emptyTitle = 'No documents yet', emptyDescription = 'Analyze an agreement to build your private document library.', onStart, query = '' }) {
  const t = useT();
  const visible = reports.filter((r) => `${r.title || ''} ${r.doc_type || ''} ${r.report_id || ''}`.toLowerCase().includes(query.toLowerCase()));
  if (loading) return <div className="loading-panel"><LoaderCircle className="spin" size={22} /><span>{t('Loading your workspace…')}</span></div>;
  if (!visible.length) return <EmptyState icon={FolderOpen} title={query ? 'No documents match your search' : emptyTitle} description={query ? 'Try a different title or clear the search field.' : emptyDescription} action={!query ? 'Analyze an agreement' : undefined} onAction={onStart} />;
  return <div className="table-wrap"><table className="documents-table"><thead><tr><th>{t('DOCUMENT')}</th><th>{t('TYPE')}</th><th>{t('RISK LEVEL')}</th><th>{t('ANALYZED')}</th><th className="align-right">{t('ACTIONS')}</th></tr></thead><tbody>
    {visible.map((item) => <tr key={item.report_id}>
      <td><button className="document-cell" onClick={() => onOpen(item.report_id)}><span className="file-type-icon"><FileText size={18} /></span><span><strong>{item.title || `${t(docName(item))} · ${dateLabel(item.created_utc)}`}</strong><small>CL-{String(item.report_id || '').slice(0, 8).toUpperCase()}</small></span></button></td>
      <td><span className="type-label">{t(docName(item))}</span></td>
      <td><RiskBadge risk={item.overall_risk} /></td>
      <td><span className="date-cell">{dateLabel(item.created_utc)}</span><small className="date-relative">{timeLabel(item.created_utc)}</small></td>
      <td><div className="table-actions"><button className="button button-quiet button-small" onClick={() => onOpen(item.report_id)}>{t('View report')} <ChevronRight size={14} /></button><button className="icon-button danger-hover" aria-label={t('Delete report')} title={t('Delete report')} onClick={() => onDelete(item.report_id)}><Trash2 size={15} /></button></div></td>
    </tr>)}
  </tbody></table></div>;
}

function Dashboard({ reports, loading, onNew, onOpen, onSample, onDelete, query }) {
  const t = useT();
  const recent = reports.slice(0, 5);
  const high = reports.filter((r) => r.overall_risk === 'red').length;
  const medium = reports.filter((r) => r.overall_risk === 'amber').length;
  const low = reports.filter((r) => r.overall_risk === 'green').length;
  return <div className="page-stack">
    <PageHeading eyebrow="YOUR LEGAL WORKSPACE" title="Agreement clarity starts here." description="Review the fine print, surface terms worth questioning, and make more informed decisions before you sign." action="New analysis" onAction={onNew} />
    <section className="welcome-hero">
      <div className="hero-grid-mark hero-mark-one" /><div className="hero-grid-mark hero-mark-two" />
      <div className="hero-content"><div className="hero-pill"><Sparkles size={13} /> {t('CLAUSELENS WORKSPACE')}</div><h2>{t("Know what you’re") }<br className="desktop-br" /> {t("signing up for.")}</h2><p>{t("Turn complex agreements into clear, structured insights — one clause at a time.")}</p><div className="hero-actions"><button className="button button-light" onClick={onNew}><FileSearch size={16} />{t("Analyze an agreement")} <ArrowRight size={15} /></button><button className="button button-hero-ghost" onClick={() => onSample()}><BookOpen size={16} />{t("Explore a sample")}</button></div></div>
      <div className="hero-art" aria-hidden="true"><div className="hero-document"><div className="hero-doc-top"><span /><span /><span /></div><div className="hero-doc-brand"><span className="hero-shield"><ShieldCheck size={20} /></span><div><b>{t('AGREEMENT REVIEW')}</b><small>{t('ClauseLens analysis')}</small></div></div><div className="hero-doc-line wide" /><div className="hero-doc-line" /><div className="hero-doc-line mid" /><div className="hero-doc-highlight"><span className="hero-highlight-icon"><AlertTriangle size={13} /></span><div><b>{t('Clause flagged for review')}</b><span>{t('Financial terms · Section 4.2')}</span></div><span className="hero-risk-dot" /></div><div className="hero-doc-line wide" /><div className="hero-doc-line mid" /></div><div className="hero-art-badge"><ShieldCheck size={17} /><span><b>{t('Privacy-first')}</b><small>{t('Local analysis workflow')}</small></span></div></div>
    </section>
    <section className="stats-grid">
      <StatCard icon={FileCheck2} label="Documents reviewed" value={formatCount(reports.length)} detail="Total saved analyses" tone="blue" />
      <StatCard icon={ShieldAlert} label="High-risk reports" value={formatCount(high)} detail={high ? 'Review these first' : 'No high-risk reports yet'} tone="red" />
      <StatCard icon={Activity} label="Needs a closer look" value={formatCount(medium)} detail="Medium-risk reports" tone="amber" />
      <StatCard icon={ShieldCheck} label="Lower-risk reports" value={formatCount(low)} detail="Still review key terms" tone="green" />
    </section>
    <section className="dashboard-lower-grid">
      <div className="card recent-card">
        <div className="card-heading"><div><h3>{t('Recent documents')}</h3><p>{t('Your most recently analyzed agreements')}</p></div><button className="text-button" onClick={() => window.dispatchEvent(new CustomEvent('clauselens-navigate', { detail: 'documents' }))}>{t('View all')} <ArrowRight size={14} /></button></div>
        <ReportList reports={recent} loading={loading} query={query} onOpen={onOpen} onDelete={onDelete} onStart={onNew} emptyTitle="Your library is ready" emptyDescription="Start with a rental agreement or an employment offer." />
      </div>
      <div className="card quick-start-card">
        <div className="quick-start-head"><IconBox icon={UploadCloud} tone="blue" size={20} /><div><h3>{t('Start a review')}</h3><p>{t('Choose a document to get started.')}</p></div></div>
        <button className="quick-action" onClick={onNew}><span className="quick-action-icon"><FileText size={18} /></span><span><strong>{t('Upload an agreement')}</strong><small>{t("PDF, DOCX, TXT or MD")}</small></span><ChevronRight size={17} /></button>
        <button className="quick-action" onClick={() => onSample()}><span className="quick-action-icon violet"><BookOpen size={18} /></span><span><strong>{t('Try a sample agreement')}</strong><small>{t('Explore how the analysis works')}</small></span><ChevronRight size={17} /></button>
        <div className="privacy-note"><LockKeyhole size={15} /><span>{t('Your report history stays in your local workspace. Review the privacy notes before uploading sensitive documents.')}</span></div>
      </div>
    </section>
    <section className="bottom-note"><Info size={16} /><p><strong>{t('Important:')}</strong> {t('ClauseLens is an awareness and document-review aid, not a legal verdict. Risk flags are indicators and should be reviewed with a qualified legal professional.')}</p></section>
  </div>;
}

function Dropzone({ file, setFile }) {
  const t = useT();
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef(null);
  const accept = '.pdf,.docx,.txt,.md';
  const handleFiles = (files) => {
    const selected = files?.[0];
    if (!selected) return;
    const extension = selected.name.split('.').pop()?.toLowerCase();
    if (!['pdf', 'docx', 'txt', 'md'].includes(extension)) { window.dispatchEvent(new CustomEvent('clauselens-toast', { detail: { message: t('Please choose a PDF, DOCX, TXT or MD file.'), kind: 'error' } })); return; }
    setFile(selected);
  };
  return <div className={cx('dropzone', dragging && 'dropzone-active', file && 'dropzone-has-file')} onDragEnter={(e) => { e.preventDefault(); setDragging(true); }} onDragOver={(e) => { e.preventDefault(); setDragging(true); }} onDragLeave={(e) => { e.preventDefault(); setDragging(false); }} onDrop={(e) => { e.preventDefault(); setDragging(false); handleFiles(e.dataTransfer.files); }}>
    <input ref={inputRef} type="file" accept={accept} hidden onChange={(e) => handleFiles(e.target.files)} />
    {file ? <><div className="dropzone-file-icon"><FileCheck2 size={25} /></div><strong className="dropzone-file-name">{file.name}</strong><span className="dropzone-support">{(file.size / 1024 / 1024).toFixed(2)} MB · {t('Ready to analyze')}</span><div className="dropzone-file-actions"><button className="button button-secondary button-small" onClick={() => inputRef.current?.click()}><RefreshCw size={14} />{t('Replace file')}</button><button className="text-button danger-text" onClick={() => { setFile(null); if (inputRef.current) inputRef.current.value = ''; }}><X size={14} />{t('Remove')}</button></div></> : <><div className="dropzone-icon"><UploadCloud size={28} /></div><strong>{t('Drop your agreement here')}</strong><span>{t('or select a file from your device')}</span><button type="button" className="button button-secondary browse-button" onClick={() => inputRef.current?.click()}><Upload size={15} />{t('Browse files')}</button><small>{t('PDF, DOCX, TXT or MD · up to 5 MB')}</small></>}
  </div>;
}

function AnalyzePage({ draftText, setDraftText, file, setFile, inputMode, setInputMode, language, setLanguage, sourceLanguage, setSourceLanguage, translationStatus, persist, setPersist, onAnalyze, onSample, busy, onClear }) {
  const t = useT();
  const [docType, setDocType] = useState('rent_agreement');
  return <div className="page-stack">
    <PageHeading eyebrow="ANALYSIS WORKSPACE" title="Analyze an agreement" description="Upload a document or paste the relevant text. ClauseLens will organize clauses and flag terms that may need closer review." />
    <div className="analysis-layout">
      <div className="analysis-main card">
        <div className="analysis-title-row"><div><div className="section-kicker">{t("STEP 1 OF 2")}</div><h2>{t('Choose your agreement')}</h2><p>{t('Start with a file or paste the contract text below.')}</p></div><span className="secure-chip"><LockKeyhole size={13} />{t('Local workflow')}</span></div>
        <div className="input-tabs"><button className={inputMode === 'file' ? 'input-tab active' : 'input-tab'} onClick={() => setInputMode('file')}><UploadCloud size={16} />{t('Upload file')}</button><button className={inputMode === 'text' ? 'input-tab active' : 'input-tab'} onClick={() => { setInputMode('text'); setFile(null); }}><FileText size={16} />{t('Paste text')}</button></div>
        {inputMode === 'file' ? <Dropzone file={file} setFile={(selected) => { setFile(selected); setDraftText(''); }} /> : <div className="text-input-wrap"><label htmlFor="agreement-text">{t('Agreement text')}</label><textarea id="agreement-text" className="agreement-textarea" value={draftText} onChange={(e) => { setDraftText(e.target.value); setFile(null); }} placeholder={t('Paste the rental agreement, leave and license agreement, job offer, or service bond text here…')} /><div className="textarea-footer"><span>{draftText.length.toLocaleString('en-IN')} {t('characters')}</span><button className="text-button" onClick={() => setDraftText('')}>{t('Clear text')}</button></div></div>}
        <div className="analysis-form-divider" />
        <div className={cx('translation-service-note', translationStatus?.ready && 'translation-service-ready')} role="status">
          <Info size={15} />
          <span>{translationStatus?.ready
            ? `${t(translationStatus.local ? 'Local translation is available at' : 'A remote translation service is configured at')} ${translationStatus.endpoint}. ${t('Supported language pairs depend on the installed models.')}`
            : t('English analysis works without translation. For Hindi or other-language documents/reports, start a local LibreTranslate service at http://127.0.0.1:5000. ClauseLens does not silently upload legal documents to a remote translator.')}</span>
        </div>
        <div className="form-section-heading"><div><div className="section-kicker">{t("STEP 2 OF 2")}</div><h2>{t('Configure the review')}</h2><p>{t('Choose the document language and the language for explanations.')}</p></div></div>
        <div className="analysis-options-grid">
          <div className="form-field"><label htmlFor="doc-type">{t('Sample agreement type')}</label><div className="select-wrap"><select id="doc-type" value={docType} onChange={(e) => setDocType(e.target.value)}><option value="rent_agreement">{t('Rental / Leave & License')}</option><option value="offer_and_bond">{t('Employment offer / service bond')}</option><option value="property_purchase">{t('Home purchase agreement')}</option></select><ChevronDown size={16} /></div><small className="field-hint">{t('Used for sample documents. For your own file, ClauseLens infers the agreement type from its text.')}</small></div>
          <div className="form-field"><label htmlFor="source-language">{t("Document language")}</label><div className="select-wrap"><select id="source-language" value={sourceLanguage} onChange={(e) => setSourceLanguage(e.target.value)}>{SOURCE_LANGUAGE_OPTIONS.map((item) => { const supported = translationStatus?.supported_source_codes_to_english || []; const needsTranslator = !['auto', 'en', 'hinglish'].includes(item.value); const disabled = needsTranslator && (!translationStatus?.ready || !supported.includes(item.value)); return <option key={item.value} value={item.value} disabled={disabled}>{item.label}{disabled ? ` · ${t('model unavailable')}` : ''}</option>; })}</select><ChevronDown size={16} /></div><small className="field-hint">{t('Auto-detect works on extracted text. For scanned PDFs, choose the language manually and install its Tesseract language pack.')}</small></div>
          <div className="form-field"><label htmlFor="output-language">{t("Explanation language")}</label><div className="select-wrap"><select id="output-language" value={language} onChange={(e) => setLanguage(e.target.value)}>{LANGUAGE_OPTIONS.map((item) => { const supported = translationStatus?.supported_output_codes || []; const needsTranslator = !['en', 'hinglish'].includes(item.value); const disabled = needsTranslator && (!translationStatus?.ready || !supported.includes(item.value)); return <option key={item.value} value={item.value} disabled={disabled}>{item.label}{disabled ? ` · ${t('model unavailable')}` : ''}</option>; })}</select><ChevronDown size={16} /></div><small className="field-hint">{t('Non-English review uses a configured LibreTranslate service. Original wording is preserved for comparison.')}</small></div>
        </div>
        <label className="checkbox-row"><input type="checkbox" checked={persist} onChange={(e) => setPersist(e.target.checked)} /><span className="fake-checkbox"><Check size={12} /></span><span><strong>{t('Save this analysis in my history')}</strong><small>{t('Uncheck this if you do not want the report saved to your local document history.')}</small></span></label>
        <div className="analysis-submit-row"><button className="button button-primary button-large" onClick={() => onAnalyze({ file: inputMode === 'file' ? file : null, text: inputMode === 'text' ? draftText : '', docType, sourceLanguage })} disabled={busy || !(inputMode === 'file' ? file : draftText.trim())}>{busy ? <><LoaderCircle className="spin" size={17} />{t('Analyzing agreement…')}</> : <><Sparkles size={17} />{t('Analyze agreement')} <ArrowRight size={16} /></>}</button><button className="button button-quiet" onClick={onClear} disabled={busy}>{t('Reset')}</button><button className="text-button sample-link" onClick={() => onSample(docType)} disabled={busy}><BookOpen size={15} />{t('Use a sample')}</button></div>
        {busy && <div className="analysis-progress"><div className="progress-track"><span /></div><p>{t('Extracting text, reviewing clauses and preparing a risk summary. Longer agreements can take a little more time.')}</p></div>}
      </div>
      <aside className="analysis-aside">
        <div className="card aside-card"><div className="aside-card-title"><ShieldCheck size={18} /><h3>{t("What you'll get")}</h3></div><div className="benefit-row"><span className="benefit-number">01</span><div><strong>{t('Risk overview')}</strong><p>{t('A high-level view of clauses flagged for closer attention.')}</p></div></div><div className="benefit-row"><span className="benefit-number">02</span><div><strong>{t('Plain-language explanations')}</strong><p>{t('Clause-by-clause explanations to help you understand the wording.')}</p></div></div><div className="benefit-row"><span className="benefit-number">03</span><div><strong>{t('Key terms & missing items')}</strong><p>{t('Important amounts, timelines and a checklist of potential gaps.')}</p></div></div></div>
        <div className="card aside-card privacy-aside"><div className="privacy-aside-icon"><LockKeyhole size={19} /></div><h3>{t('Handle documents carefully')}</h3><p>{t('Personal identifiers such as certain account numbers and contact details are masked before analysis. Names and addresses may remain in the text.')}</p><button className="text-button" onClick={() => window.dispatchEvent(new CustomEvent('clauselens-navigate', { detail: 'privacy' }))}>{t('Privacy details')} <ArrowRight size={14} /></button></div>
        <div className="aside-disclaimer"><Info size={16} /><p>{t('ClauseLens is an awareness tool, not a replacement for legal advice. Risk flags are heuristics.')}</p></div>
      </aside>
    </div>
  </div>;
}

function DashboardListPage({ title, eyebrow, description, reports, loading, onOpen, onDelete, onNew, query, setQuery }) {
  const t = useT();
  const [filter, setFilter] = useState('all');
  const filtered = reports.filter((item) => filter === 'all' || item.overall_risk === filter);
  return <div className="page-stack">
    <PageHeading eyebrow={eyebrow} title={title} description={description} action="New analysis" onAction={onNew} />
    <div className="card documents-page-card">
      <div className="documents-toolbar"><div className="filter-pills"><button className={filter === 'all' ? 'filter-pill active' : 'filter-pill'} onClick={() => setFilter('all')}>{t('All documents')} <span>{reports.length}</span></button><button className={filter === 'red' ? 'filter-pill active' : 'filter-pill'} onClick={() => setFilter('red')}>{t('High risk')}</button><button className={filter === 'amber' ? 'filter-pill active' : 'filter-pill'} onClick={() => setFilter('amber')}>{t('Medium risk')}</button><button className={filter === 'green' ? 'filter-pill active' : 'filter-pill'} onClick={() => setFilter('green')}>{t('Low risk')}</button></div><div className="list-search"><Search size={15} /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t("Filter documents")} aria-label={t("Filter documents")} />{query && <button onClick={() => setQuery('')} aria-label={t("Clear filter")}><X size={14} /></button>}</div></div>
      <ReportList reports={filtered} loading={loading} onOpen={onOpen} onDelete={onDelete} onStart={onNew} query={query} emptyTitle="No saved documents" emptyDescription="Your analyzed agreements will appear here when saved." />
    </div>
  </div>;
}

function MetricMini({ label, value, detail, tone = 'blue' }) {
  const t = useT();
  return <div className={`report-metric metric-${tone}`}><span>{t(label)}</span><strong>{value}</strong><small>{t(detail)}</small></div>;
}

function PrintableReport({ report, reportTitle, summary, clauses, facts, score, question, answer }) {
  const t = useT();
  const counts = summary.counts || {};
  const riskOrder = { red: 0, amber: 1, green: 2 };
  const prioritized = [...clauses].sort((a, b) => (riskOrder[a.risk] ?? 3) - (riskOrder[b.risk] ?? 3));
  const missing = report?.missing || [];
  const overallRisk = summary.overall_risk || 'green';
  const riskText = summary.display_risk_labels?.[overallRisk] || riskLabel(overallRisk);
  const riskDescription = summary.display_risk_description || summary.overall_label || '';
  const disclaimer = report.disclaimer || 'ClauseLens is an awareness tool, not legal advice. Risk labels are indicators, not a legal verdict. Have important clauses reviewed by a qualified advocate.';

  return <article className="print-only-report">
    <header className="print-report-header">
      <div className="print-brand-line"><span className="print-brand-mark">CL</span><div><strong>ClauseLens</strong><small>{t('Full agreement analysis report')}</small></div></div>
      <h1>{reportTitle}</h1>
      <p className="print-meta">{t('Report ID')}: CL-{String(report.report_id || '').slice(0, 8).toUpperCase()} <span>·</span> {t('Analyzed on')} {dateLabel(report.created_utc)}</p>
      {report.source_language_name && <p className="print-meta">{t('Source document language')}: {report.source_language_name}</p>}
      <div className="print-summary-grid">
        <div className="print-summary-card"><span>{t('OVERALL RISK SCORE')}</span><strong>{score}/100</strong><b className={`print-risk print-risk-${overallRisk}`}>{t(riskText)}</b></div>
        <div className="print-summary-card"><span>{t('High-risk clauses')}</span><strong>{formatCount(counts.red)}</strong></div>
        <div className="print-summary-card"><span>{t('Medium-risk clauses')}</span><strong>{formatCount(counts.amber)}</strong></div>
        <div className="print-summary-card"><span>{t('Lower-risk clauses')}</span><strong>{formatCount(counts.green)}</strong></div>
      </div>
      {riskDescription && <p className="print-summary-description">{t(riskDescription)}</p>}
      {report.translation_notice && <p className="print-translation-notice">{report.translation_notice}</p>}
    </header>

    <section className="print-section">
      <h2>{t('Executive summary')}</h2>
      <p>{t(summary.overall_label || riskDescription || 'Review the clauses below alongside the original agreement wording.')}</p>
      <p>{t('This report is a screening aid. It does not determine whether a clause is enforceable.')}</p>
    </section>

    <section className="print-section">
      <h2>{t('Key terms and amounts')}</h2>
      {facts.length ? <div className="print-facts-grid">{facts.map((fact, index) => <div className="print-fact" key={`${fact.clause_index}-${fact.type}-${index}`}>
        <span>{t(fact.display_type || cap(fact.type || 'Key term'))}{fact.role ? ` · ${t(fact.display_role || cap(fact.role))}` : ''}</span>
        <strong>{fact.text || fact.value || '—'}</strong>
        {fact.clause_index !== undefined && <small>{t('Clause')} {fact.clause_index}</small>}
      </div>)}</div> : <p>{t('No financial amounts or time periods were extracted from this agreement.')}</p>}
    </section>

    <section className="print-section">
      <h2>{t('Potentially missing terms')}</h2>
      {missing.length ? <ul className="print-list">{missing.map((item, index) => <li key={`${item.clause_id}-${index}`}><strong>{t(item.name || cap(item.clause_id || 'Unidentified term'))}</strong>{item.message ? <span>{t(item.message)}</span> : null}</li>)}</ul> : <p>{t('No likely gaps were detected by the current checklist.')}</p>}
    </section>

    <section className="print-section">
      <h2>{t('Priority findings')}</h2>
      {prioritized.filter((clause) => clause.risk === 'red' || clause.risk === 'amber').length ? prioritized.filter((clause) => clause.risk === 'red' || clause.risk === 'amber').map((clause, index) => <article className="print-finding" key={`finding-${clause.index ?? index}`}>
        <div className="print-item-head"><h3>{t(clauseName(clause))}</h3><span className={`print-risk print-risk-${riskLevel(clause.risk)}`}>{t(clause.display_risk_label || riskLabel(clause.risk))}</span></div>
        {clause.flags?.length > 0 && <p className="print-flag-line">{clause.flags.map((flag) => t(flag.display_text || cap(flag.flag))).filter(Boolean).join(' · ')}</p>}
        {clause.explanation?.summary && <p>{clause.explanation.summary}</p>}
      </article>) : <p>{t('No high or medium risk clauses were flagged by the current rules.')}</p>}
    </section>

    {answer && <section className="print-section">
      <h2>{t('Question and answer')}</h2>
      {question && <p><strong>{t('Question')}:</strong> {question}</p>}
      <p><strong>{t('Answer')}:</strong> {answer.answer}</p>
      {answer.citations?.length > 0 && <p><strong>{t('Source clauses')}:</strong> {answer.citations.map((citation) => `${t('Clause')} ${citation.number || citation.index}${citation.heading ? ` (${citation.heading})` : ''}`).join('; ')}</p>}
    </section>}

    <section className="print-section print-all-clauses">
      <h2>{t('Full clause-by-clause review')}</h2>
      <p className="print-section-intro">{t('Every extracted segment is included below, regardless of which report tab was open when PDF export was selected.')}</p>
      {clauses.length ? clauses.map((clause, index) => <article className="print-clause" key={`clause-${clause.index ?? index}`}>
        <div className="print-item-head"><h3>{t('Clause')} {clause.number || clause.index || index + 1}: {t(clauseName(clause))}</h3>{clause.risk && <span className={`print-risk print-risk-${riskLevel(clause.risk)}`}>{t(clause.display_risk_label || riskLabel(clause.risk))}</span>}</div>
        {(clause.original_text || ['en', 'hinglish'].includes(report.source_language || 'en'))
          ? <><div className="print-label">{t('Original agreement wording')}</div><blockquote>{clause.original_text || clause.text || t('Original wording was not separately matched.')}</blockquote></>
          : <><div className="print-label">{t('Original wording could not be matched confidently')}</div><p>{t('The system could not confidently map this translated finding back to an exact source-language segment.')}</p><div className="print-label">{t('Text used for classification (English translation)')}</div><blockquote>{clause.text || t('No text available.')}</blockquote></>}
        <div className="print-label">{t('Plain-language explanation')}</div>
        <p>{clause.explanation?.summary || clause.explanation?.text || t('No plain-language explanation was generated for this segment.')}</p>
        {clause.explanation?.facts_line && <p><strong>{t('Key terms:')}</strong> {clause.explanation.facts_line}</p>}
        {clause.explanation?.reasons?.length > 0 && <><div className="print-label">{t('Why this matters')}</div><ul className="print-list">{clause.explanation.reasons.map((reason, i) => <li key={i}>{reason}</li>)}</ul></>}
        {clause.explanation?.tips?.length > 0 && <><div className="print-label">{t('Suggested next steps')}</div><ul className="print-list">{clause.explanation.tips.map((tip, i) => <li key={i}>{tip}</li>)}</ul></>}
        {clause.flags?.length > 0 && <p className="print-flag-line"><strong>{t('Risk indicators')}:</strong> {clause.flags.map((flag) => t(flag.display_text || cap(flag.flag))).filter(Boolean).join(' · ')}</p>}
      </article>) : <p>{t('No clause segments were detected in this report.')}</p>}
    </section>

    <footer className="print-report-footer">
      <h2>{t('Legal disclaimer')}</h2>
      <p>{t(disclaimer)}</p>
      <p>{t('Important: Translation may miss legal nuance. Verify all translated explanations against the original agreement.')}</p>
      <small>ClauseLens · {t('Local-first agreement review')} · {t('Not legal advice')}</small>
    </footer>
  </article>;
}

function ReportView({ report, language, uiLanguage, translationStatus, reportTranslationWarning, onBack, onAnalyze, onPrint, isSaved, onToggleSaved, onReportLanguageChange }) {
  const t = useT();
  const [selectedIndex, setSelectedIndex] = useState(null);
  const [activeTab, setActiveTab] = useState('summary');
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState(null);
  const [asking, setAsking] = useState(false);
  const [notes, setNotes] = useState('');
  const [copied, setCopied] = useState(false);
  const summary = report?.summary || {};
  const clauses = report?.clauses || [];
  const assessedClauses = clauses.filter((c) => c.risk);
  const counts = summary.counts || {};
  const selectedClause = selectedIndex === null ? null : clauses.find((c) => c.index === selectedIndex) || clauses[selectedIndex] || null;
  const highFlags = clauses.filter((c) => c.risk === 'red');
  const facts = report?.key_facts || [];
  const score = reportScore(report);
  const reportTitle = `${t(docName(report))} · ${dateLabel(report.created_utc)}`;
  const askQuestion = async (event) => {
    event.preventDefault();
    if (!question.trim()) return;
    setAsking(true); setAnswer(null);
    try { setAnswer(await api.ask(report, question.trim(), language)); }
    catch (error) { setAnswer({ answer: error.message || 'Unable to retrieve an answer.', found: false, citations: [] }); }
    finally { setAsking(false); }
  };
  const copyText = async (text) => {
    try { await navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 1600); }
    catch { window.prompt('Copy this text:', text); }
  };
  return <div className="page-stack report-page">
    <PrintableReport report={report} reportTitle={reportTitle} summary={summary} clauses={clauses} facts={facts} score={score} question={question} answer={answer} />
    <div className="report-back-row"><button className="text-button" onClick={onBack}><ChevronLeft size={16} />{t('Back to documents')}</button><div className="report-meta-inline"><span className="status-check"><CheckCircle2 size={14} />{t('Analysis complete')}</span><span><Clock3 size={14} />{dateLabel(report.created_utc)}</span></div></div>
    <div className="report-title-card card"><div className="report-title-icon"><FileText size={22} /></div><div className="report-title-content"><div className="report-eyebrow">{t('ANALYSIS REPORT')} <span>·</span> CL-{String(report.report_id || '').slice(0, 8).toUpperCase()}</div><h1>{reportTitle}</h1><div className="report-title-tags"><span className="type-chip">{t(docName(report))}</span><RiskBadge risk={summary.overall_risk}>{summary.display_risk_labels?.[summary.overall_risk] || riskLabel(summary.overall_risk)}</RiskBadge><span className="muted-tag">{formatCount(clauses.length)} {t('segments detected')}</span></div></div><div className="report-header-actions"><label className="report-language-label"><span>{t('Report language')}</span><select className="report-language-select" aria-label={t('Report language')} value={language} onChange={(event) => onReportLanguageChange(event.target.value)}>{LANGUAGE_OPTIONS.filter((item) => item.value !== 'hinglish').map((item) => { const disabled = item.value !== 'en' && (!translationStatus?.ready || !(translationStatus.supported_output_codes || []).includes(item.value)); return <option key={item.value} value={item.value} disabled={disabled}>{item.label}{disabled ? ` · ${t('model unavailable')}` : ''}</option>; })}</select></label><button className="button button-secondary" onClick={onPrint}><Printer size={15} />{t('Download PDF')}</button><button className={cx("button", "button-secondary", isSaved && "saved-action")} onClick={onToggleSaved}><Bookmark size={15} fill={isSaved ? "currentColor" : "none"} />{isSaved ? t('Saved') : t('Save analysis')}</button><button className="button button-primary" onClick={onAnalyze}><Plus size={15} />{t('New review')}</button><button className="icon-button bordered-icon" aria-label={t("More report options")} title={t("More report options")} onClick={() => window.print()}><MoreHorizontal size={18} /></button></div></div>
    {reportTranslationWarning && <div className="translation-notice translation-service-note" role="status"><Info size={16} /><span>{t('Report translation failed. The original report is still displayed.')} {reportTranslationWarning}</span></div>}
    {uiLanguage === 'hi' && language === 'en' && !translationStatus?.ready && !reportTranslationWarning && <div className="translation-notice translation-service-note" role="status"><Info size={16} /><span>{t('The interface is in Hindi, but this report remains in English because the translation service is not running. Start local LibreTranslate to translate report explanations.')}</span></div>}
    {report.translation_notice && <div className="translation-notice" role="note"><Info size={16} /><span>{report.translation_notice}</span></div>}
    <div className="report-metrics-grid"><div className="score-card card"><div className="score-card-heading"><span>{t('OVERALL RISK SCORE')}</span><RiskBadge risk={summary.overall_risk}>{summary.display_risk_labels?.[summary.overall_risk] || riskLabel(summary.overall_risk)}</RiskBadge></div><div className="score-middle"><div className="score-ring" style={{ '--score': `${score}%` }}><div><strong>{score}</strong><small>/100</small></div></div><div className="score-copy"><h3>{t(summary.overall_label || riskLabel(summary.overall_risk))}</h3><p>{t(summary.display_risk_description || (summary.overall_risk === 'red' ? 'Several clauses may deserve careful review before you proceed.' : summary.overall_risk === 'amber' ? 'Some clauses could benefit from clarification or negotiation.' : 'No high-severity flags were identified by the current rules.'))}</p></div></div><div className="score-foot"><Info size={13} />{t('A screening indicator, not a legal judgment.')}</div></div>
      <MetricMini label="High-risk clauses" value={formatCount(counts.red)} detail="Prioritize these first" tone="red" /><MetricMini label="Medium-risk clauses" value={formatCount(counts.amber)} detail="Clarify before signing" tone="amber" /><MetricMini label="Key terms extracted" value={formatCount(facts.length)} detail="Amounts, dates and periods" tone="blue" /></div>
    <div className="report-tabs"><button className={activeTab === 'summary' ? 'report-tab active' : 'report-tab'} onClick={() => setActiveTab('summary')}><Gauge size={16} />{t('Summary')}</button><button className={activeTab === 'clauses' ? 'report-tab active' : 'report-tab'} onClick={() => setActiveTab('clauses')}><FileSearch size={16} />{t('Clause explorer')} <span>{clauses.length}</span></button><button className={activeTab === 'questions' ? 'report-tab active' : 'report-tab'} onClick={() => setActiveTab('questions')}><MessageSquareText size={16} />{t('Ask this agreement')}</button></div>
    {activeTab === 'summary' && <div className="report-content-grid"><div className="report-main-column">
      <RiskDistribution summary={summary} />
      <div className="card findings-card"><div className="card-heading"><div><h3>{t('Key findings to review')}</h3><p>{t('Clauses with the highest assigned risk levels')}</p></div><button className="text-button" onClick={() => setActiveTab('clauses')}>{t('Explore clauses')} <ArrowRight size={14} /></button></div>
        {highFlags.length ? <div className="findings-list">{[...highFlags, ...assessedClauses.filter((c) => c.risk === 'amber')].slice(0, 5).map((clause) => <button key={clause.index} className="finding-row" onClick={() => { setSelectedIndex(clause.index); setActiveTab('clauses'); }}><span className={`finding-icon finding-${riskLevel(clause.risk)}`}><AlertTriangle size={16} /></span><span className="finding-body"><strong>{t(clauseName(clause))}</strong><small>{(clause.flags || []).map((f) => t(f.display_text || f.flag)).filter(Boolean).join(' · ') || clause.explanation?.summary || clause.text?.slice(0, 100)}</small></span><RiskBadge risk={clause.risk}>{clause.display_risk_label || riskLabel(clause.risk)}</RiskBadge><ChevronRight size={16} className="finding-arrow" /></button>)}</div> : assessedClauses.length ? <div className="findings-list">{assessedClauses.slice(0, 5).map((clause) => <button key={clause.index} className="finding-row" onClick={() => { setSelectedIndex(clause.index); setActiveTab('clauses'); }}><span className="finding-icon finding-amber"><Info size={16} /></span><span className="finding-body"><strong>{t(clauseName(clause))}</strong><small>{clause.explanation?.summary || clause.text?.slice(0, 100)}</small></span><RiskBadge risk={clause.risk}>{clause.display_risk_label || riskLabel(clause.risk)}</RiskBadge><ChevronRight size={16} className="finding-arrow" /></button>)}</div> : <div className="inline-empty"><ShieldCheck size={18} /><span>{t('No clauses received a risk classification in this report.')}</span></div>}
      </div>
      <div className="card key-facts-card"><div className="card-heading"><div><h3>{t('Key terms found')}</h3><p>{t('Details extracted directly from the agreement text')}</p></div><span className="subtle-count">{facts.length} {t("items")}</span></div>{facts.length ? <div className="facts-grid">{facts.slice(0, 8).map((fact, i) => <div className="fact-item" key={`${fact.clause_index}-${fact.type}-${i}`}><span>{t(fact.display_type || cap(fact.type))}{fact.role ? ` · ${t(fact.display_role || cap(fact.role))}` : ''}</span><strong>{fact.text}</strong><button className="fact-source" onClick={() => { setSelectedIndex(fact.clause_index); setActiveTab('clauses'); }}>{t('View clause')} <ArrowUpRight size={12} /></button></div>)}</div> : <p className="empty-inline-copy">{t('No financial amounts or time periods were extracted from this agreement.')}</p>}</div>
    </div><aside className="report-aside-column">
      <div className="card missing-card"><div className="aside-card-title"><ListChecks size={18} /><h3>{t('Potentially missing terms')}</h3><span className="subtle-count">{report.missing?.length || 0}</span></div>{report.missing?.length ? <><p className="aside-copy">{t("These items weren't clearly identified by the current review. Confirm whether they apply to your agreement.")}</p><ul className="missing-list">{report.missing.slice(0, 6).map((item, i) => <li key={`${item.clause_id}-${i}`}><span><AlertCircle size={14} /></span><div><strong>{t(item.name || cap(item.clause_id))}</strong><small>{t(item.message)}</small></div></li>)}</ul>{report.missing.length > 6 && <button className="text-button" onClick={() => setActiveTab('clauses')}>{t("Review all")} {report.missing.length} {t("items")} <ArrowRight size={14} /></button>}</> : <div className="inline-empty compact"><CheckCircle2 size={17} /><span>{t("No likely gaps were detected by the current checklist.")}</span></div>}</div>
      <div className="card ask-card"><div className="ask-card-head"><span className="ask-icon"><MessageSquareText size={17} /></span><div><h3>{t('Ask your agreement')}</h3><p>{t('Find a clause that answers your question.')}</p></div></div><form onSubmit={askQuestion}><label className="sr-only" htmlFor="report-question">{t('Ask a question about this agreement')}</label><input id="report-question" className="ask-input" value={question} onChange={(e) => setQuestion(e.target.value)} placeholder={t('Ask about the security deposit, notice period, penalties, responsibilities, or another clause…')} /><button className="button button-primary ask-submit" disabled={asking || !question.trim()}>{asking ? <LoaderCircle className="spin" size={15} /> : <Send size={15} />}{t('Ask question')}</button></form>{answer && <div className={cx('answer-box', !answer.found && 'answer-not-found')}><strong>{t(answer.found ? 'Answer from the agreement' : 'No clear answer found')}</strong><p>{answer.answer}</p>{answer.citations?.map((cite) => <button className="citation-link" key={cite.index} onClick={() => { setSelectedIndex(cite.index); setActiveTab('clauses'); }}>{t('Clause')} {cite.number || cite.index} · {t('View source')} <ArrowUpRight size={12} /></button>)}</div>}<button className="text-button full-link" onClick={() => setActiveTab('questions')}>{t('Open full question workspace')} <ArrowRight size={14} /></button></div>
    </aside></div>}
    {activeTab === 'clauses' && <div className="clause-explorer-grid"><div className="card clause-list-card"><div className="clause-list-heading"><div><h3>{t('Clause explorer')}</h3><p>{clauses.length} {t('agreement segments')}</p></div><span className="small-muted">{t('Select a clause')}</span></div><div className="clause-list">{clauses.map((clause, index) => <button key={`${clause.index}-${index}`} className={cx('clause-list-item', selectedIndex === clause.index && 'selected', clause.risk && `clause-list-${clause.risk}`)} onClick={() => setSelectedIndex(clause.index)}><span className="clause-list-number">{clause.number || String(index + 1).padStart(2, '0')}</span><span className="clause-list-copy"><strong>{t(clauseName(clause))}</strong><small>{(clause.original_text || clause.text || '').slice(0, 70)}{(clause.original_text || clause.text || '').length > 70 ? '…' : ''}</small></span>{clause.risk && <span className={`mini-risk mini-risk-${clause.risk}`} />}</button>)}</div></div>
      <div className="card clause-detail-card">{selectedClause ? <><div className="clause-detail-top"><div><div className="section-kicker">{t('Clause')} {selectedClause.number || selectedClause.index || ''}</div><h2>{t(clauseName(selectedClause))}</h2></div>{selectedClause.risk && <RiskBadge risk={selectedClause.risk}>{selectedClause.display_risk_label || riskLabel(selectedClause.risk)}</RiskBadge>}</div><div className="clause-panel-label"><FileText size={15} />{(selectedClause.original_text || ['en', 'hinglish'].includes(report.source_language || 'en')) ? t('ORIGINAL AGREEMENT TEXT') : t('TEXT USED FOR CLASSIFICATION (ENGLISH TRANSLATION)')}</div>{!selectedClause.original_text && !['en', 'hinglish'].includes(report.source_language || 'en') && <p className="translation-notice">{t('The system could not confidently match this finding to the exact original clause. The wording below is the English translation used for classification.')}</p>}<blockquote className="original-clause">{selectedClause.original_text || selectedClause.text}</blockquote><div className="clause-panel-label explanation-label"><Sparkles size={15} />{t('PLAIN-LANGUAGE EXPLANATION')}</div><div className="explanation-panel"><p>{selectedClause.explanation?.summary || selectedClause.explanation?.text || t('No plain-language explanation was generated for this segment. Review the wording carefully.')}</p>{selectedClause.explanation?.facts_line && <small className="explanation-facts">{t("Key terms:")} {selectedClause.explanation.facts_line}</small>}</div>{selectedClause.flags?.length > 0 && <div className="clause-flags"><h4><AlertTriangle size={15} />{t('Risk indicators')}</h4><div className="flag-chips">{selectedClause.flags.map((flag, i) => <span key={`${flag.flag}-${i}`} className={`flag-chip flag-${riskLevel(flag.level)}`}>{t(flag.display_text || cap(flag.flag))}</span>)}</div></div>}<div className="clause-action-row"><button className="button button-secondary" onClick={() => copyText(`${clauseName(selectedClause)}\n\nOriginal text:\n${selectedClause.original_text || selectedClause.text}\n\nExplanation:\n${selectedClause.explanation?.summary || selectedClause.explanation?.text || ''}`)}><Copy size={15} />{copied ? t('Copied') : t('Copy explanation')}</button><button className="button button-primary" onClick={() => { setQuestion(`Explain the ${clauseName(selectedClause)} clause and any key obligations.`); setActiveTab('questions'); }}><MessageSquareText size={15} />{t('Ask about this clause')}</button></div></> : <EmptyState icon={FileSearch} title="Select a clause" description="Choose an item from the clause list to inspect the original wording and its explanation." />}</div></div>}
    {activeTab === 'questions' && <div className="card question-workspace"><div className="question-header"><IconBox icon={MessageSquareText} tone="blue" size={20} /><div><h2>{t('Ask your agreement')}</h2><p>{t('Answers are retrieved from the analyzed agreement text and show source clauses when a match is found.')}</p></div></div><form className="question-form" onSubmit={askQuestion}><label htmlFor="full-question">{t('Your question')}</label><textarea id="full-question" className="question-textarea" rows="3" value={question} onChange={(e) => setQuestion(e.target.value)} placeholder={t('Ask about the security deposit, notice period, penalties, responsibilities, or another clause…')}/><div className="question-form-footer"><span>{`${t('Response language')}: ${languageLabel(language)}`}</span><button className="button button-primary" disabled={asking || !question.trim()}>{asking ? <LoaderCircle className="spin" size={15} /> : <Send size={15} />}{t('Find answer')}</button></div></form>{answer ? <div className={cx('answer-large', !answer.found && 'answer-not-found')}><div className="answer-large-title"><CheckCircle2 size={18} /><strong>{t(answer.found ? 'Relevant wording found' : 'No clear answer found')}</strong></div><p>{answer.answer}</p>{answer.citations?.length > 0 && <div className="citation-cards"><h4>{t('Source clauses')}</h4>{answer.citations.map((citation) => <button key={citation.index} onClick={() => { setSelectedIndex(citation.index); setActiveTab('clauses'); }}><span><strong>{t('Clause')} {citation.number || citation.index}</strong><small>{t(citation.heading || 'Agreement clause')}</small></span><ChevronRight size={16} /></button>)}</div>}</div> : <div className="question-suggestions"><span>{t('Try asking')}</span>{['When is the security deposit refunded?', 'What is the notice period?', 'What happens if I leave early?'].map((suggestion) => <button key={suggestion} onClick={() => setQuestion(t(suggestion))}>{t(suggestion)}<ArrowUpRight size={13} /></button>)}</div>}</div>}
    <div className="report-disclaimer"><ShieldCheck size={16} /><p>{t(report.disclaimer || 'ClauseLens is an awareness tool, not legal advice. Risk labels are indicators, not a legal verdict. Have important clauses reviewed by a qualified advocate.')}</p><button onClick={() => window.print()}><Printer size={14} />{t('Print / save as PDF')}</button></div>
  </div>;
}

function SimpleInfoPage({ page, onNew }) {
  const t = useT();
  const content = {
    saved: { eyebrow: 'YOUR SHORTLIST', title: 'Saved analyses', desc: 'Keep the reports you want to revisit close at hand.', icon: Bookmark, body: 'Saved items are managed in your local browser session. Open a report and use your browser print dialog to save a copy as PDF.' },
    settings: { eyebrow: 'PREFERENCES', title: 'Workspace settings', desc: 'Manage the way ClauseLens behaves on this device.', icon: Settings, body: 'Language and save-history preferences are available during each new analysis. This local workspace does not currently use user accounts or cloud sync.' },
    help: { eyebrow: 'SUPPORT CENTRE', title: 'How can we help?', desc: 'Get familiar with the main ClauseLens workflow.', icon: LifeBuoy, body: 'Upload a PDF, DOCX, TXT or MD agreement, select English or Hinglish, then run the analysis. Review risk flags alongside the original text and discuss important concerns with a qualified legal professional.' },
    privacy: { eyebrow: 'YOUR DATA', title: 'Privacy & security', desc: 'Understand how documents are processed by this local application.', icon: LockKeyhole, body: 'The provided backend masks several structured identifiers before analysis, but names and addresses may remain. Saved reports are stored in the local SQLite database. Uncheck “Save this analysis in my history” if you do not want a report saved.' },
  }[page] || { eyebrow: 'WORKSPACE', title: 'ClauseLens', desc: 'Review agreements with greater clarity.', icon: ShieldCheck, body: 'Return to the dashboard to see recent activity.' };
  const Icon = content.icon;
  return <div className="page-stack"><PageHeading eyebrow={content.eyebrow} title={content.title} description={content.desc} action="New analysis" onAction={onNew} /><div className="info-page-grid"><div className="card info-hero-card"><div className="info-page-icon"><Icon size={26} /></div><h2>{t(content.title)}</h2><p>{t(content.body)}</p><button className="button button-primary" onClick={onNew}><Plus size={16} />{t('Analyze an agreement')}</button></div><div className="card info-facts-card"><h3>{t('Good to know')}</h3><div className="info-fact"><ShieldCheck size={17} /><div><strong>{t('Risk flags are screening indicators')}</strong><p>{t('They help identify wording that may deserve closer review; they do not determine legal enforceability.')}</p></div></div><div className="info-fact"><FileText size={17} /><div><strong>{t('Check the original wording')}</strong><p>{t('Always compare explanations with the clause in your actual agreement.')}</p></div></div><div className="info-fact"><LockKeyhole size={17} /><div><strong>{t('Review privacy before upload')}</strong><p>{t('Avoid uploading documents you are not permitted to share or process on this device.')}</p></div></div></div></div></div>;
}

function Toast({ toast, onClose }) {
  const t = useT();
  if (!toast) return null;
  return <div className={cx('toast', toast.kind === 'error' && 'toast-error')} role="status"><span>{toast.kind === 'error' ? <AlertCircle size={17} /> : <CheckCircle2 size={17} />}</span><p>{toast.message}</p><button onClick={onClose} aria-label={t('Dismiss notification')}><X size={16} /></button></div>;
}

export default function App() {
  const [view, setView] = useState('dashboard');
  const [reports, setReports] = useState([]);
  const [loadingReports, setLoadingReports] = useState(true);
  const [backendStatus, setBackendStatus] = useState('checking');
  const [translationStatus, setTranslationStatus] = useState(null);
  const [reportTranslationWarning, setReportTranslationWarning] = useState('');
  const [activeReport, setActiveReport] = useState(null);
  const [canonicalReport, setCanonicalReport] = useState(null);
  const [previousView, setPreviousView] = useState('documents');
  const [language, setLanguage] = useState('en');
  const [uiLanguage, setUiLanguage] = useState(() => {
    try { return localStorage.getItem('clauselens:uiLanguage') === 'hi' ? 'hi' : 'en'; }
    catch { return 'en'; }
  });
  const [sourceLanguage, setSourceLanguage] = useState('auto');
  const [query, setQuery] = useState('');
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [draftText, setDraftText] = useState('');
  const [file, setFile] = useState(null);
  const [inputMode, setInputMode] = useState('file');
  const [persist, setPersist] = useState(true);
  const [savedIds, setSavedIds] = useState(() => {
    try { return JSON.parse(localStorage.getItem('clauselens:savedReports') || '[]'); }
    catch { return []; }
  });
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState(null);

  const showToast = useCallback((message, kind = 'success') => {
    setToast({ message, kind });
    window.clearTimeout(window.__clauseLensToastTimer);
    window.__clauseLensToastTimer = window.setTimeout(() => setToast(null), 4200);
  }, []);

  const refreshReports = useCallback(async () => {
    setLoadingReports(true);
    try { const data = await api.reports(); setReports(Array.isArray(data) ? data : []); }
    catch (error) { showToast(`Could not load document history: ${error.message}`, 'error'); }
    finally { setLoadingReports(false); }
  }, [showToast]);

  useEffect(() => {
    api.health().then(() => setBackendStatus('online')).catch(() => setBackendStatus('offline'));
    refreshReports();
  }, [refreshReports]);

  // Re-check periodically while translation is offline. This lets a user start LibreTranslate
  // in another terminal without closing or manually reloading the React app.
  useEffect(() => {
    let cancelled = false;
    let timer;
    const checkTranslation = async () => {
      try {
        const status = await api.translationStatus();
        if (cancelled) return;
        setTranslationStatus(status);
        if (!status?.ready) timer = window.setTimeout(checkTranslation, 12000);
      } catch {
        if (cancelled) return;
        setTranslationStatus({ ready: false, supported_output_codes: [], supported_source_codes_to_english: [] });
        timer = window.setTimeout(checkTranslation, 12000);
      }
    };
    checkTranslation();
    return () => {
      cancelled = true;
      if (timer) window.clearTimeout(timer);
    };
  }, []);

  useEffect(() => {
    try { localStorage.setItem('clauselens:savedReports', JSON.stringify(savedIds)); } catch { /* Storage can be disabled in private browsing. */ }
  }, [savedIds]);

  useEffect(() => {
    try { localStorage.setItem('clauselens:uiLanguage', uiLanguage); } catch { /* Storage can be disabled in private browsing. */ }
  }, [uiLanguage]);

  useEffect(() => {
    const onNavigate = (event) => setView(event.detail);
    const onToast = (event) => showToast(event.detail.message, event.detail.kind || 'success');
    const onKey = (event) => { if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') { event.preventDefault(); document.querySelector('.global-search input')?.focus(); } if (event.key === 'Escape') setMobileNavOpen(false); };
    window.addEventListener('clauselens-navigate', onNavigate); window.addEventListener('clauselens-toast', onToast); window.addEventListener('keydown', onKey);
    return () => { window.removeEventListener('clauselens-navigate', onNavigate); window.removeEventListener('clauselens-toast', onToast); window.removeEventListener('keydown', onKey); };
  }, [showToast]);

  const openReport = useCallback(async (id) => {
    let detail;
    try {
      detail = await api.report(id);
    } catch (error) {
      showToast(`Could not open this report: ${error.message}`, 'error');
      return;
    }
    setPreviousView(view === 'report' ? previousView : view === 'dashboard' ? 'dashboard' : view);
    setCanonicalReport(detail);
    let displayReport = detail;
    let fallbackMessage = '';
    setReportTranslationWarning('');
    if (language !== 'en') {
      try {
        displayReport = await api.translateReport(detail, language);
      } catch (error) {
        // A saved report must remain accessible even when the translator is not running.
        setLanguage('en');
        setReportTranslationWarning(error.message || 'Translation is unavailable.');
        fallbackMessage = `The report opened in English because translation was unavailable: ${error.message}`;
      }
    }
    setActiveReport({ ...displayReport, canonical_report: detail });
    setView('report'); setMobileNavOpen(false); setQuery('');
    if (fallbackMessage) showToast(fallbackMessage, 'error');
  }, [view, previousView, language, showToast]);

  const changeReportLanguage = async (nextLanguage) => {
    if (nextLanguage === language) return;
    if (view === 'report' && canonicalReport) {
      if (nextLanguage === 'en') {
        setReportTranslationWarning('');
        setLanguage(nextLanguage);
        setActiveReport({ ...canonicalReport, canonical_report: canonicalReport });
        return;
      }
      try {
        const translated = await api.translateReport(canonicalReport, nextLanguage);
        setCanonicalReport(translated.canonical_report || canonicalReport);
        setActiveReport({ ...translated, canonical_report: translated.canonical_report || canonicalReport });
        setLanguage(nextLanguage);
        setReportTranslationWarning('');
      } catch (error) {
        setReportTranslationWarning(error.message || 'Translation is unavailable.');
        showToast(`Could not translate this report: ${error.message}`, 'error');
      }
      return;
    }
    setLanguage(nextLanguage);
  };

  const changeInterfaceLanguage = async (nextUiLanguage) => {
    setUiLanguage(nextUiLanguage);
    if (view !== 'report' || !canonicalReport) return;
    if (nextUiLanguage === 'en') {
      await changeReportLanguage('en');
      return;
    }
    try {
      const translated = await api.translateReport(canonicalReport, 'hi');
      const base = translated.canonical_report || canonicalReport;
      setCanonicalReport(base);
      setActiveReport({ ...translated, canonical_report: base });
      setLanguage('hi');
      setReportTranslationWarning('');
    } catch (error) {
      setReportTranslationWarning(error.message || 'Translation is unavailable.');
      showToast(`Interface switched to Hindi, but the report could not be translated: ${error.message}`, 'error');
    }
  };

  const startSample = async (type = 'rent_agreement') => {
    try { const sample = await api.sample(type); setDraftText(sample.text); setFile(null); setInputMode('text'); setView('analyze'); showToast('Sample agreement loaded. Review the text before analyzing.'); }
    catch (error) { showToast(`Could not load sample: ${error.message}`, 'error'); }
  };

  const resetDraft = () => { setDraftText(''); setFile(null); setInputMode('file'); setPersist(true); };

  const analyzeAgreement = async ({ file: selectedFile, text, docType, sourceLanguage: selectedSourceLanguage = sourceLanguage }) => {
    setBusy(true);
    try {
      const result = selectedFile
        ? await api.analyzeFile(selectedFile, language, persist, selectedSourceLanguage)
        : await api.analyzeText({ text, language, persist, source_language: selectedSourceLanguage });
      const baseReport = result.canonical_report || { ...result };
      delete baseReport.canonical_report;
      setCanonicalReport(baseReport);
      setActiveReport({ ...result, canonical_report: baseReport });
      setPreviousView('documents'); setView('report'); setFile(null); setDraftText('');
      if (result.persisted) await refreshReports();
      showToast('Analysis complete. Compare translated findings with the original clauses.');
    } catch (error) { showToast(error.message || 'Analysis failed. Check the document and try again.', 'error'); }
    finally { setBusy(false); }
  };

  const toggleSavedReport = (id) => {
    const wasSaved = savedIds.includes(id);
    setSavedIds((items) => wasSaved ? items.filter((item) => item !== id) : [...items, id]);
    showToast(wasSaved ? 'Removed from saved analyses.' : 'Added to saved analyses.');
  };

  const deleteReport = async (id) => {
    if (!window.confirm('Delete this saved analysis from your local history? This action cannot be undone.')) return;
    try { await api.deleteReport(id); setReports((items) => items.filter((r) => r.report_id !== id)); setSavedIds((items) => items.filter((item) => item !== id)); if (activeReport?.report_id === id) { setActiveReport(null); setCanonicalReport(null); setView('documents'); } showToast('Report deleted from history.'); }
    catch (error) { showToast(`Could not delete report: ${error.message}`, 'error'); }
  };

  const printReport = () => {
    if (!activeReport) return;
    showToast('In the print dialog, choose “Save as PDF” to download this report.');
    setTimeout(() => window.print(), 180);
  };

  const navigateBackFromReport = () => { setView(previousView === 'report' ? 'documents' : previousView); };

  const mainContent = () => {
    if (view === 'dashboard') return <Dashboard reports={reports} loading={loadingReports} onNew={() => setView('analyze')} onOpen={openReport} onSample={startSample} onDelete={deleteReport} query={query} />;
    if (view === 'analyze') return <AnalyzePage draftText={draftText} setDraftText={setDraftText} file={file} setFile={setFile} inputMode={inputMode} setInputMode={setInputMode} language={language} setLanguage={setLanguage} sourceLanguage={sourceLanguage} setSourceLanguage={setSourceLanguage} translationStatus={translationStatus} persist={persist} setPersist={setPersist} onAnalyze={analyzeAgreement} onSample={startSample} busy={busy} onClear={resetDraft} />;
    if (view === 'report' && activeReport) return <ReportView report={activeReport} language={language} uiLanguage={uiLanguage} translationStatus={translationStatus} reportTranslationWarning={reportTranslationWarning} onReportLanguageChange={changeReportLanguage} onBack={navigateBackFromReport} onAnalyze={() => { resetDraft(); setView('analyze'); }} onPrint={printReport} isSaved={savedIds.includes(activeReport.report_id)} onToggleSaved={() => toggleSavedReport(activeReport.report_id)} />;
    if (view === 'saved') return <DashboardListPage title="Saved analyses" eyebrow="YOUR SHORTLIST" description="Reports you marked to revisit. Saved reports are remembered in this browser on this device." reports={reports.filter((r) => savedIds.includes(r.report_id))} loading={loadingReports} onOpen={openReport} onDelete={deleteReport} onNew={() => setView('analyze')} query={query} setQuery={setQuery} />;
    if (view === 'documents' || view === 'reports') return <DashboardListPage title={view === 'reports' ? 'Risk reports' : 'My documents'} eyebrow={view === 'reports' ? 'RISK MONITORING' : 'DOCUMENT LIBRARY'} description={view === 'reports' ? 'Browse completed reports and open the findings that need your attention.' : 'Your locally saved agreement analyses, organized in one place.'} reports={reports} loading={loadingReports} onOpen={openReport} onDelete={deleteReport} onNew={() => setView('analyze')} query={query} setQuery={setQuery} />;
    if (view === 'settings' || view === 'help' || view === 'privacy') return <SimpleInfoPage page={view} onNew={() => setView('analyze')} />;
    return <Dashboard reports={reports} loading={loadingReports} onNew={() => setView('analyze')} onOpen={openReport} onSample={startSample} onDelete={deleteReport} query={query} />;
  };

  return <I18nProvider language={uiLanguage}><div className="app-shell">
    <Sidebar view={view} setView={setView} open={mobileNavOpen} onClose={() => setMobileNavOpen(false)} reportCount={reports.length} />
    <div className="main-shell"><Topbar view={view} onMenu={() => setMobileNavOpen(true)} setView={setView} query={query} setQuery={setQuery} uiLanguage={uiLanguage} onUiLanguageChange={changeInterfaceLanguage} reports={reports} onOpenReport={openReport} />
      <main className="main-content">{backendStatus === 'offline' && <div className="backend-warning"><AlertCircle size={16} /><span>{translateUiText('Backend connection not detected. Start the FastAPI server and refresh this page.', uiLanguage)}</span><button onClick={() => api.health().then(() => setBackendStatus('online')).catch(() => setBackendStatus('offline'))}>{translateUiText('Retry', uiLanguage)}</button></div>}{mainContent()}</main>
      <footer className="app-footer"><span>© {new Date().getFullYear()} ClauseLens</span><span><LockKeyhole size={13} />{translateUiText('Local-first agreement review', uiLanguage)}</span><span>{translateUiText('Not legal advice', uiLanguage)}</span></footer>
    </div>
    <Toast toast={toast} onClose={() => setToast(null)} />
  </div></I18nProvider>;
}
