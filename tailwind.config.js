import { fileURLToPath } from 'node:url'
import path from 'node:path'
import animate from 'tailwindcss-animate'

// Resolve content globs relative to this config file, not the CWD, so the
// dev server works whether it's launched from here or from a parent folder.
const root = path.dirname(fileURLToPath(import.meta.url))

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    path.join(root, 'index.html'),
    path.join(root, 'src/**/*.{js,jsx}'),
  ],
  theme: {
    extend: {},
  },
  plugins: [animate],
}
