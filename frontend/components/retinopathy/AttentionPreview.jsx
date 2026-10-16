import { ScanEye } from 'lucide-react';

// Render only supplied backend assets. Demo mode never fabricates model attention.
export default function AttentionPreview({ imageUrl, label, compact = false }) {
  return imageUrl ? (
    <img className="retino-attention-image" src={imageUrl} alt={label} />
  ) : (
    <span className={`retino-attention-placeholder${compact ? ' compact' : ''}`}>
      <ScanEye size={compact ? 25 : 36} aria-hidden="true" />
      <strong>Image unavailable</strong>
      <span>No authorized image loaded</span>
    </span>
  );
}
