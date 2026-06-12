// bridge-check.mjs -- regression guard for the T4 data bridge (DONATIONS.md S5.1).
// Extracts window.oncoDonate from the BUILT page and asserts it is a real object (not a
// double-encoded string, the bug the T4-T6 review caught: jsonify without safeJS).
// Run AFTER `hugo --gc --minify`:  node scripts/bridge-check.mjs (wired into T7 test steps)
import { readFileSync } from 'node:fs';

const PAGES = [
  'public/ro/donate/persoane-fizice/index.html',
  'public/ro/donate/firme/index.html',
];

let fails = 0;
function check(name, cond) {
  console.log((cond ? 'PASS' : 'FAIL') + ' - ' + name);
  if (!cond) fails += 1;
}

// Balanced-brace extraction: the minifier drops the trailing ';' before </script>, so a lazy
// regex overshoots into the next inline script. Walk from the first '{', tracking depth and
// string state, and return the exact object literal.
function extractObject(html, anchor) {
  const at = html.indexOf(anchor);
  if (at < 0) return null;
  const start = html.indexOf('{', at);
  if (start < 0) return null;
  let depth = 0, inStr = null;
  for (let i = start; i < html.length; i++) {
    const c = html[i];
    if (inStr) {
      if (c === '\\') i += 1;
      else if (c === inStr) inStr = null;
    } else if (c === '"' || c === "'") inStr = c;
    else if (c === '{') depth += 1;
    else if (c === '}') { depth -= 1; if (depth === 0) return html.slice(start, i + 1); }
  }
  return null;
}

for (const page of PAGES) {
  const html = readFileSync(page, 'utf8');
  const lit = extractObject(html, 'window.oncoDonate');
  check(page + ': bridge assignment found', !!lit);
  if (!lit) continue;
  let bridge = null;
  // The minifier may rewrite the JSON into a JS object literal (unquoted keys), so evaluate it
  // as JS, not JSON.parse. Double-encoded garbage (the original bug) yields strings, caught below.
  try { bridge = new Function('return ' + lit)(); } catch (e) { /* syntax error -> garbage */ }
  check(page + ': bridge evaluates to an object', bridge !== null && typeof bridge === 'object');
  if (!bridge) continue;
  check(page + ': assoc is an object (not a string)', typeof bridge.assoc === 'object' && bridge.assoc !== null);
  check(page + ': fiscal is an object (not a string)', typeof bridge.fiscal === 'object' && bridge.fiscal !== null);
  check(page + ': assoc.cif === "54791907"', bridge.assoc && bridge.assoc.cif === '54791907');
  check(page + ': fiscal flag is boolean', typeof ((bridge.fiscal || {}).flags || {}).registru163_active === 'boolean');
  check(page + ': base is a clean path (no quote chars)', typeof bridge.base === 'string' && /^[/a-z0-9._-]+\/$/i.test(bridge.base));
  check(page + ': locale is a bare language code', typeof bridge.locale === 'string' && /^[a-z]{2}$/.test(bridge.locale));
  check(page + ': web3formsKey is a bare key (no embedded quotes)', typeof bridge.web3formsKey === 'string' && !bridge.web3formsKey.includes('"'));
  // No PII: the bridge must contain only the public data files + key/locale/base.
  const allowed = ['assoc', 'fiscal', 'web3formsKey', 'locale', 'base'];
  check(page + ': no unexpected bridge keys', Object.keys(bridge).every((k) => allowed.includes(k)));
}

console.log(fails === 0 ? '\nALL BRIDGE CHECKS PASSED' : '\n' + fails + ' BRIDGE CHECK(S) FAILED');
process.exit(fails === 0 ? 0 : 1);
