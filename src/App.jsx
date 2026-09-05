import { useEffect, useState } from 'react';
import { Activity, FileText, LogOut, Stethoscope } from 'lucide-react';
import LoginScreen from './components/LoginScreen.jsx';
import PatientForm from './components/PatientForm.jsx';
import ResultsDashboard from './components/ResultsDashboard.jsx';
import { INITIAL_FORM, toPayload } from './lib/fields.js';
import { predictOutcome } from './lib/predict.js';
import { clearSession, getStaff, getToken } from './lib/session.js';

export default function App() {
  const [user, setUser] = useState(() => (getToken() ? getStaff() : null));
  const [form, setForm] = useState(INITIAL_FORM);
  const [result, setResult] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  // A 401 from /api/predict (expired session) clears the token and dispatches
  // this event — drop back to the login screen instead of a stale dashboard.
  useEffect(() => {
    const handleLogout = () => {
      setUser(null);
      setResult(null);
      setError(null);
    };
    window.addEventListener('oncopredict:logout', handleLogout);
    return () => window.removeEventListener('oncopredict:logout', handleLogout);
  }, []);

  if (!user) {
    return <LoginScreen onLogin={() => setUser(getStaff())} />;
  }

  const updateField = ({ target }) => {
    setForm((prev) => ({ ...prev, [target.name]: target.value }));
  };

  const startNewEntry = () => {
    setResult(null);
    setForm(INITIAL_FORM);
    setError(null);
  };

  const signOut = () => {
    clearSession();
    setUser(null);
    setResult(null);
    setError(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      setResult(await predictOutcome(toPayload(form)));
    } catch (err) {
      setError(err.message || 'Could not reach the prediction service.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex">
      <aside className="w-64 bg-slate-900 text-white flex-col hidden md:flex">
        <div className="h-16 flex items-center px-6 border-b border-slate-800">
          <Stethoscope className="w-6 h-6 text-blue-400 mr-2" />
          <span className="font-bold text-lg tracking-wide">OncoPredict</span>
        </div>

        <nav className="flex-1 overflow-y-auto py-4 px-2 space-y-1">
          <button
            onClick={startNewEntry}
            className={`w-full group flex items-center px-2 py-2 text-sm font-medium rounded-md transition-colors ${
              result ? 'text-slate-300 hover:bg-slate-700 hover:text-white' : 'bg-blue-600 text-white'
            }`}
          >
            <FileText
              className={`mr-3 flex-shrink-0 h-5 w-5 ${
                result ? 'text-slate-400 group-hover:text-slate-300' : 'text-blue-200'
              }`}
            />
            New Patient Entry
          </button>
          <a
            href="#"
            className="text-slate-300 hover:bg-slate-700 hover:text-white group flex items-center px-2 py-2 text-sm font-medium rounded-md transition-colors"
          >
            <Activity className="mr-3 flex-shrink-0 h-5 w-5 text-slate-400 group-hover:text-slate-300" />
            Patient Database
          </a>
        </nav>

        <div className="p-4 border-t border-slate-800">
          <p className="text-xs text-slate-500 mb-2 px-1 truncate">Signed in: {user}</p>
          <button
            onClick={signOut}
            className="flex items-center text-slate-400 hover:text-white transition-colors text-sm w-full"
          >
            <LogOut className="w-4 h-4 mr-2" /> Secure Logout
          </button>
        </div>
      </aside>

      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="md:hidden bg-slate-900 h-16 flex items-center justify-between px-4">
          <div className="flex items-center text-white">
            <Stethoscope className="w-6 h-6 text-blue-400 mr-2" />
            <span className="font-bold">OncoPredict</span>
          </div>
          <button onClick={signOut} className="text-slate-400 hover:text-white">
            <LogOut className="w-5 h-5" />
          </button>
        </header>

        <main className="flex-1 overflow-y-auto p-4 md:p-8">
          <div className="max-w-5xl mx-auto">
            {result ? (
              <ResultsDashboard result={result} patient={form} onReset={startNewEntry} />
            ) : (
              <PatientForm
                form={form}
                onFieldChange={updateField}
                onSubmit={handleSubmit}
                isSubmitting={isSubmitting}
                error={error}
              />
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
