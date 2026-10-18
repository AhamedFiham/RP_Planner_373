'use client';
import { useRef, useState } from 'react';
import { ImagePlus, Upload, RefreshCw, ScanLine, LoaderCircle } from 'lucide-react';
import styles from './food-detection.module.css';

export default function MealImageUpload({ file, dimensions, loading, preparing, onSelect, onAnalyze, onReset, children }) {
  const input = useRef(null);
  const [dragging, setDragging] = useState(false);
  const browse = () => input.current?.click();
  return <section className={styles.card} aria-labelledby="upload-heading">
    <div className={styles.cardHeading}><span className={styles.icon}><ImagePlus size={20}/></span><div><h3 id="upload-heading">Upload Meal Image</h3><p>A clear photo makes a difference.</p></div><span className={styles.step}>01</span></div>
    <input ref={input} className={styles.fileInput} type="file" accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp" aria-label="Choose meal image" onChange={e => { const file = e.target.files?.[0]; if (file) onSelect(file); e.target.value = ''; }}/>
    {!file ? <div className={`${styles.dropzone} ${dragging ? styles.dragging : ''}`} onDragOver={e => { e.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={e => { e.preventDefault(); setDragging(false); if (e.dataTransfer.files.length === 1) onSelect(e.dataTransfer.files[0]); else onSelect(null); }}>
      <span className={styles.uploadIcon}><Upload size={28}/></span><h4>{preparing ? 'Opening your image…' : 'Your meal, ready for a closer look'}</h4><p>Drag and drop your meal image here</p><span className={styles.or}>or</span><button className="button" type="button" onClick={browse}>Choose Image</button><small>JPG, JPEG, PNG or WebP · Up to 10 MiB</small>
    </div> : <><div className={styles.preview}>{children}</div><div className={styles.fileDetails}><strong title={file.name}>{file.name}</strong><span>{dimensions && `${dimensions.width} × ${dimensions.height} · `}{(file.size / 1024 / 1024).toFixed(2)} MB</span></div><div className={styles.actions}><button className={`button ${styles.analyze}`} type="button" disabled={loading} onClick={onAnalyze}>{loading ? <LoaderCircle className={styles.spin} size={17}/> : <ScanLine size={17}/>} {loading ? 'Analyzing your meal…' : 'Analyze Meal'}</button><button className="button secondary" type="button" onClick={browse}>Change Image</button><button className={styles.reset} type="button" onClick={onReset} aria-label="Remove selected image"><RefreshCw size={16}/> Reset</button></div></>}
    <div className={styles.cardNote}><span className={styles.dot}/>Your image is used for analysis and is not saved by the detector.</div>
  </section>;
}
