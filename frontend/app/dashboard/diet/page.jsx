import ToolDashboard from '@/components/tool-dashboard';
export const metadata = { title: "Nutrition & Diet" };
export default function Page() { return <ToolDashboard {...{"title": "Nutrition & Diet", "description": "Prepare your profile for personalized nutrition planning.", "action": "Open diet workspace", "href": "/diet", "steps": ["Review your dietary preferences.", "Have current health measurements ready.", "Discuss meal changes with your care team."]}}/>; }
