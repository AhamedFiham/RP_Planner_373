import Link from 'next/link';
import { ArrowRight, Utensils, Leaf, History, ImagePlus } from 'lucide-react';
import DashboardShell from '@/components/dashboard/DashboardShell';
import styles from '@/components/diet/food-detection.module.css';

export const metadata = { title: 'Nutrition & Diet' };
export default function Page() {
  return <DashboardShell title="Nutrition & Diet" hideSidebar><div className="dashboard-inner">
    <section className="dashboard-welcome"><div><p className="dashboard-kicker">YOUR NUTRITION WORKSPACE</p><h2>Nutrition &amp; Diet</h2><p>Understand your meal, portion size, and nutrition at a glance.</p></div><Link className="button" href="/diet">Analyze My Meal <ArrowRight size={16}/></Link></section>
    <div className="dashboard-columns">
      <section className={`dashboard-card ${styles.landingCard}`}><span className={styles.icon}><Utensils size={22}/></span><h2>Latest Meal Assessment</h2><div className={styles.dashboardEmpty}><ImagePlus size={30}/><h3>Your next meal is a great place to start</h3><p>Upload a meal photo to explore the foods on your plate and their portions.</p><Link className="card-action" href="/diet">Analyze a meal <ArrowRight size={16}/></Link></div></section>
      <section className={`dashboard-card ${styles.landingCard}`}><span className={styles.icon}><Leaf size={22}/></span><h2>Nutrition Summary</h2><div className={styles.dashboardEmpty}><Leaf size={30}/><h3>A little more insight into your meal</h3><p>Your meal’s nutrition information will appear during your assessment. Start with a clear meal photo.</p><Link className="card-action" href="/diet">Explore your meal <ArrowRight size={16}/></Link></div></section>
    </div>
    <section className={`dashboard-card ${styles.landingCard}`}><div className={styles.historyHeading}><span className={styles.icon}><Leaf size={22}/></span><div><h2>Meal Guidance</h2><p>Personalized context for your current glucose level.</p></div></div><p className="muted">Enter your glucose level with a meal photo to receive portion and food guidance.</p><Link className="card-action" href="/diet">Get meal guidance <ArrowRight size={16}/></Link></section>
    <section className={`dashboard-card ${styles.landingCard}`}><div className={styles.historyHeading}><span className={styles.icon}><History size={22}/></span><div><h2>Meal History</h2><p>No saved meal assessments yet.</p></div></div><p className="muted">Completed analyses are currently available on the meal analysis page. Saved meal history will appear here when available.</p></section>
  </div></DashboardShell>;
}
