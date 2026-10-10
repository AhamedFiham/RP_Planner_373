(globalThis["TURBOPACK"] || (globalThis["TURBOPACK"] = [])).push([typeof document === "object" ? document.currentScript : undefined,
"[project]/frontend/components/retino/retino-workflow.jsx [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "default",
    ()=>RetinoWorkflowProvider,
    "useRetinoWorkflow",
    ()=>useRetinoWorkflow
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/jsx-dev-runtime.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/index.js [app-client] (ecmascript)");
;
var _s = __turbopack_context__.k.signature(), _s1 = __turbopack_context__.k.signature();
'use client';
;
const RetinoWorkflowContext = /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["createContext"])(null);
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
    _s();
    const [workflow, setWorkflow] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(emptyWorkflow);
    const [isRestoring, setIsRestoring] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(true);
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useEffect"])({
        "RetinoWorkflowProvider.useEffect": ()=>{
            let active = true;
            readStoredImage().then({
                "RetinoWorkflowProvider.useEffect": (file)=>{
                    if (!active || !file) return;
                    const restoredFile = file instanceof File ? file : new File([
                        file
                    ], file.name || 'fundus-image', {
                        type: file.type || 'image/jpeg'
                    });
                    setWorkflow({
                        "RetinoWorkflowProvider.useEffect": (current)=>({
                                ...current,
                                uploadedImage: restoredFile,
                                imagePreview: URL.createObjectURL(restoredFile)
                            })
                    }["RetinoWorkflowProvider.useEffect"]);
                }
            }["RetinoWorkflowProvider.useEffect"]).catch({
                "RetinoWorkflowProvider.useEffect": ()=>{}
            }["RetinoWorkflowProvider.useEffect"]).finally({
                "RetinoWorkflowProvider.useEffect": ()=>{
                    if (active) setIsRestoring(false);
                }
            }["RetinoWorkflowProvider.useEffect"]);
            return ({
                "RetinoWorkflowProvider.useEffect": ()=>{
                    active = false;
                }
            })["RetinoWorkflowProvider.useEffect"];
        }
    }["RetinoWorkflowProvider.useEffect"], []);
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useEffect"])({
        "RetinoWorkflowProvider.useEffect": ()=>({
                "RetinoWorkflowProvider.useEffect": ()=>{
                    if (workflow.imagePreview) URL.revokeObjectURL(workflow.imagePreview);
                }
            })["RetinoWorkflowProvider.useEffect"]
    }["RetinoWorkflowProvider.useEffect"], [
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
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(RetinoWorkflowContext.Provider, {
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
_s(RetinoWorkflowProvider, "KW4pMaYckRkILMlV8zteWOpTHpI=");
_c = RetinoWorkflowProvider;
function useRetinoWorkflow() {
    _s1();
    const context = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useContext"])(RetinoWorkflowContext);
    if (!context) throw new Error('useRetinoWorkflow must be used within RetinoWorkflowProvider');
    return context;
}
_s1(useRetinoWorkflow, "b9L3QQ+jgeyIrH0NfHrJ8nn7VMU=");
var _c;
__turbopack_context__.k.register(_c, "RetinoWorkflowProvider");
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
]);

//# sourceMappingURL=frontend_components_retino_retino-workflow_jsx_1eg8l-n._.js.map