'use client';

import Link from 'next/link';
import {
  Activity, Apple, ArrowRight, CalendarDays, Eye, HeartPulse,
  ShieldCheck, Utensils, Image as ImageIcon,
} from 'lucide-react';
import DashboardShell from '@/components/dashboard/DashboardShell';

const tools = [
  { title: 'Diabetes Risk', result: 'Moderate Risk', detail: '68% risk probability', note: 'Based on your latest health assessment.', action: 'View Assessment', href: '/dashboard/diabetes', icon: HeartPulse, tone: 'warning', progress: 68 },
  { title: 'Retinopathy', result: 'Moderate NPDR', detail: '87% confidence', note: 'Latest retinal fundus image assessment.', action: 'View Analysis', href: '/dashboard/retinopathy', icon: Eye, tone: 'warning' },
  { title: 'Wound Healing', result: 'Healing', detail: '72% healing progress', note: 'Latest diabetic foot wound assessment.', action: 'View Progress', href: '/dashboard/wound', icon: ShieldCheck, tone: 'success', progress: 72 },
  { title: 'Diet Planning', result: 'Moderate Glycemic Load', detail: "Today's GL target: Low–Moderate", note: 'Personalized recommendations based on your profile.', action: 'View Diet Plan', href: '/dashboard/diet', icon: Utensils, tone: 'info' },
];

const quickActions = [
  ['Check Diabetes Risk', 'Run a health risk assessment.', Activity, '/diabetes'],
  ['Analyze Retinal Image', 'Upload a fundus image for analysis.', ImageIcon, '/retinopathy'],
  ['Analyze Wound', 'Track your wound healing progress.', ShieldCheck, '/dfu'],
  ['Plan My Meal', 'Get a personalized meal plan.', Apple, '/diet'],
];

const assessments = [
  ['Retinopathy Analysis', 'Moderate NPDR', '02 Oct 2026', Eye, 'warning'],
  ['Diabetes Prediction', 'Moderate Risk', '30 Sep 2026', HeartPulse, 'warning'],
  ['Diet Analysis', 'Moderate Glycemic Load', '28 Sep 2026', Utensils, 'info'],
  ['Wound Assessment', 'Healing Progress · 72%', '25 Sep 2026', ShieldCheck, 'success'],
];

function Badge({ children, tone = 'info' }) { return <span className={`dash-badge ${tone}`}>{children}</span>; }
function SectionTitle({ children, action }) { return <div className="dash-section-title"><h2>{children}</h2>{action}</div>; }

export default function DashboardPage() {
  return (
    <DashboardShell title="Dashboard">
        <div className="dashboard-inner">
          <p className="dashboard-demo-note">Demo dashboard: assessment values below are examples, not results calculated from your data.</p>
          <section className="dashboard-welcome"><div><p className="dashboard-kicker">PATIENT DASHBOARD</p><h2>Good Morning, Demo patient <span aria-hidden="true">👋</span></h2><p>Here is an overview of your diabetes health and recent AI assessments.</p></div><span className="updated-label">Last updated: <strong>Today</strong></span></section>
          <section className="health-overview"><div className="overview-heading"><div><p className="dashboard-kicker">HEALTH SUMMARY</p><h2>Your Health Overview</h2></div><Badge tone="warning">Needs Attention</Badge></div><div className="overview-main"><div className="overall-status"><div className="status-ring"><HeartPulse size={25} /></div><div><span>Overall Status</span><strong>Needs Attention</strong><p>Complete regular assessments to keep your health insights up to date.</p></div></div><div className="overview-indicators">{[['Diabetes Risk','Moderate','warning'],['Eye Health','Moderate','warning'],['Wound Status','Healing','success'],['Diet Status','On track','info']].map(([label,value,tone]) => <div key={label}><span>{label}</span><strong>{value}</strong><Badge tone={tone}>●</Badge></div>)}</div></div></section>
          <SectionTitle>AI Health Tools</SectionTitle><div className="ai-tool-grid">{tools.map(({ title, result, detail, note, action, href, icon: Icon, tone, progress }) => <article className="ai-tool-card" key={title}><div className="tool-card-head"><div className={`tool-icon ${tone}`}><Icon size={21} /></div><Badge tone={tone}>{tone === 'success' ? 'Good' : tone === 'warning' ? 'Review' : 'Updated'}</Badge></div><h3>{title}</h3><strong className="tool-result">{result}</strong><span className="tool-detail">{detail}</span>{progress && <div className="progress-track"><span style={{ width: `${progress}%` }} /></div>}<p>{note}</p><Link href={href} className="card-action">{action}<ArrowRight size={16} /></Link></article>)}</div>
          <SectionTitle>Quick Actions</SectionTitle><div className="quick-actions">{quickActions.map(([name, description, Icon, href]) => <Link className="quick-action" href={href} key={name}><span className="quick-icon"><Icon size={19} /></span><span><strong>{name}</strong><small>{description}</small></span><ArrowRight size={17} /></Link>)}</div>
          <div className="dashboard-columns" id="history"><section className="dashboard-card assessments"><SectionTitle action={<Link href="#history" className="view-link">View All History <ArrowRight size={15} /></Link>}>Recent AI Assessments</SectionTitle><div className="assessment-list">{assessments.map(([name, status, date, Icon, tone]) => <div className="assessment-row" key={name}><span className={`assessment-icon ${tone}`}><Icon size={17} /></span><span className="assessment-copy"><strong>{name}</strong><small>{status}</small></span><span className="assessment-date">{date}</span><Link href="#history" className="row-link">View Report</Link></div>)}</div></section><section className="dashboard-card progress-card"><SectionTitle action={<select aria-label="Time period"><option>Last 6 Months</option><option>Last Year</option></select>}>Health Progress</SectionTitle><p className="chart-label">Diabetes Risk Trend</p><div className="chart"><div className="chart-grid"><span /><span /><span /><span /></div><svg viewBox="0 0 420 145" preserveAspectRatio="none" role="img" aria-label="Diabetes risk trend from 72 to 65 percent"><polyline points="5,30 105,48 205,68 305,83 415,112" fill="none" stroke="#0e7490" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" /><circle cx="5" cy="30" r="5" /><circle cx="105" cy="48" r="5" /><circle cx="205" cy="68" r="5" /><circle cx="305" cy="83" r="5" /><circle cx="415" cy="112" r="5" /></svg><div className="chart-axis"><span>Jan · 72%</span><span>Apr · 65%</span></div></div></section></div>
          <div className="dashboard-columns bottom-columns"><section className="dashboard-card" id="recommendations"><SectionTitle>Personalized Recommendations</SectionTitle><div className="recommendations"><div><span className="recommendation-icon"><Activity size={17} /></span><p><strong>Monitor Blood Glucose</strong><small>Keep measurements updated for more accurate risk assessments.</small></p></div><div><span className="recommendation-icon"><Eye size={17} /></span><p><strong>Schedule Eye Screening</strong><small>Continued monitoring may be useful based on your latest assessment.</small></p></div><div><span className="recommendation-icon"><Apple size={17} /></span><p><strong>Improve Meal Balance</strong><small>Reduce high-glycemic portions and increase vegetables.</small></p></div></div><p className="disclaimer">AI-generated guidance supports, but does not replace, professional medical advice.</p></section><section className="dashboard-card upcoming"><SectionTitle>Upcoming</SectionTitle><div className="reminder"><CalendarDays size={18} /><span><strong>Retinal Screening</strong><small>12 Oct 2026</small></span></div><div className="reminder"><CalendarDays size={18} /><span><strong>Weekly Diet Review</strong><small>05 Oct 2026</small></span></div></section></div>
        </div>
    </DashboardShell>
  );
}
