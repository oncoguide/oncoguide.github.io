// make-contract-template.mjs -- builds static/donate/templates/sponsorship-contract-ro.pdf
// (DONATIONS.md T6, Appendix B). Fully programmatic and reproducible: re-running this script
// regenerates the committed template byte-for-byte-equivalent (modulo PDF ids/dates).
//
// Source text: .private/finantare/contract-text-ro.txt (gitignored -- vetted clause text,
// transcribed from the precompletat contract MINUS the representative name, D4). The committed
// PDF carries only generic legal boilerplate + public association data; every personal datum is
// a blank AcroForm field. The anonymity audit (scripts/audit-contract-template.mjs) must pass
// on the output: all text fields empty, no /JS, no representative name anywhere.
//
// Field schema (Appendix B, with the T6 refinement): sponsor_denumire, sponsor_cui,
// sponsor_reg_com, sponsor_sediu, sponsor_reprezentant, sponsor_calitate, sponsor_banca,
// sponsor_iban, suma, suma_litere, data_contract, art5_a + art5_b (two checkboxes replacing the
// single "art5_varianta" -- the vetted Art. 5 has [ ] a) and [ ] b); the flow checks exactly
// one), beneficiar_denumire, beneficiar_cif, beneficiar_sediu, beneficiar_iban, beneficiar_reg163
// (filled at generation from data/association.yaml), sponsor_semnatura (pushbutton placeholder
// for pdf-lib setImage), and beneficiar_reprezentant + beneficiar_semnatura (NO default value --
// left blank for the association's offline countersignature, D4).
//
// The text is pure ASCII (verified), so StandardFonts Helvetica is sufficient (no font
// embedding needed). NeedAppearances is set so viewers regenerate filled-field appearances.
// NEVER flatten (S7.1): the beneficiary fields must stay fillable for countersignature.
//
// Usage: node scripts/make-contract-template.mjs

import { PDFDocument, StandardFonts, rgb, PDFName, PDFBool } from 'pdf-lib';
import { readFileSync, writeFileSync } from 'node:fs';

const SRC = '.private/finantare/contract-text-ro.txt';
const OUT = 'static/donate/templates/sponsorship-contract-ro.pdf';

// ---- page geometry (A4) ----
const PAGE_W = 595.28;
const PAGE_H = 841.89;
const MARGIN = 50;
const BOTTOM = 56;
const MAX_X = PAGE_W - MARGIN;

// ---- type scale ----
const BODY_SIZE = 9.5;
const LEADING = 13.5;
const HEADING_SIZE = 10.5;
const TITLE_SIZE = 13;
const FIELD_H = 13; // text-field widget height
const RULE = rgb(0.45, 0.45, 0.45);
const INK = rgb(0, 0, 0);

let text;
try {
  text = readFileSync(SRC, 'utf8');
} catch (e) {
  console.error(
    'make-contract-template: cannot read ' + SRC + '\n' +
    'The contract source text lives in the gitignored .private/ tree (provenance, D4).\n' +
    'The committed template PDF is the build artifact; rebuild requires the .private file.'
  );
  process.exit(1);
}
if (/[^\x00-\x7F]/.test(text)) {
  console.error('make-contract-template: ' + SRC + ' must be pure ASCII (Helvetica, S7).');
  process.exit(1);
}

const doc = await PDFDocument.create();
const font = await doc.embedFont(StandardFonts.Helvetica);
const bold = await doc.embedFont(StandardFonts.HelveticaBold);
const form = doc.getForm();

let page = doc.addPage([PAGE_W, PAGE_H]);
let y = PAGE_H - MARGIN - 6;

// field name -> created pdf-lib field (a field may have several widgets, e.g. data_contract
// appears in the header and in Art. 12 and shows the same value in both places).
const textFields = new Map();
const checkboxes = new Map();
let signatureButton = null;

function newPageIfNeeded(needed) {
  if (y - needed < BOTTOM) {
    page = doc.addPage([PAGE_W, PAGE_H]);
    y = PAGE_H - MARGIN;
  }
}

// Place a named text field widget at (x, baselineY) and draw a fill-in rule under it.
function placeTextField(name, x, width, fontSize) {
  let f = textFields.get(name);
  const isNew = !f;
  if (isNew) {
    f = form.createTextField(name);
    textFields.set(name, f);
  }
  f.addToPage(page, {
    x: x,
    y: y - 3,
    width: width,
    height: FIELD_H,
    borderWidth: 0,
    backgroundColor: undefined,
    borderColor: undefined,
  });
  // setFontSize needs the /DA created by addToPage, so it runs after the first widget exists.
  if (isNew) f.setFontSize(fontSize || 9);
  page.drawLine({
    start: { x: x, y: y - 2.5 },
    end: { x: x + width, y: y - 2.5 },
    thickness: 0.6,
    color: RULE,
  });
}

function placeCheckbox(name, x) {
  let c = checkboxes.get(name);
  if (c) throw new Error('duplicate checkbox ' + name);
  c = form.createCheckBox(name);
  checkboxes.set(name, c);
  c.addToPage(page, {
    x: x,
    y: y - 1.5,
    width: 10,
    height: 10,
    borderWidth: 1,
    borderColor: INK,
    backgroundColor: undefined,
  });
}

// Pushbutton placeholder for the drawn signature image (pdf-lib setImage; Appendix B).
function placeSignatureButton(name, x, width, height) {
  if (signatureButton) throw new Error('duplicate signature button');
  signatureButton = form.createButton(name);
  signatureButton.addToPage('', page, {
    x: x,
    y: y - height + 8,
    width: width,
    height: height,
    borderWidth: 0.6,
    borderColor: RULE,
    backgroundColor: rgb(1, 1, 1), // pdf-lib defaults buttons to gray; keep the sign area white
    textColor: INK,
    font: font,
  });
}

// A chunk is a whitespace-split word; it may carry a field token with leading/trailing
// punctuation attached, e.g. "([[F:suma_litere:300:8]]" or "[[F:sponsor_cui:90]],".
const TOKEN_RE = /^(.*?)\[\[([FCS]):([a-z0-9_]+)(?::(\d+))?(?::(\d+))?\]\](.*)$/;

// Measure one chunk without drawing.
function chunkWidth(chunk, size) {
  const m = chunk.match(TOKEN_RE);
  if (!m) return font.widthOfTextAtSize(chunk, size);
  const w = m[2] === 'C' ? 10 : parseInt(m[4], 10);
  return font.widthOfTextAtSize(m[1] + m[6], size) + w;
}

// Draw one chunk at (x, y); returns the new x.
function drawChunk(chunk, x, size, fnt) {
  const m = chunk.match(TOKEN_RE);
  if (!m) {
    page.drawText(chunk, { x: x, y: y, size: size, font: fnt, color: INK });
    return x + fnt.widthOfTextAtSize(chunk, size);
  }
  const prefix = m[1], kind = m[2], name = m[3], suffix = m[6];
  let x2 = x;
  if (prefix) {
    page.drawText(prefix, { x: x2, y: y, size: size, font: fnt, color: INK });
    x2 += fnt.widthOfTextAtSize(prefix, size);
  }
  if (kind === 'F') {
    const width = parseInt(m[4], 10);
    placeTextField(name, x2, width, m[5] ? parseInt(m[5], 10) : undefined);
    x2 += width;
  } else if (kind === 'C') {
    placeCheckbox(name, x2);
    x2 += 10;
  } else if (kind === 'S') {
    placeSignatureButton(name, x2, parseInt(m[4], 10), parseInt(m[5], 10));
    x2 += parseInt(m[4], 10);
  }
  if (suffix) {
    page.drawText(suffix, { x: x2, y: y, size: size, font: fnt, color: INK });
    x2 += fnt.widthOfTextAtSize(suffix, size);
  }
  return x2;
}

const SPACE_W = font.widthOfTextAtSize(' ', BODY_SIZE);

// Wrapped paragraph with inline tokens.
function par(line) {
  const chunks = line.split(/\s+/).filter(Boolean);
  let x = MARGIN;
  newPageIfNeeded(LEADING);
  for (const chunk of chunks) {
    const w = chunkWidth(chunk, BODY_SIZE);
    if (x > MARGIN && x + w > MAX_X) {
      y -= LEADING;
      newPageIfNeeded(LEADING);
      x = MARGIN;
    }
    x = drawChunk(chunk, x, BODY_SIZE, font) + SPACE_W;
  }
  y -= LEADING;
}

function centerLine(line, size, fnt) {
  const chunks = line.split(/\s+/).filter(Boolean);
  let total = 0;
  for (const c of chunks) total += chunkWidth(c, size) + SPACE_W;
  total -= SPACE_W;
  let x = (PAGE_W - total) / 2;
  newPageIfNeeded(LEADING);
  for (const c of chunks) x = drawChunk(c, x, size, fnt) + SPACE_W;
  y -= LEADING;
}

function heading(line) {
  y -= 6; // breathing room before a section
  newPageIfNeeded(LEADING + 6);
  page.drawText(line, { x: MARGIN, y: y, size: HEADING_SIZE, font: bold, color: INK });
  y -= LEADING;
}

// Two-column block (signature area): rows of "left | right".
function cols(rows) {
  const RIGHT_X = 330;
  const COL_LEAD = 19;
  // keep the block together on one page (signature rows include a 55pt button)
  newPageIfNeeded(rows.length * COL_LEAD + 60);
  for (const row of rows) {
    const [left, right] = row.split(' | ');
    let extra = 0;
    for (const [colText, colX] of [[left, MARGIN], [right, RIGHT_X]]) {
      let x = colX;
      for (const chunk of (colText || '').split(/\s+/).filter(Boolean)) {
        const sig = chunk.match(TOKEN_RE);
        if (sig && sig[2] === 'S') extra = Math.max(extra, parseInt(sig[5], 10) - COL_LEAD + 8);
        x = drawChunk(chunk, x, BODY_SIZE, /^[A-Z ]+$/.test(colText) ? bold : font) + SPACE_W;
      }
    }
    y -= COL_LEAD + extra;
  }
}

// ---- parse the source markup ----
const lines = text.split('\n');
let colRows = null;
for (const raw of lines) {
  const line = raw.replace(/\s+$/, '');
  if (line.startsWith('#') || line === '') continue;
  if (colRows !== null) {
    if (line === '.endcols') { cols(colRows); colRows = null; }
    else colRows.push(line);
    continue;
  }
  if (line === '.cols') { colRows = []; continue; }
  if (line.startsWith('.title ')) { centerLine(line.slice(7), TITLE_SIZE, bold); y -= 4; continue; }
  if (line.startsWith('.center ')) { centerLine(line.slice(8), BODY_SIZE, font); continue; }
  if (line.startsWith('.heading ')) { heading(line.slice(9)); continue; }
  if (line.startsWith('.space ')) { y -= parseInt(line.slice(7), 10); continue; }
  if (line.startsWith('.par ')) { par(line.slice(5)); continue; }
  throw new Error('unknown directive: ' + line.slice(0, 40));
}

// ---- Appendix B completeness check ----
const EXPECTED_TEXT = [
  'sponsor_denumire', 'sponsor_cui', 'sponsor_reg_com', 'sponsor_sediu', 'sponsor_reprezentant',
  'sponsor_calitate', 'sponsor_banca', 'sponsor_iban', 'suma', 'suma_litere', 'data_contract',
  'beneficiar_denumire', 'beneficiar_cif', 'beneficiar_sediu', 'beneficiar_iban',
  'beneficiar_reg163', 'beneficiar_reprezentant', 'beneficiar_semnatura',
];
for (const name of EXPECTED_TEXT) {
  if (!textFields.has(name)) throw new Error('missing text field: ' + name);
}
for (const name of ['art5_a', 'art5_b']) {
  if (!checkboxes.has(name)) throw new Error('missing checkbox: ' + name);
}
if (!signatureButton) throw new Error('missing sponsor_semnatura button');

// ---- metadata (no personal data) + NeedAppearances, save (never flatten, S7.1) ----
doc.setTitle('Contract de sponsorizare -- Asociatia OncoGuide');
doc.setSubject('Model de contract de sponsorizare (Legea nr. 32/1994)');
doc.setProducer('OncoGuide make-contract-template.mjs (pdf-lib)');
doc.setCreator('OncoGuide');
form.acroForm.dict.set(PDFName.of('NeedAppearances'), PDFBool.True);
const bytes = await doc.save();
writeFileSync(OUT, bytes);
console.log(
  'wrote ' + OUT + ': ' + doc.getPageCount() + ' page(s), ' + bytes.length + ' bytes, ' +
  textFields.size + ' text fields, ' + checkboxes.size + ' checkboxes, 1 signature button'
);
