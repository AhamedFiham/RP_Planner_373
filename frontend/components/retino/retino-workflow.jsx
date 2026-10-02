'use client';

import { createContext, useContext, useEffect, useState } from 'react';

const RetinoWorkflowContext = createContext(null);
const DATABASE_NAME = 'retino-frontend-workflow';
const STORE_NAME = 'images';
const IMAGE_KEY = 'uploaded-fundus-image';

function openImageDatabase() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DATABASE_NAME, 1);
    request.onupgradeneeded = () => request.result.createObjectStore(STORE_NAME);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function storeImage(file) {
  const database = await openImageDatabase();
  await new Promise((resolve, reject) => {
    const transaction = database.transaction(STORE_NAME, 'readwrite');
    transaction.objectStore(STORE_NAME).put(file, IMAGE_KEY);
    transaction.oncomplete = resolve;
    transaction.onerror = () => reject(transaction.error);
    transaction.onabort = () => reject(transaction.error);
  });
  database.close();
}

async function readStoredImage() {
  const database = await openImageDatabase();
  const file = await new Promise((resolve, reject) => {
    const transaction = database.transaction(STORE_NAME, 'readonly');
    const request = transaction.objectStore(STORE_NAME).get(IMAGE_KEY);
    request.onsuccess = () => resolve(request.result ?? null);
    request.onerror = () => reject(request.error);
  });
  database.close();
  return file;
}

async function removeStoredImage() {
  const database = await openImageDatabase();
  await new Promise((resolve, reject) => {
    const transaction = database.transaction(STORE_NAME, 'readwrite');
    transaction.objectStore(STORE_NAME).delete(IMAGE_KEY);
    transaction.oncomplete = resolve;
    transaction.onerror = () => reject(transaction.error);
    transaction.onabort = () => reject(transaction.error);
  });
  database.close();
}

const emptyWorkflow = {
  uploadedImage: null,
  imagePreview: null,
  qualityStatus: null,
  processedImage: null,
  predictedClass: null,
  confidence: null,
  probabilities: null,
  gradcamImages: null,
  guidance: null,
};

export default function RetinoWorkflowProvider({ children }) {
  const [workflow, setWorkflow] = useState(emptyWorkflow);
  const [isRestoring, setIsRestoring] = useState(true);

  useEffect(() => {
    let active = true;
    readStoredImage()
      .then(file => {
        if (!active || !file) return;
        const restoredFile = file instanceof File
          ? file
          : new File([file], file.name || 'fundus-image', { type: file.type || 'image/jpeg' });
        setWorkflow(current => ({
          ...current,
          uploadedImage: restoredFile,
          imagePreview: URL.createObjectURL(restoredFile),
        }));
      })
      .catch(() => {})
      .finally(() => {
        if (active) setIsRestoring(false);
      });

    return () => { active = false; };
  }, []);

  useEffect(() => () => {
    if (workflow.imagePreview) URL.revokeObjectURL(workflow.imagePreview);
  }, [workflow.imagePreview]);

  async function setUploadedImage(file) {
    await storeImage(file);
    setWorkflow(current => ({
      ...current,
      uploadedImage: file,
      imagePreview: URL.createObjectURL(file),
    }));
  }

  async function clearUploadedImage() {
    await removeStoredImage();
    setWorkflow(emptyWorkflow);
  }

  return (
    <RetinoWorkflowContext.Provider value={{ workflow, setUploadedImage, clearUploadedImage, isRestoring }}>
      {children}
    </RetinoWorkflowContext.Provider>
  );
}

export function useRetinoWorkflow() {
  const context = useContext(RetinoWorkflowContext);
  if (!context) throw new Error('useRetinoWorkflow must be used within RetinoWorkflowProvider');
  return context;
}