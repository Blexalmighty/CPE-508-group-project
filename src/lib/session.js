/**
 * Login + session token helpers.
 *
 * A successful /api/login returns a signed token that /api/predict requires.
 * It lives in localStorage so a page refresh keeps the session; logout clears
 * it. A 401 anywhere in the app should call clearSession() and fall back to
 * the login screen.
 */

import { apiRequest } from './api';

const TOKEN_KEY = 'oncopredict_token';
const STAFF_KEY = 'oncopredict_staff';

export async function login(staffId, password) {
  const { token } = await apiRequest('/api/login', {
    method: 'POST',
    body: { staffId, password },
  });
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(STAFF_KEY, staffId);
  return token;
}

export async function logout() {
  const token = getToken();
  clearSession();

  if (!token) {
    return { ok: true, message: 'Logged out successfully.' };
  }

  try {
    return await apiRequest('/api/logout', {
      method: 'POST',
      token,
    });
  } catch {
    return { ok: true, message: 'Logged out successfully.' };
  }
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function getStaff() {
  return localStorage.getItem(STAFF_KEY);
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(STAFF_KEY);
}
