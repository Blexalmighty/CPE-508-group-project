import { AlertTriangle, ShieldCheck, Stethoscope, User } from 'lucide-react';

const INPUT = 'focus:ring-blue-500 focus:border-blue-500 block w-full pl-10 sm:text-sm border-slate-300 rounded-md py-3 border';

export default function LoginScreen({ onLogin }) {
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="mx-auto w-16 h-16 bg-blue-600 rounded-full flex items-center justify-center shadow-lg">
          <Stethoscope className="text-white w-8 h-8" />
        </div>
        <h2 className="mt-6 text-center text-3xl font-extrabold text-slate-900">OncoPredict CDSS</h2>
        <p className="mt-2 text-center text-sm text-slate-600">
          Clinical Decision Support System for Cancer Care
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow-xl sm:rounded-xl sm:px-10 border border-slate-100">
          <form
            className="space-y-6"
            onSubmit={(e) => {
              e.preventDefault();
              onLogin();
            }}
          >
            <LoginField id="staffId" label="Staff ID / Email" type="text" placeholder="Enter your staff ID" icon={User} />
            <LoginField id="password" label="Password" type="password" placeholder="••••••••" icon={ShieldCheck} />

            <button
              type="submit"
              className="w-full flex justify-center py-3 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
            >
              Secure Login
            </button>

            <p className="text-xs text-center text-slate-400 flex items-center justify-center">
              <AlertTriangle className="w-3 h-3 mr-1" />
              Prototype: credentials are not verified.
            </p>
          </form>
        </div>
      </div>
    </div>
  );
}

function LoginField({ id, label, type, placeholder, icon: Icon }) {
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-slate-700">
        {label}
      </label>
      <div className="mt-1 relative rounded-md shadow-sm">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <Icon className="h-5 w-5 text-slate-400" />
        </div>
        <input id={id} type={type} required placeholder={placeholder} className={INPUT} />
      </div>
    </div>
  );
}
