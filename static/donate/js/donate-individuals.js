/* donate-individuals.js -- DONATIONS.md T5. Form 230 generator flow for individuals (the 3,5%
 * path, S8.2), built on donate-common.js (engine), field-maps.js (verified ANAF map), i18n.js
 * (all UI strings; nothing user-facing is hard-coded here).
 *
 * D6 reality (verified in T3): the official 230 has fillable AcroForm fields ONLY for the income
 * year and the donor CNP (+ their page-2 mirrors) and 4 data checkboxes. The OncoGuide entity
 * block is pre-filled automatically by the engine's positioned text overlay. The donor's
 * name/address have NO fields on the form -- they are written BY HAND after printing, and the UI
 * says this plainly (review step + done step, list from ONCO_FIELD_MAPS.f230.manualAfterPrint).
 *
 * D3: the 230 is NEVER signed in the browser -- no signature step; the supporter signs the
 * printed form by hand. Step 5 holds ONLY the GDPR consent that gates the optional send-copy.
 *
 * Privacy (S11/S12): the CNP lives only in this page's in-memory state object. It is never put
 * in a URL, localStorage, sessionStorage, cookie, or network request. The deliberately minimal
 * filename (Formular-230-OncoGuide.pdf, no name slug -- we do not even collect the donor's name)
 * keeps data minimization strict. The no-PII ping fires ONLY inside the send-copy click handler,
 * never on generate.
 */
(function (root) {
  'use strict';

  // Build the exact values object passed to oncoDonateEngine.fillAnafForm('f230', ...).
  // Pure function (no DOM), exposed below for the Node test harness.
  // supportEntity ("2. Sustinerea unei entitati nonprofit") is ALWAYS checked (field-maps.js);
  // twoYear and shareConsent are the donor's own choices; every value also fills its page-2
  // mirror per DONATIONS.md 7.3.4.
  function buildF230Values(state) {
    return {
      year: state.year,
      yearCopy: state.year,
      cnp: state.cnp,
      cnpCopy: state.cnp,
      checks: {
        supportEntity: true,
        supportEntityCopy: true,
        twoYear: !!state.twoYear,
        twoYearCopy: !!state.twoYear,
        shareConsent: !!state.shareConsent,
        shareConsentCopy: !!state.shareConsent
      }
    };
  }

  // '2027-05-25' -> '25.05.2027'
  function fmtDateRo(iso) {
    var p = String(iso || '').split('-');
    return p.length === 3 ? p[2] + '.' + p[1] + '.' + p[0] : String(iso || '');
  }

  // Tiny DOM builder (textContent only -- no innerHTML, so user data can never become markup).
  function el(tag, attrs, children) {
    var n = document.createElement(tag);
    if (attrs) {
      Object.keys(attrs).forEach(function (k) {
        if (k === 'text') n.textContent = attrs[k];
        else if (k === 'className') n.className = attrs[k];
        else if (k === 'htmlFor') n.htmlFor = attrs[k];
        else n.setAttribute(k, attrs[k]);
      });
    }
    (children || []).forEach(function (c) { n.appendChild(c); });
    return n;
  }

  root.oncoInitFlow = function (genEl) {
    // Gate (S10): while registru163_active is false, render nothing and stay hidden.
    if (!genEl || !genEl.dataset || genEl.dataset.active !== 'true') return;
    if (genEl.dataset.rendered === '1') return;
    genEl.dataset.rendered = '1';

    var E = root.oncoDonateEngine;
    var D = root.oncoDonate || {};
    var map = (root.ONCO_FIELD_MAPS || {}).f230 || {};
    function t(key) { return root.oncoI18n.t(key, D.locale); }
    function txt(s) { return document.createTextNode(s); }

    var deadlineIso = (((D.fiscal || {}).deadlines) || {}).form230_next || '';
    // Default income year = filing-deadline year - 1 (form230_next 2027-05-25 -> 2026 income).
    var incomeYear = deadlineIso ? String(parseInt(deadlineIso.slice(0, 4), 10) - 1) : '';
    var state = { cnp: '', year: incomeYear, twoYear: false, shareConsent: false };
    var steps; // assigned after the sections exist; handlers below run only after that

    function manualUl() {
      return el('ul', null, (map.manualAfterPrint || []).map(function (item) {
        return el('li', { text: item });
      }));
    }

    function textField(id, labelKey, hintKey, extra) {
      var hintId = id + '-hint', errId = id + '-err';
      var attrs = { type: 'text', id: id, 'aria-describedby': hintId + ' ' + errId };
      Object.keys(extra || {}).forEach(function (k) { attrs[k] = extra[k]; });
      var input = el('input', attrs);
      var err = el('span', { className: 'donate-error', id: errId });
      var wrap = el('label', { className: 'donate-field', htmlFor: id }, [
        el('span', { text: t(labelKey) }),
        input,
        el('small', { id: hintId, text: t(hintKey) }),
        err
      ]);
      return { wrap: wrap, input: input, err: err };
    }

    function checkboxField(id, labelKey) {
      var input = el('input', { type: 'checkbox', id: id });
      var wrap = el('label', { className: 'donate-field', htmlFor: id }, [
        input, txt(' '), txt(t(labelKey))
      ]);
      return { wrap: wrap, input: input };
    }

    function fail(field, msgKey) {
      field.err.textContent = t(msgKey);
      field.input.setAttribute('aria-invalid', 'true');
    }
    function pass(field) {
      field.err.textContent = '';
      field.input.setAttribute('aria-invalid', 'false');
    }

    // ---------- step 1: intro / eligibility (S8.2) ----------
    var s1 = el('section', { className: 'donate-step', 'data-step': '1' }, [
      el('h2', { tabindex: '-1', text: t('t5Step1Title') }),
      el('p', { text: t('t5Intro') }),
      el('p', { text: t('t5IntroPfa') }),
      el('p', {
        text: t('t5DeadlineClosed') + ' ' + t('t5DeadlineNext')
          .replace('{an}', incomeYear)
          .replace('{data}', fmtDateRo(deadlineIso))
      })
    ]);

    // ---------- step 2: eligibility confirm ----------
    var confirm = checkboxField('f230-confirm', 't5ConfirmLabel');
    var confirmErr = el('span', { className: 'donate-error', id: 'f230-confirm-err' });
    var s2 = el('section', { className: 'donate-step', 'data-step': '2' }, [
      el('h2', { tabindex: '-1', text: t('t5Step2Title') }),
      confirm.wrap,
      confirmErr
    ]);

    // ---------- step 3: data (only what the PDF can hold, S8.2/D6) ----------
    var cnpF = textField('f230-cnp', 't5CnpLabel', 't5CnpHint',
      { maxlength: '13', inputmode: 'numeric', autocomplete: 'off' });
    var yearF = textField('f230-year', 't5YearLabel', 't5YearHint',
      { maxlength: '4', inputmode: 'numeric', autocomplete: 'off' });
    yearF.input.value = incomeYear;
    var twoYearC = checkboxField('f230-twoyear', 't5TwoYearLabel');
    // The ANAF form's OWN data-sharing checkbox -- distinct from our GDPR consent in step 5.
    var shareC = checkboxField('f230-share', 't5ShareLabel');
    var s3 = el('section', { className: 'donate-step', 'data-step': '3' }, [
      el('h2', { tabindex: '-1', text: t('t5Step3Title') }),
      cnpF.wrap,
      yearF.wrap,
      twoYearC.wrap,
      shareC.wrap,
      el('p', null, [el('small', { text: t('t5ShareHint') })])
    ]);

    // ---------- step 4: review + hand-written-after-print note ----------
    var rCnp = el('dd'), rYear = el('dd'), rTwo = el('dd'), rShare = el('dd');
    var s4 = el('section', { className: 'donate-step', 'data-step': '4' }, [
      el('h2', { tabindex: '-1', text: t('t5Step4Title') }),
      el('dl', null, [
        el('dt', { text: t('t5ReviewCnp') }), rCnp,
        el('dt', { text: t('t5ReviewYear') }), rYear,
        el('dt', { text: t('t5ReviewTwoYear') }), rTwo,
        el('dt', { text: t('t5ReviewShare') }), rShare
      ]),
      el('p', { text: t('t5ManualIntro') }),
      el('p', null, [el('strong', { text: t('manualAfterPrintTitle') })]),
      manualUl()
    ]);
    function fillReview() {
      rCnp.textContent = state.cnp;
      rYear.textContent = state.year;
      rTwo.textContent = state.twoYear ? t('t5Yes') : t('t5No');
      rShare.textContent = state.shareConsent ? t('t5Yes') : t('t5No');
    }

    // ---------- step 5: GDPR consent ONLY (no signature -- D3) ----------
    var gdpr = checkboxField('f230-gdpr', 'consentLabel');
    var s5 = el('section', { className: 'donate-step', 'data-step': '5' }, [
      el('h2', { tabindex: '-1', text: t('t5Step5Title') }),
      el('p', { text: t('t5GdprIntro') }),
      gdpr.wrap,
      el('p', null, [
        el('a', { href: t('t5PrivacyUrl'), text: t('t5PrivacyLinkText') })
      ]),
      el('p', null, [el('small', { text: t('noPiiPing') })])
    ]);

    // ---------- step 6: generate + done ----------
    var genBtn = el('button', { type: 'button', className: 'donate-generate-btn', text: t('generate') });
    var statusP = el('p', { className: 'donate-status', text: '' });
    var sendBtn = el('button', { type: 'button', className: 'donate-generate-btn', text: t('sendCopy') });
    var doneBox = el('div', { hidden: '' }, [
      el('h3', { text: t('t5RoutesTitle') }),
      el('ol', null, [
        el('li', { text: t('t5RoutePrint') }),
        el('li', { text: t('t5RouteHandwrite') }, [manualUl()]),
        el('li', { text: t('t5RouteSign') }),
        el('li', { text: t('t5RouteSubmit') })
      ]),
      el('p', { text: t('t5RouteSpv') }),
      el('p', { text: t('t5Payout') }),
      sendBtn,
      el('p', null, [el('small', { text: t('sendCopyHint') + ' ' + t('t5SendCopyGate') })])
    ]);
    var s6 = el('section', { className: 'donate-step', 'data-step': '6' }, [
      el('h2', { tabindex: '-1', text: t('t5Step6Title') }),
      el('p', { text: t('t5GenerateHint') }),
      genBtn,
      statusP,
      doneBox
    ]);

    genBtn.addEventListener('click', function () {
      genBtn.disabled = true;
      statusP.textContent = t('t5Generating');
      steps.announce(t('t5Generating'));
      // pdf-lib loads ONLY now (lazy, S7.1); the engine needs window.PDFLib.
      root.oncoLoad('pdf-lib.min.js')
        .then(function () { return E.fillAnafForm('f230', buildF230Values(state)); })
        .then(function (bytes) {
          // Data minimization: no name slug in the filename -- the donor's name is deliberately
          // never collected (the form has no field for it; it is hand-written after printing).
          E.downloadPdf(bytes, 'Formular-230-OncoGuide.pdf');
          statusP.textContent = t('t5Generated');
          steps.announce(t('t5Generated'));
          doneBox.hidden = false;
          // NO sendPing here: the ping is opt-in and fires only in the send-copy click (S11).
        })
        .catch(function () {
          statusP.textContent = t('t5GenerateError');
          steps.announce(t('t5GenerateError'));
        })
        .then(function () { genBtn.disabled = false; });
    });

    sendBtn.addEventListener('click', function () {
      // Same click handler: no-PII ping + the supporter's own mail client (S11, 7.5).
      E.sendPing('form230', D.locale);
      root.location.href = E.buildMailto((D.assoc || {}).email || '', t('mailSubject'), t('mailBody'));
    });
    E.consentGate(gdpr.input, [sendBtn]); // GDPR consent gates ONLY the send-copy action

    // ---------- validation-gated navigation ----------
    function validConfirm() {
      if (confirm.input.checked) { confirmErr.textContent = ''; return true; }
      confirmErr.textContent = t('t5ConfirmRequired');
      steps.announce(t('t5ConfirmRequired'));
      confirm.input.focus();
      return false;
    }

    function validData() {
      var firstBad = null;
      var cnp = cnpF.input.value.replace(/\s+/g, '');
      if (E.validCNP(cnp)) { pass(cnpF); } else { fail(cnpF, 'invalidCNP'); firstBad = firstBad || { f: cnpF, k: 'invalidCNP' }; }
      var year = yearF.input.value.replace(/\s+/g, '');
      if (/^\d{4}$/.test(year)) { pass(yearF); } else { fail(yearF, 'invalidYear'); firstBad = firstBad || { f: yearF, k: 'invalidYear' }; }
      if (firstBad) {
        steps.announce(t(firstBad.k));
        firstBad.f.input.focus();
        return false;
      }
      state.cnp = cnp;
      state.year = year;
      state.twoYear = twoYearC.input.checked;
      state.shareConsent = shareC.input.checked;
      return true;
    }

    function nav(withPrev, withNext, beforeNext) {
      var box = el('div', { className: 'donate-nav' });
      if (withPrev) {
        var p = el('button', { type: 'button', text: t('prev') });
        p.addEventListener('click', function () { steps.prev(); });
        box.appendChild(p);
      }
      if (withNext) {
        var n = el('button', { type: 'button', text: t('next') });
        n.addEventListener('click', function () {
          if (!beforeNext || beforeNext()) steps.next();
        });
        box.appendChild(n);
      }
      return box;
    }

    s1.appendChild(nav(false, true));
    s2.appendChild(nav(true, true, validConfirm));
    s3.appendChild(nav(true, true, validData));
    s4.appendChild(nav(true, true));
    s5.appendChild(nav(true, true));
    s6.appendChild(nav(true, false));

    genEl.appendChild(el('div', { className: 'donate-steps' }, [s1, s2, s3, s4, s5, s6]));
    steps = E.createSteps(genEl, {
      onChange: function (i) { if (i === 3) fillReview(); }
    });
    genEl.removeAttribute('hidden');
    steps.start();
  };

  // Test hook (Node harness): the pure values builder, no DOM required.
  root.oncoDonateIndividuals = { buildF230Values: buildF230Values, fmtDateRo: fmtDateRo };
  if (typeof module !== 'undefined' && module.exports) module.exports = root.oncoDonateIndividuals;
})(typeof window !== 'undefined' ? window : globalThis);
