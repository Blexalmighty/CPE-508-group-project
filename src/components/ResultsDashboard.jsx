import { AlertTriangle, ArrowLeft, CheckCircle, Info, TrendingUp } from 'lucide-react';

// Badge and bar colours are keyed off the risk band so the visuals track the
// score instead of being pinned to one outcome.
const RISK_STYLES = {
  'Low Risk': { badge: 'bg-green-100 text-green-700 border-green-200', bar: 'bg-green-500' },
  'Moderate Risk': { badge: 'bg-amber-100 text-amber-700 border-amber-200', bar: 'bg-amber-500' },
  'High Risk': { badge: 'bg-red-100 text-red-700 border-red-200', bar: 'bg-red-500' },
};

// Bars in the class breakdown, worst outcome to best.
const CLASS_BARS = {
  Progressive: 'bg-red-500',
  Stable: 'bg-amber-500',
  Partial: 'bg-sky-500',
  Complete: 'bg-green-500',
};

const METRICS = [
  {
    key: 'completion',
    title: 'Treatment Completion Likelihood',
    scoreKey: 'completionLikelihood',
    riskKey: 'completionRisk',
    Icon: CheckCircle,
    watermark: 'text-green-600',
    blurbs: {
      'Low Risk': 'High probability of completing the prescribed treatment cycle.',
      'Moderate Risk': 'Some risk of interrupting the prescribed treatment cycle.',
      'High Risk': 'Substantial risk of defaulting before the treatment cycle ends.',
    },
  },
  {
    key: 'response',
    title: 'Treatment Response Likelihood',
    scoreKey: 'responseLikelihood',
    riskKey: 'responseRisk',
    Icon: TrendingUp,
    watermark: 'text-amber-500',
    blurbs: {
      'Low Risk': 'Strong chance of a positive clinical response to the therapy.',
      'Moderate Risk': 'Moderate chance of a positive clinical response to the therapy.',
      'High Risk': 'Limited chance of a positive clinical response to the therapy.',
    },
  },
];

export default function ResultsDashboard({ result, patient, onReset }) {
  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">AI Prediction Results</h1>
          <p className="text-slate-600 mt-1">
            {patient.cancerType} &middot; Stage {patient.tumorStage} &middot; {patient.age}y {patient.sex} &middot;{' '}
            {patient.location || 'Location not given'}
          </p>
        </div>
        <button
          onClick={onReset}
          className="hidden sm:flex items-center text-sm font-medium text-blue-600 hover:text-blue-800 bg-blue-50 px-4 py-2 rounded-full transition-colors"
        >
          <ArrowLeft className="w-4 h-4 mr-2" /> New Patient
        </button>
      </div>

      <div className="mb-6 flex items-start bg-amber-50 border border-amber-200 text-amber-900 rounded-lg p-4">
        <AlertTriangle className="w-5 h-5 mr-3 flex-shrink-0 mt-0.5 text-amber-500" />
        <div className="text-sm">
          <p>
            <span className="font-medium">Response</span> is predicted by{' '}
            <code className="font-mono text-xs bg-amber-100 px-1 py-0.5 rounded">{result.modelName}</code> as
            P(Partial) + P(Complete).
            {result.completionIsEstimate && (
              <>
                {' '}
                <span className="font-medium">Completion</span> is a rule-based estimate — no completion model has been
                trained yet.
              </>
            )}
          </p>
          <p className="mt-1 text-amber-800">
            An auxiliary risk-flagging aid only. It does not replace clinical judgement.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {METRICS.map((metric) => (
          <MetricCard
            key={metric.key}
            metric={metric}
            score={result[metric.scoreKey]}
            band={result[metric.riskKey]}
            isEstimate={metric.key === 'completion' && result.completionIsEstimate}
          />
        ))}
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 mb-6">
        <h3 className="text-lg font-semibold text-slate-900 mb-1">Predicted Tumour Response</h3>
        <p className="text-sm text-slate-500 mb-4">
          Most likely outcome: <span className="font-semibold text-slate-800">{result.responseClass}</span>
        </p>
        <ul className="space-y-3">
          {result.classBreakdown.map(({ name, percent }) => (
            <li key={name} className="flex items-center">
              <span className="w-28 text-sm text-slate-600 flex-shrink-0">{name}</span>
              <div className="flex-1 bg-slate-100 rounded-full h-2.5 mx-3">
                <div
                  className={`h-2.5 rounded-full transition-all duration-700 ${CLASS_BARS[name] ?? 'bg-slate-400'}`}
                  style={{ width: `${percent}%` }}
                />
              </div>
              <span className="w-12 text-sm font-medium text-slate-700 text-right flex-shrink-0">{percent}%</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <h3 className="text-lg font-semibold text-slate-900 mb-4 flex items-center">
          <Info className="w-5 h-5 mr-2 text-blue-500" /> Decision Support Recommendations
        </h3>
        <div className="bg-slate-50 rounded-lg p-5 border border-slate-100">
          <ul className="space-y-3">
            {result.recommendations.map((rec) => (
              <li key={rec} className="flex items-start">
                <div className="w-2 h-2 rounded-full bg-blue-500 flex-shrink-0 mt-2" />
                <p className="ml-3 text-slate-700">{rec}</p>
              </li>
            ))}
          </ul>
        </div>

        <button
          onClick={onReset}
          className="mt-6 w-full sm:hidden flex justify-center items-center text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 py-3 rounded-md transition-colors"
        >
          <ArrowLeft className="w-4 h-4 mr-2" /> Start New Patient Entry
        </button>
      </div>
    </div>
  );
}

function MetricCard({ metric, score, band, isEstimate }) {
  const { Icon, title, watermark, blurbs } = metric;
  const style = RISK_STYLES[band] ?? RISK_STYLES['Moderate Risk'];

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 relative overflow-hidden">
      <div className="absolute top-0 right-0 p-4 opacity-10">
        <Icon className={`w-24 h-24 ${watermark}`} />
      </div>
      <div className="flex items-center mb-2 relative">
        <h3 className="text-lg font-semibold text-slate-800">{title}</h3>
        {isEstimate && (
          <span className="ml-2 px-2 py-0.5 text-xs font-medium rounded bg-slate-100 text-slate-600 border border-slate-200">
            estimate
          </span>
        )}
      </div>
      <div className="flex items-end mb-4 relative">
        <span className="text-5xl font-extrabold text-slate-900">{score}%</span>
        <span className={`ml-3 mb-1 px-3 py-1 text-sm font-semibold rounded-full border ${style.badge}`}>{band}</span>
      </div>
      <div className="w-full bg-slate-100 rounded-full h-3 mb-2 relative">
        <div
          className={`h-3 rounded-full transition-all duration-700 ${style.bar}`}
          style={{ width: `${score}%` }}
        />
      </div>
      <p className="text-sm text-slate-500 relative">{blurbs[band]}</p>
    </div>
  );
}
