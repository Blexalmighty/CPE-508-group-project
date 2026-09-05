/**
 * Prediction service — the only place the UI talks to the model.
 *
 * The backend returns what the trained model can actually say: a probability per
 * Tumor_Response class. Risk bands and recommendation text are derived here so
 * those rules live in one language instead of being mirrored in Python.
 *
 * There is no offline mock. A fabricated score that looks like a model output is
 * worse than an error banner, so a failed call surfaces as a failed call.
 */

import { apiRequest, ApiError } from './api';
import { getToken, clearSession } from './session';

// Clinical order, worst to best — the order Tumor_Response was encoded in.
const CLASS_ORDER = ['Progressive', 'Stable', 'Partial', 'Complete'];

export async function predictOutcome(patient) {
  const prediction = await fetchPrediction(patient);

  const response = toPercent(prediction.responseProbability);
  // completionProbability is null until a completion model exists, so that card
  // falls back to a rule-based estimate and says so.
  const modelledCompletion = prediction.completionProbability != null;
  const completion = modelledCompletion
    ? toPercent(prediction.completionProbability)
    : estimateCompletion(patient);

  return {
    responseLikelihood: response,
    responseRisk: riskBand(response),
    responseClass: prediction.predictedClass,
    classBreakdown: orderClasses(prediction.classProbabilities),

    completionLikelihood: completion,
    completionRisk: riskBand(completion),
    completionIsEstimate: !modelledCompletion,

    recommendations: buildRecommendations(patient, completion, response),
    modelName: prediction.modelName,
  };
}

async function fetchPrediction(patient) {
  try {
    return await apiRequest('/api/predict', {
      method: 'POST',
      body: patient,
      token: getToken(),
    });
  } catch (err) {
    // An expired or otherwise rejected token shows the login screen again;
    // don't leave the user staring at a stale 401 on the dashboard.
    if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
      clearSession();
      window.dispatchEvent(new Event('oncopredict:logout'));
    }
    throw err;
  }
}

/** Known classes first, in clinical order, then anything unexpected. */
function orderClasses(probabilities) {
  const entries = Object.entries(probabilities ?? {});
  const known = CLASS_ORDER.filter((name) => name in (probabilities ?? {})).map((name) => [
    name,
    probabilities[name],
  ]);
  const rest = entries.filter(([name]) => !CLASS_ORDER.includes(name));
  return [...known, ...rest].map(([name, value]) => ({ name, percent: Math.round(value * 100) }));
}

const toPercent = (probability) => Math.max(1, Math.min(99, Math.round(probability * 100)));

export function riskBand(score) {
  if (score >= 75) return 'Low Risk';
  if (score >= 50) return 'Moderate Risk';
  return 'High Risk';
}

/**
 * RULE-BASED ESTIMATE — NOT A TRAINED MODEL.
 *
 * No treatment-completion model has been trained; the five candidate models all
 * predict Tumor_Response. These weights are transparent, invented, and carry no
 * clinical validity. Delete this once a completion model is serving.
 */
function estimateCompletion(patient) {
  const distance = Number(patient.distanceKm) || 0;
  let score = 70;

  if (patient.financialStatus === 'Low Income') score -= 15;
  if (patient.financialStatus === 'High Income') score += 8;
  if (distance > 100) score -= 15;
  else if (distance > 50) score -= 8;
  if (patient.previousTreatment === 'Defaulted/Stopped previous treatment') score -= 20;
  if (patient.previousTreatment === 'Completed previous treatment') score += 12;
  if (patient.tumorStage === 'IV') score -= 10;
  if (Number(patient.age) > 70) score -= 8;
  if (Number(patient.nauseaSeverity) >= 4) score -= 8;

  return Math.max(1, Math.min(99, score));
}

function buildRecommendations(patient, completion, response) {
  const age = Number(patient.age) || 0;
  const distance = Number(patient.distanceKm) || 0;
  const recs = [];

  if (completion >= 75) {
    recs.push('Patient has a high likelihood of completing treatment; standard follow-up schedule is appropriate.');
  } else if (completion >= 50) {
    recs.push('Moderate risk of treatment interruption — consider proactive adherence monitoring.');
  } else {
    recs.push('High risk of treatment default. Prioritise this patient for adherence support before the first cycle.');
  }

  if (patient.financialStatus === 'Low Income') {
    recs.push("Recommend assigning a financial counsellor due to 'Low Income' status to ensure adherence.");
  }
  if (distance > 50) {
    recs.push(`Patient travels ${distance} km to the facility — explore transport support or a treatment site closer to home.`);
  }
  if (patient.previousTreatment === 'Defaulted/Stopped previous treatment') {
    recs.push('Prior treatment was discontinued. Review the reasons for default before starting this regimen.');
  }
  if (response < 50) {
    recs.push(`Predicted response is low for Stage ${patient.tumorStage} disease — consider a multidisciplinary review of the ${patient.chemoRegimen} regimen.`);
  }
  if (patient.metastasisStatus === 'Yes') {
    recs.push('Metastatic disease recorded — confirm the treatment intent (curative vs palliative) is documented.');
  }
  if (patient.neutropenia === 'Yes') {
    recs.push('Neutropenia recorded — monitor blood counts before each cycle and consider growth-factor support.');
  }
  if (Number(patient.nauseaSeverity) >= 4) {
    recs.push('Severe nausea reported; review antiemetic cover, which is a common reason for stopping treatment early.');
  }
  if (patient.medicalHistory.trim()) {
    recs.push('Documented comorbidities may affect tolerance; coordinate with the managing physician.');
  }
  if (age > 70) {
    recs.push('Patient is over 70 — assess performance status and consider dose adjustment.');
  }

  return recs;
}
