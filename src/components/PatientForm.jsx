import { AlertTriangle, HeartPulse, LifeBuoy, Lock, User } from 'lucide-react';
import Field from './Field.jsx';
import { SECTIONS } from '../lib/fields.js';

const SECTION_ICONS = {
  patient: { Icon: User, className: 'text-blue-500' },
  clinical: { Icon: HeartPulse, className: 'text-red-500' },
  support: { Icon: LifeBuoy, className: 'text-emerald-500' },
};

export default function PatientForm({ form, onFieldChange, onSubmit, isSubmitting, error }) {
  return (
    <>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900">Patient Data Entry</h1>
        <p className="text-slate-600 mt-1">
          Enter patient clinical and socio-demographic data to generate an AI prediction.
        </p>
        <p className="mt-3 text-sm text-slate-500">
          Required fields are marked with <span className="text-red-500 font-medium">*</span> and should be completed before generating the prediction.
        </p>
      </div>

      {error && (
        <div className="mb-6 flex items-start bg-red-50 border border-red-200 text-red-800 rounded-lg p-4">
          <AlertTriangle className="w-5 h-5 mr-3 flex-shrink-0 mt-0.5 text-red-500" />
          <div>
            <p className="font-medium">Prediction failed</p>
            <p className="text-sm text-red-700 mt-0.5">{error}</p>
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <form onSubmit={onSubmit}>
          {SECTIONS.map((section, index) => {
            const { Icon, className } = SECTION_ICONS[section.id];
            return (
              <div
                key={section.id}
                className={`p-6 border-b border-slate-200 ${index % 2 ? 'bg-slate-50/50' : ''}`}
              >
                <h3 className="text-lg font-medium text-slate-900 flex items-center">
                  <Icon className={`w-5 h-5 mr-2 ${className}`} /> {section.title}
                </h3>
                {section.note && <p className="text-sm text-slate-500 mt-1">{section.note}</p>}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-4">
                  {section.fields.map((field) => (
                    <Field key={field.name} field={field} value={form[field.name]} onChange={onFieldChange} />
                  ))}
                </div>
              </div>
            );
          })}

          <div className="p-6 bg-slate-100/50 flex flex-col sm:flex-row items-center justify-between gap-4">
            <p className="text-sm text-slate-500 flex items-center">
              <Lock className="w-4 h-4 mr-1 text-slate-400" />
              Patient data is secured and handled with strict confidentiality.
            </p>
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full sm:w-auto px-8 py-3 bg-blue-600 text-white font-medium rounded-md hover:bg-blue-700 transition-colors disabled:bg-blue-400 flex items-center justify-center shadow-md"
            >
              {isSubmitting ? (
                <>
                  <Spinner /> AI Processing...
                </>
              ) : (
                'Generate AI Prediction'
              )}
            </button>
          </div>
          <div className="px-6 pb-6 text-xs text-slate-500">
            This tool provides decision-support guidance only and should be reviewed alongside clinical judgement.
          </div>
        </form>
      </div>
    </>
  );
}

function Spinner() {
  return (
    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );
}
