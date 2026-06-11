// scripts/fill-test.mjs -- DONATIONS.md T3 (7.3.2, 7.3.5, 7.3.6).
//
// Verifies that the original ANAF AcroForms (Form 230, Form 177) can be filled with pdf-lib
// without touching their layout, and produces the field inventory used to build field-maps.js.
//
// For each form it: enumerates fields; sets a SHORT unique marker on every text field
// (respecting maxLength -- pdf-lib throws if exceeded); checks every checkbox; asserts every
// PDFButton is a non-data pushbutton (no on-state); sets NeedAppearances via the documented
// private path; saves to /tmp/filled-<form>.pdf; reload-asserts the flag; and prints the
// inventory (index -> marker, type, maxLength, name). Open the /tmp PDFs in a viewer to read
// which visible box each marker landed in.
//
// Run: node scripts/fill-test.mjs    (exit 0 = pass)
import { PDFDocument, PDFName, PDFBool } from 'pdf-lib';
import { readFileSync, writeFileSync } from 'node:fs';

const FORMS = [
  { id: '230', path: 'static/donate/templates/form-230-original.pdf' },
  { id: '177', path: 'static/donate/templates/form-177-original.pdf' },
];

function markerFor(idx, maxLen) {
  const base = 'X' + String(idx).padStart(2, '0'); // 3 chars, e.g. X07
  if (maxLen === undefined || maxLen === 0 || maxLen >= base.length) return base;
  return base.slice(0, maxLen); // clamp (e.g. maxLength 1 -> "X")
}

let failures = 0;

for (const form of FORMS) {
  console.log(`\n===== Form ${form.id} (${form.path}) =====`);
  const doc = await PDFDocument.load(readFileSync(form.path), { ignoreEncryption: true });
  const acro = doc.getForm();
  const fields = acro.getFields();

  const counts = {};
  for (const f of fields) counts[f.constructor.name] = (counts[f.constructor.name] || 0) + 1;
  console.log('  field type counts:', JSON.stringify(counts));

  const inventory = [];
  let idx = 0;
  for (const f of fields) {
    const t = f.constructor.name;
    const name = f.getName();
    if (t === 'PDFTextField') {
      idx += 1;
      const maxLen = f.getMaxLength();
      const marker = markerFor(idx, maxLen);
      try {
        f.setText(marker);
      } catch (e) {
        console.log(`  FILL-ERR on ${name}: ${e.message}`);
        failures += 1;
      }
      inventory.push({ idx, marker, type: 'Text', maxLen: maxLen === undefined ? '-' : maxLen, name });
    } else if (t === 'PDFCheckBox') {
      try {
        f.check();
      } catch (e) {
        console.log(`  CHECK-ERR on ${name}: ${e.message}`);
        failures += 1;
      }
      inventory.push({ idx: '', marker: '[x]', type: 'CheckBox', maxLen: '-', name });
    } else if (t === 'PDFButton') {
      // 7.3.6: must be a non-data pushbutton -- no on-state. A real on-state would mean we
      // could (and might accidentally) set it. Inspect the widget /AP /N keys for an on-state.
      let onState = null;
      for (const w of f.acroField.getWidgets()) {
        const ap = w.dict.lookup(PDFName.of('AP'));
        if (ap && ap.lookup) {
          const n = ap.lookup(PDFName.of('N'));
          if (n && n.keys) {
            const keys = n.keys().map((k) => k.asString());
            const on = keys.find((k) => k !== '/Off');
            if (on) { onState = on; break; }
          }
        }
      }
      if (onState) {
        console.log(`  PUSHBUTTON HAS ON-STATE (settable!) ${name} -> ${onState}`);
        failures += 1;
      }
      inventory.push({ idx: '', marker: '(btn)', type: 'Button', maxLen: '-', name });
    } else {
      inventory.push({ idx: '', marker: '?', type: t.replace('PDF', ''), maxLen: '-', name });
    }
  }

  // 7.3.5: set NeedAppearances via the private dict; do NOT call updateFieldAppearances().
  acro.acroForm.dict.set(PDFName.of('NeedAppearances'), PDFBool.True);
  const bytes = await doc.save({ updateFieldAppearances: false });
  const out = `/tmp/filled-${form.id}.pdf`;
  writeFileSync(out, bytes);

  // reload-assert (byte-grep would false-fail: pdf-lib writes object streams).
  const reloaded = await PDFDocument.load(bytes, { ignoreEncryption: true });
  const flagOk = reloaded.getForm().acroForm.dict.has(PDFName.of('NeedAppearances'));
  console.log(`  saved ${out} (${bytes.length} bytes); NeedAppearances on reload: ${flagOk}`);
  if (!flagOk) failures += 1;

  console.log('  --- inventory (text fields carry markers) ---');
  for (const r of inventory) {
    if (r.type === 'Button') continue; // omit the dozens of pushbuttons from the printout
    console.log(`  ${String(r.idx).padStart(2)} ${String(r.marker).padEnd(5)} ${r.type.padEnd(9)} maxLen=${String(r.maxLen).padEnd(3)} ${r.name}`);
  }
  const btnCount = inventory.filter((r) => r.type === 'Button').length;
  console.log(`  (${btnCount} pushbuttons classified non-data, not printed)`);
}

console.log(`\n${failures === 0 ? 'PASS' : 'FAIL (' + failures + ' problem(s))'}`);
process.exit(failures === 0 ? 0 : 1);
