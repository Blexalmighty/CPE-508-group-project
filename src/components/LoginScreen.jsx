import { useState } from 'react';
import { AlertTriangle, ShieldCheck, Stethoscope, User } from 'lucide-react';
import { login, userLogin, signup } from '../lib/session';

const INPUT = 'focus:ring-blue-500 focus:border-blue-500 block w-full pl-10 sm:text-sm border-slate-300 rounded-md py-3 border';

export default function LoginScreen({ onLogin }) {
  const [staffId, setStaffId] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [mode, setMode] = useState('admin'); // 'admin' or 'user'
  const [isSignup, setIsSignup] = useState(false);
  const [error, setError] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      if (mode === 'admin') {
        await login(staffId, password);
        onLogin(staffId);
      } else {
        if (isSignup) {
          await signup(staffId, password, name);
          onLogin(staffId);
        } else {
          await userLogin(staffId, password);
          onLogin(staffId);
        }
      }
    } catch (err) {
      setError(err.message || 'Could not reach the login service.');
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="mx-auto w-16 h-16 bg-blue-600 rounded-full flex items-center justify-center shadow-lg">
          <Stethoscope className="text-white w-8 h-8" />
        </div>
        <h2 className="mt-6 text-center text-3xl font-extrabold text-slate-900">onco_predict</h2>
        <p className="mt-2 text-center text-sm text-slate-600">
          Clinical Decision Support System for Cancer Care
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow-xl sm:rounded-xl sm:px-10 border border-slate-100">
          {error && (
            <p
              role="alert"
              className="mb-4 rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700"
            >
              {error}
            </p>
          )}
          <form className="space-y-6" onSubmit={handleSubmit}>
            <div className="flex items-center justify-center gap-4">
              <button type="button" className={`text-sm ${mode==='admin'?'font-semibold':''}`} onClick={() => {setMode('admin'); setIsSignup(false);}}>
                Admin
              </button>
              <button type="button" className={`text-sm ${mode==='user'?'font-semibold':''}`} onClick={() => {setMode('user');}}>
                User
              </button>
            </div>
            <div className="mt-4" />
            <LoginField
              id="staffId"
              label={mode === 'admin' ? 'Admin Email' : 'Email'}
              type="text"
              placeholder={mode === 'admin' ? 'blessedbaidoo79@gmail.com' : 'you@example.com'}
              icon={User}
              value={staffId}
              onChange={(value) => setStaffId(value)}
            />
            {mode === 'user' && isSignup && (
              <LoginField
                id="name"
                label="Full name"
                type="text"
                placeholder="Your name"
                icon={Stethoscope}
                value={name}
                onChange={(value) => setName(value)}
              />
            )}
            {mode === 'admin' ? (
              <p className="-mt-4 text-xs text-slate-500">Use the administrator email for access. Password is case-sensitive.</p>
            ) : (
              <p className="-mt-4 text-xs text-slate-500">Create an account or sign in with your email.</p>
            )}
            <LoginField
              id="password"
              label="Password"
              type="password"
              placeholder="••••••••"
              icon={ShieldCheck}
              value={password}
              onChange={(value) => setPassword(value)}
            />

            {mode === 'user' && (
              <div className="flex items-center justify-between text-xs">
                <label className="flex items-center gap-2">
                  <input type="checkbox" checked={isSignup} onChange={() => setIsSignup(!isSignup)} />
                  <span>Sign up</span>
                </label>
                <button type="button" className="text-blue-600" onClick={() => { setMode(mode==='admin'?'user':'admin'); setIsSignup(false); }}>
                  Switch mode
                </button>
              </div>
            )}

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full flex justify-center py-3 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors disabled:opacity-60"
            >
              {isSubmitting ? 'Signing in…' : 'Secure Login'}
            </button>

            <p className="text-xs text-center text-slate-400 flex items-center justify-center">
              <AlertTriangle className="w-3 h-3 mr-1" />
              Protected admin area — credentials are checked by the server.
            </p>
          </form>
        </div>
      </div>
    </div>
  );
}

function LoginField({ id, label, type, placeholder, icon: Icon, value, onChange }) {
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-slate-700">
        {label}
      </label>
      <div className="mt-1 relative rounded-md shadow-sm">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <Icon className="h-5 w-5 text-slate-400" />
        </div>
        <input
          id={id}
          type={type}
          required
          placeholder={placeholder}
          className={INPUT}
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
      </div>
    </div>
  );
}
