(globalThis["TURBOPACK"] || (globalThis["TURBOPACK"] = [])).push([typeof document === "object" ? document.currentScript : undefined,
"[project]/components/welcome-message.jsx [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "default",
    ()=>WelcomeMessage
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/jsx-dev-runtime.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$demo$2d$session$2e$jsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/components/demo-session.jsx [app-client] (ecmascript)");
;
var _s = __turbopack_context__.k.signature();
'use client';
;
function WelcomeMessage() {
    _s();
    const { user } = (0, __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$demo$2d$session$2e$jsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useDemoSession"])();
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
        children: [
            "Welcome, ",
            user?.email.split('@')[0] || 'team member',
            "."
        ]
    }, void 0, true, {
        fileName: "[project]/components/welcome-message.jsx",
        lineNumber: 7,
        columnNumber: 10
    }, this);
}
_s(WelcomeMessage, "fMfWQwVyOqDf7H0ignQFdQS+iCY=", false, function() {
    return [
        __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$demo$2d$session$2e$jsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useDemoSession"]
    ];
});
_c = WelcomeMessage;
var _c;
__turbopack_context__.k.register(_c, "WelcomeMessage");
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
]);

//# sourceMappingURL=components_welcome-message_jsx_10_mv3w._.js.map