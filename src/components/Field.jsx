const CONTROL = 'w-full border border-slate-300 rounded-md py-2 px-3 focus:ring-blue-500 focus:border-blue-500';

/** Renders one form control from its config entry in lib/fields.js. */
export default function Field({ field, value, onChange }) {
  // `default` only seeds INITIAL_FORM and `hint` renders below the control;
  // neither is a DOM attribute.
  const { name, label, options, type, fullWidth, hint, default: _seed, ...attrs } = field;

  return (
    <div className={fullWidth ? 'md:col-span-2' : undefined}>
      <label htmlFor={name} className="block text-sm font-medium text-slate-700 mb-1">
        {label}
      </label>

      {options ? (
        <select id={name} name={name} value={value} onChange={onChange} className={CONTROL}>
          {options.map((option) => (
            <option key={option}>{option}</option>
          ))}
        </select>
      ) : type === 'textarea' ? (
        <textarea id={name} name={name} value={value} onChange={onChange} className={CONTROL} {...attrs} />
      ) : (
        <input id={name} name={name} type={type ?? 'text'} value={value} onChange={onChange} className={CONTROL} {...attrs} />
      )}

      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </div>
  );
}
