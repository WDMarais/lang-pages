// ESLint (flat config). Scope is deliberately one rule to start: braces always.
//
//   curly: ['error', 'all'] — every if/else/for/while/do body must be a block,
//   even a one-liner. Keeps `if (x) foo()` from silently swallowing a second
//   statement when someone adds one later; makes the control flow explicit to
//   parse. (Autofixable: `npm run lint:fix`.)
//
// These are browser <script> files sharing globals across files (not ES
// modules), so sourceType is 'script'. no-undef is intentionally NOT enabled —
// cross-file globals (html, diagram, HanziWriter, LAYOUT) would false-positive,
// and catching typos is not what this config is for yet.
export default [
  {
    ignores: ['shared/vendor/**', 'node_modules/**', '.venv/**'],
  },
  {
    files: ['**/*.js'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'script',
    },
    rules: {
      curly: ['error', 'all'],
      // curly's autofix emits `{return x;}`; the codebase pads braces
      // (`{ on: [], kun: [] }`), so keep the one-line blocks it adds consistent.
      'block-spacing': ['error', 'always'],
    },
  },
];
