module.exports = [
"[project]/frontend/components/retino/retino-workflow.jsx [app-ssr] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "default",
    ()=>RetinoWorkflowProvider,
    "useRetinoWorkflow",
    ()=>useRetinoWorkflow
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react-jsx-dev-runtime.js [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react.js [app-ssr] (ecmascript)");
'use client';
;
;
const RetinoWorkflowContext = /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["createContext"])(null);
const DATABASE_NAME = 'retino-frontend-workflow';
const STORE_NAME = 'images';
const IMAGE_KEY = 'uploaded-fundus-image';
function openImageDatabase() {
    return new Promise((resolve, reject)=>{
        const request = indexedDB.open(DATABASE_NAME, 1);
        request.onupgradeneeded = ()=>request.result.createObjectStore(STORE_NAME);
        request.onsuccess = ()=>resolve(request.result);
        request.onerror = ()=>reject(request.error);
    });
}
async function storeImage(file) {
    const database = await openImageDatabase();
    await new Promise((resolve, reject)=>{
        const transaction = database.transaction(STORE_NAME, 'readwrite');
        transaction.objectStore(STORE_NAME).put(file, IMAGE_KEY);
        transaction.oncomplete = resolve;
        transaction.onerror = ()=>reject(transaction.error);
        transaction.onabort = ()=>reject(transaction.error);
    });
    database.close();
}
async function readStoredImage() {
    const database = await openImageDatabase();
    const file = await new Promise((resolve, reject)=>{
        const transaction = database.transaction(STORE_NAME, 'readonly');
        const request = transaction.objectStore(STORE_NAME).get(IMAGE_KEY);
        request.onsuccess = ()=>resolve(request.result ?? null);
        request.onerror = ()=>reject(request.error);
    });
    database.close();
    return file;
}
async function removeStoredImage() {
    const database = await openImageDatabase();
    await new Promise((resolve, reject)=>{
        const transaction = database.transaction(STORE_NAME, 'readwrite');
        transaction.objectStore(STORE_NAME).delete(IMAGE_KEY);
        transaction.oncomplete = resolve;
        transaction.onerror = ()=>reject(transaction.error);
        transaction.onabort = ()=>reject(transaction.error);
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
    guidance: null
};
function RetinoWorkflowProvider({ children }) {
    const [workflow, setWorkflow] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])(emptyWorkflow);
    const [isRestoring, setIsRestoring] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])(true);
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useEffect"])(()=>{
        let active = true;
        readStoredImage().then((file)=>{
            if (!active || !file) return;
            const restoredFile = file instanceof File ? file : new File([
                file
            ], file.name || 'fundus-image', {
                type: file.type || 'image/jpeg'
            });
            setWorkflow((current)=>({
                    ...current,
                    uploadedImage: restoredFile,
                    imagePreview: URL.createObjectURL(restoredFile)
                }));
        }).catch(()=>{}).finally(()=>{
            if (active) setIsRestoring(false);
        });
        return ()=>{
            active = false;
        };
    }, []);
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useEffect"])(()=>()=>{
            if (workflow.imagePreview) URL.revokeObjectURL(workflow.imagePreview);
        }, [
        workflow.imagePreview
    ]);
    async function setUploadedImage(file) {
        await storeImage(file);
        setWorkflow((current)=>({
                ...current,
                uploadedImage: file,
                imagePreview: URL.createObjectURL(file)
            }));
    }
    async function clearUploadedImage() {
        await removeStoredImage();
        setWorkflow(emptyWorkflow);
    }
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(RetinoWorkflowContext.Provider, {
        value: {
            workflow,
            setUploadedImage,
            clearUploadedImage,
            isRestoring
        },
        children: children
    }, void 0, false, {
        fileName: "[project]/frontend/components/retino/retino-workflow.jsx",
        lineNumber: 112,
        columnNumber: 5
    }, this);
}
function useRetinoWorkflow() {
    const context = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useContext"])(RetinoWorkflowContext);
    if (!context) throw new Error('useRetinoWorkflow must be used within RetinoWorkflowProvider');
    return context;
}
}),
];

//# sourceMappingURL=frontend_components_retino_retino-workflow_jsx_0zsvjbu._.js.map