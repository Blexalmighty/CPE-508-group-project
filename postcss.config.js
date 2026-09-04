import { fileURLToPath } from 'node:url'
import path from 'node:path'

// Pin the Tailwind config path so it resolves relative to this file rather
// than the CWD, which lets the dev server run from a parent directory too.
const root = path.dirname(fileURLToPath(import.meta.url))

export default {
  plugins: {
    tailwindcss: { config: path.join(root, 'tailwind.config.js') },
    autoprefixer: {},
  },
}
