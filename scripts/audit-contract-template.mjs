// Anonymity audit for the donation flows (DONATIONS.md S12, T1).
//
// Guards the hard rule that the association representative's name never enters git:
//   (a) no contract-template text field may carry a non-empty default value
//   (b) the template may not contain embedded JavaScript (/JS, /JavaScript)
//   (c) the representative name may not appear in template field names/values/metadata
//   (d) the representative name may not appear anywhere in the tracked source tree
//
// The name is NEVER a literal here: it comes from the REPRESENTATIVE_NAME env var,
// fed from the gitignored .private/finantare/.audit-name by the pre-commit hook.
// Exit code 0 = pass, 1 = fail.

import { execSync } from 'node:child_process';
import { existsSync, readFileSync, statSync } from 'node:fs';

const TEMPLATE_GLOB_DIR = 'static/donate/templates';
const TEMPLATE_PREFIX = 'sponsorship-contract-';

const name = (process.env.REPRESENTATIVE_NAME || '').trim();
if (!name) {
  console.error(
    'audit-contract-template: REPRESENTATIVE_NAME is not set.\n' +
    'Set it from the gitignored name file, e.g.:\n' +
    '  REPRESENTATIVE_NAME="$(cat .private/finantare/.audit-name)" npm run audit'
  );
  process.exit(1);
}

// Case/diacritic-insensitive matcher. The secret is the legal name in RO order
// (surname first). A lone GIVEN name is not flagged: the author's first name is an
// established public section label in this repo (/dorin/ hub, robots.txt) and flagging
// it alone would drown the audit in false positives. We flag instead:
//   (1) the full normalized name,
//   (2) the surname token (first token -- the distinctive secret part),
//   (3) any TWO name tokens co-occurring in the same text (catches reorderings).
const normalize = (s) =>
  s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
const fullName = normalize(name).replace(/[^a-z]+/g, ' ').trim();
const nameTokens = fullName.split(' ').filter((t) => t.length >= 3);
const surname = nameTokens[0];
const containsName = (text) => {
  const t = normalize(text);
  if (t.includes(fullName)) return true;
  if (surname && t.includes(surname)) return true;
  const present = nameTokens.filter((tok) => t.includes(tok));
  return present.length >= 2;
};

let failed = false;
const fail = (msg) => { console.error('AUDIT FAIL: ' + msg); failed = true; };

// ---- (a)-(c): template checks (skip with warning until T6 authors the template) ----
const lsFiles = execSync('git ls-files', { encoding: 'utf8' }).split('\n').filter(Boolean);
const templates = lsFiles.filter(
  (f) => f.startsWith(TEMPLATE_GLOB_DIR + '/') && f.includes(TEMPLATE_PREFIX) && f.endsWith('.pdf')
);

if (templates.length === 0) {
  console.warn('audit: no contract template committed yet -- skipping checks (a)-(c) (expected before T6).');
} else {
  const { PDFDocument, PDFName } = await import('pdf-lib');
  for (const tpl of templates) {
    const bytes = readFileSync(tpl);
    const doc = await PDFDocument.load(bytes, { ignoreEncryption: true });

    // (a) + (c) on fields, via the pdf-lib API (byte-grep false-fails: object streams, S7.3.5)
    const form = doc.getForm();
    for (const field of form.getFields()) {
      const fname = field.getName();
      if (containsName(fname)) fail(`${tpl}: field name "${fname}" matches the representative name`);
      if (field.constructor.name === 'PDFTextField') {
        const v = field.getText() || '';
        if (v.trim() !== '') fail(`${tpl}: text field "${fname}" has a non-empty default value ("${v}")`);
        if (containsName(v)) fail(`${tpl}: field "${fname}" default value matches the representative name`);
      }
    }

    // (b) embedded JavaScript -- check the raw bytes for the action keys
    const raw = bytes.toString('latin1');
    if (raw.includes('/JavaScript') || /\/JS[\s(<]/.test(raw)) {
      fail(`${tpl}: contains embedded JavaScript (/JS or /JavaScript)`);
    }

    // (c) metadata (XMP + info dict)
    const meta = [doc.getTitle(), doc.getAuthor(), doc.getSubject(), doc.getKeywords(),
                  doc.getProducer(), doc.getCreator()].filter(Boolean).join(' ');
    if (containsName(meta)) fail(`${tpl}: document metadata matches the representative name`);
    const xmpMatch = raw.match(/<x:xmpmeta[\s\S]*?<\/x:xmpmeta>/);
    if (xmpMatch && containsName(xmpMatch[0])) fail(`${tpl}: XMP metadata matches the representative name`);
  }
}

// ---- (d): full tracked source tree grep (text files; binary PDFs covered by (a)-(c)) ----
for (const f of lsFiles) {
  if (f.startsWith(TEMPLATE_GLOB_DIR + '/') && f.endsWith('.pdf')) continue;
  if (!existsSync(f)) continue;
  if (!statSync(f).isFile()) continue; // submodule gitlinks (themes/PaperMod) list as dirs
  const buf = readFileSync(f);
  if (buf.includes(0)) continue; // skip binary
  if (containsName(buf.toString('utf8'))) {
    fail(`tracked file ${f} contains the representative name`);
  }
}

if (failed) process.exit(1);
console.log(`audit: OK (${templates.length} template(s) checked, ${lsFiles.length} tracked files scanned)`);
