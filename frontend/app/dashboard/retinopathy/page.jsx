import ToolDashboard from '@/components/tool-dashboard';
export const metadata = { title: "Eye Health" };
export default function Page() { return <ToolDashboard {...{"title": "Eye Health", "description": "Organize retinal screening and review your eye care workflow.", "action": "Open retinal screening", "href": "/retino", "steps": ["Prepare a clear retinal fundus image.", "Check the image format before uploading.", "Arrange clinical review of the screening result."]}}/>; }
