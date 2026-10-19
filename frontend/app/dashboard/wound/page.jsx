import ToolDashboard from '@/components/tool-dashboard';
export const metadata = { title: "Wound Healing" };
export default function Page() { return <ToolDashboard {...{"title": "Wound Healing", "description": "Follow your wound monitoring workflow and visit images.", "action": "Open wound workspace", "href": "/dfu", "steps": ["Prepare a clear wound image.", "Record the visit date consistently.", "Consult your care team about changes."]}}/>; }
