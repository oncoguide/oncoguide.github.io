/* donate-common.js -- DONATIONS.md T4. Shared document engine + UI helpers for the donation
 * generators. Vanilla JS, no framework. Loaded lazily (the generator layout injects it on first
 * interaction). Depends on the vendored pdf-lib UMD (window.PDFLib), field-maps.js
 * (window.ONCO_FIELD_MAPS), and the data bridge window.oncoDonate = {assoc, fiscal, web3formsKey}
 * injected by layouts/donate-generator/single.html.
 *
 * D6 fill model: official ANAF PDF is loaded unchanged; we set the few REAL AcroForm fields that
 * exist and draw a positioned TEXT OVERLAY for the values the form has no field for (OncoGuide's
 * beneficiary/entity block). Nothing is renamed/moved/resized/restyled/flattened. NeedAppearances
 * is set so the real fields render across viewers (asserted via reload in tests, never byte-grep).
 *
 * No PII is stored or transmitted by us. The only network calls are: fetching the static template
 * PDFs, and (optionally, opt-in) a no-PII web3forms ping fired solely inside the send-copy click.
 */
(function (root) {
  'use strict';

  var TEMPLATE_BASE = '/donate/templates/';

  // ---- resolve an overlay "src" path like 'assoc.cif' / 'assoc.address_parts.strada' /
  // 'values.sumaRedirectionata' (T6: per-fill values join the constant association data) ----
  function resolveSrc(src, values) {
    var ctx = { assoc: (root.oncoDonate || {}).assoc || {}, values: values || {} };
    return src.split('.').reduce(function (o, k) { return o == null ? undefined : o[k]; }, ctx);
  }

  // ===================== CORE: fill an official ANAF form =====================
  // values = { <fieldKey>: string, checks: { <checkboxKey>: bool } }
  async function fillAnafForm(formKey, values) {
    var L = root.PDFLib;
    var map = root.ONCO_FIELD_MAPS[formKey];
    if (!map) throw new Error('unknown form ' + formKey);
    var buf = await fetch(TEMPLATE_BASE + map.template).then(function (r) {
      if (!r.ok) throw new Error('template fetch failed: ' + map.template);
      return r.arrayBuffer();
    });
    var doc = await L.PDFDocument.load(buf);
    var form = doc.getForm();

    // 1) real text fields (clamp to maxLength -- pdf-lib throws if exceeded)
    Object.keys(map.fields).forEach(function (key) {
      var v = values[key];
      if (v == null || v === '') return;
      var f = form.getTextField(map.fields[key]);
      var max = f.getMaxLength();
      var s = String(v);
      if (max != null && s.length > max) s = s.slice(0, max);
      f.setText(s);
    });

    // 2) checkboxes
    var checks = values.checks || {};
    Object.keys(map.checkboxes || {}).forEach(function (key) {
      if (checks[key]) form.getCheckBox(map.checkboxes[key]).check();
    });

    // 3) overlay (OncoGuide beneficiary/entity block + any positioned values)
    var font = await doc.embedFont(L.StandardFonts.Helvetica);
    (map.overlay || []).forEach(function (o) {
      var text = o.text != null ? o.text : resolveSrc(o.src, values);
      if (text == null || text === '') return;
      doc.getPage(o.page).drawText(String(text), {
        x: o.x, y: o.y, size: o.size || 9, font: font, color: L.rgb(0, 0, 0)
      });
    });

    // 4) NeedAppearances so the real fields render in every viewer (D6 / 7.3.5)
    form.acroForm.dict.set(L.PDFName.of('NeedAppearances'), L.PDFBool.True);
    return doc.save({ updateFieldAppearances: false });
  }

  // ===================== CORE: fill our sponsorship contract (T6) =====================
  // Real AcroForm template we own: set text fields + embed the signature image (setImage).
  async function fillContract(templateName, values, signaturePngDataUrl) {
    var L = root.PDFLib;
    var buf = await fetch(TEMPLATE_BASE + templateName).then(function (r) {
      if (!r.ok) throw new Error('template fetch failed: ' + templateName);
      return r.arrayBuffer();
    });
    var doc = await L.PDFDocument.load(buf);
    var form = doc.getForm();
    Object.keys(values).forEach(function (name) {
      var v = values[name];
      if (v == null || v === '') return;
      try { form.getTextField(name).setText(String(v)); }
      catch (e) {
        // Not a text field: contract checkboxes (T6 art5_a / art5_b) take a boolean true.
        try { if (v === true) form.getCheckBox(name).check(); } catch (e2) { /* unknown key */ }
      }
    });
    if (signaturePngDataUrl) {
      var png = await doc.embedPng(signaturePngDataUrl);
      // sponsor_semnatura is a pushbutton used as an image placeholder (App. B).
      form.getButton('sponsor_semnatura').setImage(png);
    }
    form.acroForm.dict.set(L.PDFName.of('NeedAppearances'), L.PDFBool.True);
    return doc.save({ updateFieldAppearances: false }); // never flatten: beneficiary block stays fillable
  }

  // ===================== validators =====================
  // Romanian CNP: 13 digits, control key 279146358279, remainder 10 -> control digit 1.
  function validCNP(cnp) {
    if (!/^\d{13}$/.test(cnp)) return false;
    var w = [2, 7, 9, 1, 4, 6, 3, 5, 8, 2, 7, 9], sum = 0;
    for (var i = 0; i < 12; i++) sum += parseInt(cnp[i], 10) * w[i];
    var c = sum % 11; if (c === 10) c = 1;
    return c === parseInt(cnp[12], 10);
  }

  // Romanian CUI checksum (control key 753217532, applied right-aligned to the digits before the
  // check digit; remainder*10 % 11, 10 -> 0). Accepts an optional leading "RO".
  function validCUI(cui) {
    var d = String(cui).toUpperCase().replace(/^RO/, '').replace(/\s/g, '');
    if (!/^\d{2,10}$/.test(d)) return false;
    var key = [7, 5, 3, 2, 1, 7, 5, 3, 2], ctrl = parseInt(d.slice(-1), 10), body = d.slice(0, -1);
    var sum = 0, kb = key.slice(key.length - body.length);
    for (var i = 0; i < body.length; i++) sum += parseInt(body[i], 10) * kb[i];
    var r = (sum * 10) % 11; if (r === 10) r = 0;
    return r === ctrl;
  }

  // IBAN mod-97 (ISO 13616): move first 4 chars to end, letters -> 10..35, big-int mod 97 === 1.
  function validIBAN(iban) {
    var s = String(iban).replace(/\s/g, '').toUpperCase();
    if (!/^[A-Z]{2}\d{2}[A-Z0-9]{10,30}$/.test(s)) return false;
    var re = s.slice(4) + s.slice(0, 4);
    var expanded = re.replace(/[A-Z]/g, function (ch) { return (ch.charCodeAt(0) - 55).toString(); });
    var rem = 0;
    for (var i = 0; i < expanded.length; i++) rem = (rem * 10 + (expanded.charCodeAt(i) - 48)) % 97;
    return rem === 1;
  }

  // ===================== output / delivery =====================
  function downloadPdf(bytes, filename) {
    var blob = new Blob([bytes], { type: 'application/pdf' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url; a.download = filename;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(function () { URL.revokeObjectURL(url); }, 4000);
  }

  // Short mailto (under ~300 chars; mobile clients truncate). Detail lives on the page (7.5).
  function buildMailto(to, subject, body) {
    var b = (body || '').slice(0, 280);
    return 'mailto:' + encodeURIComponent(to) +
      '?subject=' + encodeURIComponent(subject) +
      '&body=' + encodeURIComponent(b);
  }

  // Opt-in, no-PII ping. ONLY {type, locale} (+ web3forms' empty botcheck honeypot; no client
  // timestamp -- receipt time is server-side, S11). Caller fires it inside the send-copy click
  // handler, never automatically on generate (Section 11).
  function sendPing(type, locale) {
    var key = (root.oncoDonate || {}).web3formsKey;
    if (!key) return Promise.resolve();
    return fetch('https://api.web3forms.com/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({
        access_key: key,
        subject: 'OncoGuide donatie -- ' + type,
        type: type, locale: locale,
        botcheck: ''
      })
    }).catch(function () { /* best-effort; never blocks the user */ });
  }

  // ===================== step machine =====================
  // root element holds <section data-step="1..N">; returns a controller. Focus + ARIA-live managed.
  function createSteps(rootEl, opts) {
    opts = opts || {};
    var sections = Array.prototype.slice.call(rootEl.querySelectorAll('[data-step]'));
    var live = rootEl.querySelector('[data-step-live]');
    var cur = 0;
    function render() {
      sections.forEach(function (s, i) { s.hidden = i !== cur; });
      var h = sections[cur].querySelector('h2, h3, [tabindex], button, input, select, textarea');
      if (h && h.focus) h.focus();
      if (opts.onChange) opts.onChange(cur, sections[cur]);
    }
    function announce(msg) { if (live) { live.textContent = ''; setTimeout(function () { live.textContent = msg; }, 30); } }
    return {
      sections: sections,
      index: function () { return cur; },
      go: function (i) { if (i >= 0 && i < sections.length) { cur = i; render(); } },
      next: function () { if (cur < sections.length - 1) { cur++; render(); } },
      prev: function () { if (cur > 0) { cur--; render(); } },
      announce: announce,
      start: render
    };
  }

  // Wire a consent checkbox to gate one or more action buttons (Section 12): buttons stay disabled
  // until the box is checked.
  function consentGate(checkbox, buttons) {
    function sync() { buttons.forEach(function (b) { b.disabled = !checkbox.checked; }); }
    checkbox.addEventListener('change', sync); sync();
  }

  root.oncoDonateEngine = {
    fillAnafForm: fillAnafForm,
    fillContract: fillContract,
    validCNP: validCNP,
    validCUI: validCUI,
    validIBAN: validIBAN,
    downloadPdf: downloadPdf,
    buildMailto: buildMailto,
    sendPing: sendPing,
    createSteps: createSteps,
    consentGate: consentGate,
    _resolveSrc: resolveSrc
  };

  if (typeof module !== 'undefined' && module.exports) module.exports = root.oncoDonateEngine;
})(typeof window !== 'undefined' ? window : globalThis);
