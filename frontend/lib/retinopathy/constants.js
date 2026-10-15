export const RETINOPATHY_SEVERITIES = [
  {
    key: 'no-dr',
    label: 'No DR',
    fullLabel: 'No diabetic retinopathy',
    classNumber: 0,
    color: '#16a34a',
    tint: '#ecfdf3',
    description: 'Model category indicating no diabetic retinopathy; professional assessment is still required.',
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

export const CLASS_KEYS = ['no_dr', 'mild_npdr', 'moderate_npdr', 'severe_npdr', 'proliferative_dr'];
export const MAX_FILE_SIZE = 10 * 1024 * 1024;
export const percent = value => Number.isFinite(value) ? `${(value * 100).toFixed(1)}%` : 'Unavailable';
export function validateRetinalFile(file) {
  if (!file || !['image/jpeg', 'image/png'].includes(file.type) || !/\.(jpe?g|png)$/i.test(file.name)) return 'Please select a JPG or PNG retinal image.';
  if (!file.size) return 'This file is empty.';
  if (file.size > MAX_FILE_SIZE) return 'Please select an image no larger than 10 MB.';
  return '';
}
