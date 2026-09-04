// Single source of truth for the patient form. Drives the rendered inputs, the
// initial state, and the payload shape sent to the prediction service — add a
// field here and it flows through all three.
//
// The option strings and numeric ranges are not cosmetic: they are the exact
// categories and documented bounds the models were trained on (report 3.1.2).
// Changing a label is safe; changing a value means changing backend/features.py
// to match, or the model silently receives a feature it never saw in training.

export const SECTIONS = [
  {
    id: 'patient',
    title: 'Patient',
    fields: [
      { name: 'age', label: 'Age', type: 'number', required: true, min: 30, max: 85, default: 55 },
      { name: 'sex', label: 'Sex', options: ['Male', 'Female'] },
      { name: 'bmi', label: 'BMI', type: 'number', required: true, min: 18.5, max: 35, step: 0.1, default: 26.5 },
      { name: 'smokingStatus', label: 'Smoking Status', options: ['Never', 'Former', 'Current'] },
      { name: 'neutropenia', label: 'Neutropenia', options: ['No', 'Yes'] },
      {
        name: 'nauseaSeverity',
        label: 'Nausea Severity (1–5)',
        type: 'number',
        required: true,
        min: 1,
        max: 5,
        default: 3,
      },
      {
        // Random Forest was trained without this column -- it was excluded as
        // leakage, being a downstream outcome rather than a predictor. Still
        // collected and still sent, because the XGBoost bundle does use it and
        // either model can be serving. Under Random Forest it changes nothing,
        // hence the hint.
        name: 'survivalMonths',
        label: 'Overall Survival (months)',
        type: 'number',
        required: true,
        min: 6,
        max: 120,
        default: 24,
        hint: 'Recorded for context. Excluded from the Random Forest model as leakage.',
      },
    ],
  },
  {
    id: 'clinical',
    title: 'Tumour & Treatment',
    fields: [
      { name: 'cancerType', label: 'Cancer Type', options: ['Breast', 'Colon', 'Leukemia', 'Lung', 'Lymphoma'] },
      { name: 'tumorStage', label: 'Tumour Stage', options: ['I', 'II', 'III', 'IV'] },
      { name: 'metastasisStatus', label: 'Metastasis', options: ['No', 'Yes'] },
      {
        name: 'geneticMutation',
        label: 'Genetic Mutation',
        options: ['None', 'BRCA1', 'EGFR', 'KRAS', 'TP53'],
      },
      {
        name: 'chemoRegimen',
        label: 'Chemotherapy Regimen',
        options: ['None', 'ABVD', 'CHOP', 'FOLFOX', 'Gemcitabine'],
      },
      {
        name: 'tumorSizeCm',
        label: 'Tumour Size (cm)',
        type: 'number',
        required: true,
        min: 1,
        max: 10,
        step: 0.1,
        default: 3.5,
      },
      {
        name: 'dosage',
        label: 'Dosage (mg/m²)',
        type: 'number',
        required: true,
        min: 50,
        max: 600,
        default: 300,
      },
      {
        name: 'cyclesCompleted',
        label: 'Cycles Completed',
        type: 'number',
        required: true,
        min: 1,
        max: 8,
        default: 4,
      },
    ],
  },
  {
    id: 'support',
    title: 'Support Context',
    // Report 3.3 restricts these to routing supportive interventions. They are
    // deliberately not model inputs — they shape the recommendations only.
    note: 'Used to route supportive interventions. Not sent to the model.',
    fields: [
      { name: 'location', label: 'State/Location', placeholder: 'e.g., Ibadan' },
      { name: 'religion', label: 'Religion', options: ['Christianity', 'Islam', 'Traditional', 'Other/None'] },
      {
        name: 'distanceKm',
        label: 'Distance from Hospital (km)',
        type: 'number',
        required: true,
        min: 0,
        default: 20,
      },
      { name: 'financialStatus', label: 'Financial Status', options: ['Low Income', 'Middle Income', 'High Income'] },
      {
        name: 'previousTreatment',
        label: 'Previous Treatment Records',
        options: ['None (First time patient)', 'Completed previous treatment', 'Defaulted/Stopped previous treatment'],
      },
      {
        name: 'medicalHistory',
        label: 'Previous Medical History / Comorbidities',
        type: 'textarea',
        rows: 3,
        fullWidth: true,
        placeholder: 'E.g., Hypertension, Diabetes...',
      },
    ],
  },
];

const ALL_FIELDS = SECTIONS.flatMap((section) => section.fields);

const NUMERIC_FIELDS = ALL_FIELDS.filter((field) => field.type === 'number').map((field) => field.name);

// Numbers use their stated default, selects start on their first option, and
// free-text fields start empty.
export const INITIAL_FORM = Object.fromEntries(
  ALL_FIELDS.map((field) => [field.name, field.default ?? field.options?.[0] ?? '']),
);

/** Coerce the form's string values into the types the API expects. */
export function toPayload(form) {
  const payload = { ...form };
  for (const name of NUMERIC_FIELDS) {
    payload[name] = Number(payload[name]);
  }
  return payload;
}
