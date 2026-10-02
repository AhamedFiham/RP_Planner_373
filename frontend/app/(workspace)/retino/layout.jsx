import RetinoWorkflowProvider from '@/components/retino/retino-workflow';
import './retino.css';

export default function RetinoLayout({ children }) {
  return <RetinoWorkflowProvider>{children}</RetinoWorkflowProvider>;
}