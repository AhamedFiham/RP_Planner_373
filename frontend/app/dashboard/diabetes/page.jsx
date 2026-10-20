import ToolDashboard from '@/components/tool-dashboard';
export const metadata = { title: "Diabetes Risk" };
export default function Page() { return <ToolDashboard {...{"title": "Diabetes Risk", "description": "Review your risk assessment and prepare your health information.", "action": "Start risk assessment", "href": "/diabetes", "steps": ["Have your recent glucose reading ready.", "Review your age, BMI, and family history.", "Discuss risk results with your healthcare provider."]}}/>; }
