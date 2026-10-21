'use client';

import { Activity, Calendar, ChevronRight, Clock, FileText, Search, ShieldCheck } from 'lucide-react';

export default function RiskHistory({ history = [], onSelectAssessment, loading }) {
  if (loading) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-sm text-slate-500 shadow-sm">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mb-3"></div>
        <p className="m-0 font-medium">Loading clinical assessment history...</p>
      </div>
    );
  }

  if (!history || history.length === 0) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center shadow-sm">
        <div className="w-12 h-12 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-3 text-slate-400">
          <FileText className="w-6 h-6" />
        </div>
        <h3 className="text-base font-bold text-slate-800 mb-1">No Assessment Records Yet</h3>
        <p className="text-xs text-slate-500 max-w-sm mx-auto m-0">
          When you complete a diabetes risk assessment, it is securely archived here with full SHAP contributions and clinical interpretation.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-md overflow-hidden">
      <div className="p-6 border-b border-slate-100 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h3 className="text-lg font-bold text-slate-900 m-0">Clinical Assessment History</h3>
          <p className="text-xs text-slate-500 m-0 mt-0.5">
            Archived evaluations with persistent SHAP attribution and WHO clinical classifications.
          </p>
        </div>
        <span className="text-xs font-bold px-3 py-1 bg-slate-100 text-slate-700 rounded-full border border-slate-200">
          {history.length} Record{history.length === 1 ? '' : 's'} Stored
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="bg-slate-50/80 border-b border-slate-200 text-slate-600 font-bold uppercase tracking-wider text-[11px]">
              <th className="py-3 px-4">Timestamp</th>
              <th className="py-3 px-4">Prediction</th>
              <th className="py-3 px-4">Probability</th>
              <th className="py-3 px-4">WHO Status</th>
              <th className="py-3 px-4">Biomarkers Tested</th>
              <th className="py-3 px-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {history.map((item, idx) => {
              const isPos = item.prediction?.label === 'positive';
              const prob = Math.round((item.prediction?.probability || 0) * 100);
              const dateStr = item.timestamp
                ? new Date(item.timestamp).toLocaleString(undefined, {
                    month: 'short',
                    day: 'numeric',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                  })
                : 'Recent';

              return (
                <tr key={item.id || idx} className="hover:bg-slate-50/60 transition group">
                  <td className="py-3.5 px-4 text-slate-600 font-mono text-[11px] whitespace-nowrap">
                    <div className="flex items-center gap-1.5">
                      <Clock className="w-3.5 h-3.5 text-slate-400" />
                      {dateStr}
                    </div>
                  </td>
                  <td className="py-3.5 px-4 whitespace-nowrap">
                    <span
                      className={`px-2.5 py-1 rounded-full text-[10px] font-extrabold uppercase tracking-wide inline-flex items-center gap-1 ${
                        isPos
                          ? 'bg-rose-50 text-rose-700 border border-rose-200'
                          : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                      }`}
                    >
                      <span className={`w-1.5 h-1.5 rounded-full ${isPos ? 'bg-rose-500' : 'bg-emerald-500'}`}></span>
                      {item.prediction?.label}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 font-mono font-bold text-slate-900 text-sm whitespace-nowrap">
                    {prob}%
                  </td>
                  <td className="py-3.5 px-4 whitespace-nowrap">
                    <span className="capitalize px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-medium text-[11px]">
                      {item.clinical_assessment?.status?.replace('_', ' ') || 'Normal'}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 text-slate-600 font-mono text-[11px] whitespace-nowrap">
                    <span className="font-semibold text-slate-800">
                      HbA1c: {item.input?.HbA1c_level || item.input?.hba1c_level || 'N/A'}%
                    </span>
                    <span className="text-slate-400 mx-1.5">•</span>
                    <span>BG: {item.input?.blood_glucose_level || 'N/A'} mg/dL</span>
                    <span className="text-slate-400 mx-1.5">•</span>
                    <span>BMI: {item.input?.bmi || 'N/A'}</span>
                  </td>
                  <td className="py-3.5 px-4 text-right whitespace-nowrap">
                    {onSelectAssessment && (
                      <button
                        type="button"
                        onClick={() => onSelectAssessment(item)}
                        className="px-3 py-1.5 bg-blue-50 hover:bg-blue-100 text-blue-700 font-bold text-xs rounded-lg transition inline-flex items-center gap-1 cursor-pointer"
                      >
                        <span>Review</span>
                        <ChevronRight className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
