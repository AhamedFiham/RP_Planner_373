import ToolDashboard from '@/components/tool-dashboard';
export const metadata = { title: 'Nutrition & Diet' };
export default function Page() {
  return <ToolDashboard title="Nutrition & Diet" description="Explore food detection as the first step in your dietary research workspace." action="Open Food Detector" href="/diet" steps={['Choose a clear photo of your Sri Lankan meal.', 'Analyze the image to identify supported foods.', 'Review detected food names and confidence scores.']}/>;
}
