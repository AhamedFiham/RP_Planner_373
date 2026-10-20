import DfuWorkspace from '@/components/dfu-workspace';

export const metadata = {
  title: { absolute: 'DFU Research | DiabeticCARE' },
  description: 'Record dated diabetic foot ulcer images and review the planned healing outlook interface.',
};

export default function DfuPage() {
  return <DfuWorkspace />;
}
