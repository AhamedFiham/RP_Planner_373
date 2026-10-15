export const RETINOPATHY_SEVERITIES = [
  {
    key: 'no-dr',
    label: 'No DR',
    fullLabel: 'No diabetic retinopathy',
    classNumber: 0,
    color: '#16a34a',
    tint: '#ecfdf3',
    description: 'No visible signs of diabetic retinopathy in the demonstration result.',
  },
  {
    key: 'mild',
    label: 'Mild NPDR',
    fullLabel: 'Mild non-proliferative diabetic retinopathy',
    classNumber: 1,
    color: '#d97706',
    tint: '#fffbeb',
    description: 'Early retinal changes that need confirmation by an eye-care professional.',
  },
  {
    key: 'moderate',
    label: 'Moderate NPDR',
    fullLabel: 'Moderate non-proliferative diabetic retinopathy',
    classNumber: 2,
    color: '#ea580c',
    tint: '#fff7ed',
    description: 'Retinal changes that may require closer professional evaluation.',
  },
  {
    key: 'severe',
    label: 'Severe NPDR',
    fullLabel: 'Severe non-proliferative diabetic retinopathy',
    classNumber: 3,
    color: '#dc2626',
    tint: '#fef2f2',
    description: 'More extensive retinal changes that warrant prompt specialist review.',
  },
  {
    key: 'proliferative',
    label: 'Proliferative DR',
    fullLabel: 'Proliferative diabetic retinopathy',
    classNumber: 4,
    color: '#991b1b',
    tint: '#fef2f2',
    description: 'Advanced retinal changes requiring specialist assessment.',
  },
];

export const DEMO_RESULT = {
  predictedClass: 2,
  confidence: 87,
  probabilities: [2, 6, 87, 4, 1],
  quality: 'good',
  calibration: 'Demo — Not available',
};

export const DEMO_HISTORY = [
  { id: 1, date: '02 Oct 2026', severity: 'Moderate NPDR', confidence: 87, quality: 'Good' },
  { id: 2, date: '15 Sep 2026', severity: 'Mild NPDR', confidence: 82, quality: 'Good' },
  { id: 3, date: '20 Aug 2026', severity: 'Mild NPDR', confidence: 79, quality: 'Usable' },
];

export const QUALITY_STATES = {
  good: {
    label: 'Good',
    message: 'The demonstration image has passed the simulated quality assessment.',
    metrics: { Clarity: 'Good', Illumination: 'Adequate', 'Retinal visibility': 'Good' },
  },
  usable: {
    label: 'Usable',
    message: 'The demonstration image is usable, though a clearer fundus photograph may improve reliability.',
    metrics: { Clarity: 'Adequate', Illumination: 'Adequate', 'Retinal visibility': 'Adequate' },
  },
  reject: {
    label: 'Reject',
    message: 'This image is not suitable for reliable retinal analysis. Please upload a clearer fundus photograph.',
    metrics: { Clarity: 'Insufficient', Illumination: 'Poor', 'Retinal visibility': 'Limited' },
  },
};

export const DEMO_THRESHOLD = 75;


export const DEMO_CONFIG = {
  maxFileSize: 10 * 1024 * 1024,
  acceptedTypes: ['image/jpeg', 'image/png'],
  qualityDelay: 800,
  analysisDelay: 700,
};

// This adapter is the only source of simulated prediction values.
// Future responses can supply calibrated: true and gradcam[classIndex].{heatmapUrl, overlayUrl}.
export function createDemoResult(quality, confidenceScenario) {
  if (quality === 'reject') return null;
  return {
    ...DEMO_RESULT,
    quality,
    isDemo: true,
    calibrated: false,
    confidence: confidenceScenario === 'uncertain' ? 62 : 87,
    probabilities: confidenceScenario === 'uncertain' ? [8, 17, 62, 10, 3] : [...DEMO_RESULT.probabilities],
    gradcam: [],
  };
}

export function validateRetinalFile(file, maxFileSize = DEMO_CONFIG.maxFileSize) {
  if (!file || !DEMO_CONFIG.acceptedTypes.includes(file.type) || !/\.(jpe?g|png)$/i.test(file.name)) {
    return 'Please choose a JPG, JPEG, or PNG image.';
  }
  if (!file.size) return 'This file is empty. Please select a retinal image.';
  if (file.size > maxFileSize) return `This image is larger than ${maxFileSize / 1024 / 1024} MB. Choose a smaller fundus image.`;
  return '';
}

export const EDUCATIONAL_GUIDANCE = [
  'This example category does not indicate visible diabetic retinopathy. It does not rule out other eye conditions or replace a professional eye examination.',
  'This example category describes early retinal changes. An eye-care specialist can confirm the findings and advise on appropriate follow-up.',
  'This category indicates retinal changes that may require closer professional evaluation. An eye-care specialist can confirm the findings and recommend appropriate follow-up.',
  'This example category describes more extensive retinal changes. Seek an eye-care specialist’s assessment to understand the findings and appropriate care.',
  'This example category describes advanced retinal changes. An eye-care specialist’s assessment is needed to confirm the findings and discuss appropriate care.',
];
