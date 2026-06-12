/* donate-companies.js -- DONATIONS.md T6. Company sponsorship generator (the "20%" path, S8.1),
 * built on donate-common.js (engine), field-maps.js (verified ANAF map), i18n.js (all UI
 * strings; nothing user-facing is hard-coded here), signature.js (lazy-loaded canvas pad).
 *
 * Two sub-paths chosen at step 1 (S8.1): (a) sponsorizare cu plata directa -> sponsorship
 * contract only; (b) redirectionare prin formularul 177 -> contract (Art. 5 lit. b checked)
 * plus the pre-filled official ANAF Form 177.
 *
 * Config-driven eligibility (S8.1, hard rule): which regimes may use Form 177 comes from
 * data/fiscal.yaml flags.eligibility via window.oncoDonate.fiscal -- NO fiscal rule is
 * hard-coded here, so the accountant can correct it by config. Current config: profit tax yes;
 * microenterprises no (OUG 115/2023 -- honest donation-equivalent messaging, no tax credit);
 * IMCA no (verified, Art. 42 not applicable at IMCA level).
 *
 * D3: the in-browser signature is embedded ONLY in the sponsorship contract (our document) as a
 * convenience working copy; the done step says plainly that for ANAF purposes the contract is
 * printed and wet-signed by both parties. The ANAF Form 177 is NEVER signed in the browser.
 *
 * D6: the 177 is the unchanged official PDF; the company's own section I fields are set via the
 * engine, the OncoGuide beneficiary block + the per-fill amount/contract cells are positioned
 * text overlays (field-maps.js f177.overlay, incl. the T6 'values.*' entries).
 *
 * Privacy (S11/S12): all company data lives in this page's in-memory state only. The no-PII
 * ping fires ONLY inside the consent-gated send-copy click, never on generate.
 */
(function (root) {
  'use strict';

  // ---------- pure helpers (no DOM; exposed below for the Node test harness) ----------

  // S8.1 ceiling math: min(turnover_pct * CA, profit_tax_pct * impozit), minus what was already
  // granted this year, floored at 0. Whole lei (floor -- conservative for the supporter).
  function computeCeiling(ca, impozit, deja, ceilings) {
    var c = ceilings || {};
    var ceiling = Math.floor(Math.min(
      (c.sponsorship_turnover_pct || 0) * ca,
      (c.sponsorship_profit_tax_pct || 0) * impozit
    ));
    var available = Math.max(0, Math.floor(ceiling - deja));
    return { ceiling: ceiling, available: available };
  }

  // '1.234.567' / '1 234 567' / '1234567' -> 1234567 (whole lei); null when not a clean number.
  function parseAmount(s) {
    var d = String(s == null ? '' : s).trim().replace(/[.\s]/g, '').replace(',', '.');
    if (d === '' || !/^\d+(\.\d+)?$/.test(d)) return null;
    return parseFloat(d);
  }

  // 1234567 -> '1.234.567' (RON grouping; integers only).
  function fmtNumber(n) {
    return String(Math.floor(n)).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  }

  // Romanian amount-in-words for whole lei, ASCII (no diacritics -- contract overlay/fields are
  // Helvetica). Handles 0 .. 999,999,999 with the 'de' rule and feminine forms for mii.
  function roWordsLei(n) {
    n = Math.floor(Math.abs(n));
    if (n === 0) return 'zero';
    var UNITS = ['', 'unu', 'doi', 'trei', 'patru', 'cinci', 'sase', 'sapte', 'opt', 'noua'];
    var TEENS = ['zece', 'unsprezece', 'doisprezece', 'treisprezece', 'paisprezece',
                 'cincisprezece', 'saisprezece', 'saptesprezece', 'optsprezece', 'nouasprezece'];
    var TENS = ['', '', 'douazeci', 'treizeci', 'patruzeci', 'cincizeci', 'saizeci',
                'saptezeci', 'optzeci', 'nouazeci'];
    function under100(x) {
      if (x < 10) return UNITS[x];
      if (x < 20) return TEENS[x - 10];
      var t = TENS[Math.floor(x / 10)], u = x % 10;
      return u ? t + ' si ' + UNITS[u] : t;
    }
    function under1000(x) {
      var h = Math.floor(x / 100), r = x % 100, parts = [];
      if (h === 1) parts.push('o suta');
      else if (h === 2) parts.push('doua sute');
      else if (h > 2) parts.push(UNITS[h] + ' sute');
      if (r) parts.push(under100(r));
      return parts.join(' ');
    }
    // feminine forms before 'mii' (doua mii, douasprezece mii, douazeci si doua de mii)
    function feminize(words) {
      return words.replace(/doisprezece$/, 'douasprezece').replace(/doi$/, 'doua')
                  .replace(/unu$/, 'una');
    }
    function group(x, one, many) {
      if (x === 0) return '';
      if (x === 1) return one;
      var w = feminize(under1000(x));
      var needDe = !(x % 100 >= 1 && x % 100 <= 19);
      return w + (needDe ? ' de ' : ' ') + many;
    }
    var mil = Math.floor(n / 1000000), mii = Math.floor((n % 1000000) / 1000), rest = n % 1000;
    var out = [];
    if (mil) out.push(group(mil, 'un milion', 'milioane'));
    if (mii) out.push(group(mii, 'o mie', 'mii'));
    if (rest) out.push(under1000(rest));
    return out.join(' ');
  }

  // 'FIRMA Test S.R.L.' -> 'firma-test-s-r-l' (ASCII slug for the download filename).
  function slugify(s) {
    return String(s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '')
      .toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || 'firma';
  }

  // '2026-06-25' -> '25.06.2026'
  function fmtDateRo(iso) {
    var p = String(iso || '').split('-');
    return p.length === 3 ? p[2] + '.' + p[1] + '.' + p[0] : String(iso || '');
  }

  // dd.mm.yyyy for the contract date (local time -- the supporter's date).
  function todayRo(d) {
    d = d || new Date();
    var dd = String(d.getDate()), mm = String(d.getMonth() + 1);
    return (dd.length < 2 ? '0' + dd : dd) + '.' + (mm.length < 2 ? '0' + mm : mm) + '.' + d.getFullYear();
  }

  // Values for oncoDonateEngine.fillContract (Appendix B field names; art5_a/art5_b are the two
  // checkboxes refining App. B 'art5_varianta'; exactly one is true). Beneficiary identification
  // comes from association.yaml via the data bridge; representative/signature blanks stay EMPTY
  // for offline countersignature (D4).
  function buildContractValues(state, assoc, dateRo) {
    assoc = assoc || {};
    return {
      sponsor_denumire: state.denumire,
      sponsor_cui: state.cui,
      sponsor_reg_com: state.regCom,
      sponsor_sediu: state.sediu,
      sponsor_reprezentant: state.reprezentant,
      sponsor_calitate: state.calitate,
      sponsor_banca: state.banca,
      sponsor_iban: state.iban,
      suma: fmtNumber(state.suma),
      suma_litere: roWordsLei(state.suma),
      data_contract: dateRo,
      art5_a: state.subpath === 'a',
      art5_b: state.subpath === 'b',
      beneficiar_denumire: assoc.name,
      beneficiar_cif: assoc.cif,
      beneficiar_sediu: assoc.address,
      beneficiar_iban: assoc.iban,
      beneficiar_reg163: assoc.registru163_no
    };
  }

  // Values for oncoDonateEngine.fillAnafForm('f177', ...): the company's OWN section I real
  // fields + the per-fill overlay cells (sumaRedirectionata, contractNrData). cifAttr is left
  // empty deliberately (the printed form's attribute cell stays blank; CIF digits only, no RO).
  // The three section-II sums are emitted only when the profit-tax calculator ran (the ceiling
  // formula is profit-tax-specific, S8.1); otherwise the company's accountant completes them.
  function buildF177Values(state, dateRo) {
    var hasCeiling = state.regime === 'profit';
    return {
      year: state.anul,
      cif: String(state.cui || '').toUpperCase().replace(/^RO/, '').replace(/\s/g, ''),
      denumire: state.denumire,
      judet: state.judet,
      localitate: state.localitate,
      strada: state.strada,
      numar: state.numar,
      bloc: state.bloc,
      scara: state.scara,
      ap: state.ap,
      codPostal: state.codPostal,
      telefon: state.telefon,
      email: state.emailFirma,
      sumaMaxima: hasCeiling ? String(state.ceiling) : '',
      sumaAnterior: hasCeiling ? String(Math.floor(state.deja)) : '',
      sumaRamasa: hasCeiling ? String(state.available) : '',
      sumaRedirectionata: String(state.suma),
      contractNrData: 'din ' + dateRo,
      checks: { beneficiaryNonprofit: true }
    };
  }

  // regime radio value -> data/fiscal.yaml flags.eligibility key (S8.1; rule lives in config)
  var ELIGIBILITY_KEY = { profit: 'form177_profit_tax', micro: 'form177_micro', imca: 'form177_imca' };

  // ---------- flow ----------
  root.oncoInitFlow = function (genEl) {
    // Gate (S10): while registru163_active is false, render nothing and stay hidden.
    if (!genEl || !genEl.dataset || genEl.dataset.active !== 'true') return;
    if (genEl.dataset.rendered === '1') return;
    genEl.dataset.rendered = '1';

    var E = root.oncoDonateEngine;
    var D = root.oncoDonate || {};
    var fiscal = D.fiscal || {};
    var eligibility = (fiscal.flags || {}).eligibility || {};
    var ceilings = fiscal.ceilings || {};
    var deadlineIso = (fiscal.deadlines || {}).form177_next || '';
    // F177 anul = the profit-tax year being redirected = filing-deadline year - 1 (editable).
    var defaultYear = deadlineIso ? String(parseInt(deadlineIso.slice(0, 4), 10) - 1) : '';
    function t(key) { return root.oncoI18n.t(key, D.locale); }
    function txt(s) { return document.createTextNode(s); }

    var state = {
      regime: '', subpath: '',
      ca: 0, impozit: 0, deja: 0, ceiling: 0, available: 0, suma: 0,
      denumire: '', cui: '', regCom: '', sediu: '', reprezentant: '', calitate: '',
      banca: '', iban: '',
      anul: defaultYear, judet: '', localitate: '', strada: '', numar: '', bloc: '',
      scara: '', ap: '', codPostal: '', telefon: '', emailFirma: ''
    };
    var steps; // assigned after the sections exist; handlers below run only after that

    // ----- tiny DOM builder (textContent only -- user data can never become markup) -----
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

    function textField(id, labelKey, hintKey, extra) {
      var hintId = id + '-hint', errId = id + '-err';
      var attrs = { type: 'text', id: id, 'aria-describedby': hintId + ' ' + errId };
      Object.keys(extra || {}).forEach(function (k) { attrs[k] = extra[k]; });
      var input = el('input', attrs);
      var err = el('span', { className: 'donate-error', id: errId });
      var wrap = el('label', { className: 'donate-field', htmlFor: id }, [
        el('span', { text: t(labelKey) }),
        input,
        hintKey ? el('small', { id: hintId, text: t(hintKey) }) : el('small', { id: hintId }),
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

    function radioField(name, id, value, labelKey) {
      var input = el('input', { type: 'radio', name: name, id: id, value: value });
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

    // ---------- step 1: tax regime + sub-path (S8.1, config-driven) ----------
    var regProfit = radioField('t6-regime', 't6-reg-profit', 'profit', 't6RegimeProfit');
    var regMicro = radioField('t6-regime', 't6-reg-micro', 'micro', 't6RegimeMicro');
    var regImca = radioField('t6-regime', 't6-reg-imca', 'imca', 't6RegimeImca');
    var regimeNote = el('p', { className: 'donate-status' });
    var spA = radioField('t6-subpath', 't6-sub-a', 'a', 't6SubpathA');
    var spB = radioField('t6-subpath', 't6-sub-b', 'b', 't6SubpathB');
    var spBNote = el('p', null, [el('small', {
      text: t('t6SubpathBDeadline').replace('{data}', fmtDateRo(deadlineIso))
    })]);
    // sub-path (b) stays disabled until a regime marked eligible in fiscal.yaml is chosen
    spB.input.disabled = true;
    spBNote.hidden = true;
    var s1Err = el('span', { className: 'donate-error', id: 't6-s1-err' });
    var s1 = el('section', { className: 'donate-step', 'data-step': '1' }, [
      el('h2', { tabindex: '-1', text: t('t6Step1Title') }),
      el('p', { text: t('t6Intro') }),
      el('fieldset', null, [
        el('legend', { text: t('t6RegimeLegend') }),
        regProfit.wrap, regMicro.wrap, regImca.wrap
      ]),
      regimeNote,
      el('fieldset', null, [
        el('legend', { text: t('t6SubpathLegend') }),
        spA.wrap, spB.wrap, spBNote
      ]),
      s1Err
    ]);

    var REGIME_NOTE_KEY = { profit: 't6ProfitNote', micro: 't6MicroNote', imca: 't6ImcaNote' };
    function onRegimeChange(value) {
      state.regime = value;
      regimeNote.textContent = t(REGIME_NOTE_KEY[value]);
      // F177 sub-path only for regimes marked eligible in data/fiscal.yaml (S8.1)
      var ok = !!eligibility[ELIGIBILITY_KEY[value]];
      spB.input.disabled = !ok;
      spBNote.hidden = !ok;
      if (!ok && spB.input.checked) { spB.input.checked = false; state.subpath = ''; }
    }
    [regProfit, regMicro, regImca].forEach(function (r) {
      r.input.addEventListener('change', function () { onRegimeChange(r.input.value); });
    });
    [spA, spB].forEach(function (r) {
      r.input.addEventListener('change', function () { state.subpath = r.input.value; });
    });

    function validStep1() {
      if (!state.regime) { s1Err.textContent = t('t6RegimeRequired'); steps.announce(t('t6RegimeRequired')); regProfit.input.focus(); return false; }
      if (!state.subpath || (state.subpath === 'b' && !eligibility[ELIGIBILITY_KEY[state.regime]])) {
        s1Err.textContent = t('t6SubpathRequired'); steps.announce(t('t6SubpathRequired')); spA.input.focus(); return false;
      }
      s1Err.textContent = '';
      return true;
    }

    // ---------- step 2: ceiling calculator (S8.1) ----------
    var caF = textField('t6-ca', 't6CaLabel', 't6CaHint', { inputmode: 'numeric', autocomplete: 'off' });
    var impF = textField('t6-impozit', 't6ImpozitLabel', 't6ImpozitHint', { inputmode: 'numeric', autocomplete: 'off' });
    var dejaF = textField('t6-deja', 't6DejaLabel', 't6DejaHint', { inputmode: 'numeric', autocomplete: 'off' });
    dejaF.input.value = '0';
    var calcBtn = el('button', { type: 'button', text: t('t6CalcBtn') });
    var calcOut = el('p', { className: 'donate-status', 'aria-live': 'polite' });
    var sumaF = textField('t6-suma', 't6SumaLabel', 't6SumaHint', { inputmode: 'numeric', autocomplete: 'off' });
    var calcWrap = el('div', null, [caF.wrap, impF.wrap, dejaF.wrap, calcBtn, calcOut]);
    var calcSkipNote = el('p', { text: t('t6CalcSkipNote'), hidden: '' });
    var s2 = el('section', { className: 'donate-step', 'data-step': '2' }, [
      el('h2', { tabindex: '-1', text: t('t6Step2Title') }),
      el('p', { text: t('t6CalcIntro') }),
      calcWrap,
      calcSkipNote,
      sumaF.wrap
    ]);

    // The plafond applies to the profit-tax credit; for other regimes the calculator is hidden
    // and the company simply chooses an amount (honest messaging set in step 1).
    function syncStep2() {
      var isProfit = state.regime === 'profit';
      calcWrap.hidden = !isProfit;
      calcSkipNote.hidden = isProfit;
    }

    function runCalc(announceIt) {
      var ca = parseAmount(caF.input.value);
      var imp = parseAmount(impF.input.value);
      var deja = parseAmount(dejaF.input.value === '' ? '0' : dejaF.input.value);
      var bad = null;
      if (ca == null) { fail(caF, 'invalidAmount'); bad = bad || caF; } else { pass(caF); }
      if (imp == null) { fail(impF, 'invalidAmount'); bad = bad || impF; } else { pass(impF); }
      if (deja == null) { fail(dejaF, 'invalidAmount'); bad = bad || dejaF; } else { pass(dejaF); }
      if (bad) { steps.announce(t('invalidAmount')); bad.input.focus(); return null; }
      var r = computeCeiling(ca, imp, deja, ceilings);
      state.ca = ca; state.impozit = imp; state.deja = deja;
      state.ceiling = r.ceiling; state.available = r.available;
      var msg = t('t6CalcResult')
        .replace('{plafon}', fmtNumber(r.ceiling))
        .replace('{disponibil}', fmtNumber(r.available));
      calcOut.textContent = msg;
      if (announceIt) steps.announce(msg);
      return r;
    }
    calcBtn.addEventListener('click', function () { runCalc(true); });

    function validStep2() {
      var suma = parseAmount(sumaF.input.value);
      if (suma == null || suma < 1 || Math.floor(suma) !== suma) {
        fail(sumaF, 'invalidAmount'); steps.announce(t('invalidAmount')); sumaF.input.focus(); return false;
      }
      if (state.regime === 'profit') {
        if (!runCalc(false)) return false;
        if (suma > state.available) {
          sumaF.err.textContent = t('t6SumaTooBig').replace('{disponibil}', fmtNumber(state.available));
          sumaF.input.setAttribute('aria-invalid', 'true');
          steps.announce(sumaF.err.textContent);
          sumaF.input.focus();
          return false;
        }
      }
      pass(sumaF);
      state.suma = suma;
      return true;
    }

    // ---------- step 3: company data (App. B sponsor_* + F177 section I when sub-path b) ----------
    var denF = textField('t6-denumire', 't6DenumireLabel', null, { autocomplete: 'organization' });
    var cuiF = textField('t6-cui', 't6CuiLabel', 't6CuiHint', { autocomplete: 'off' });
    var regComF = textField('t6-regcom', 't6RegComLabel', 't6RegComHint', { autocomplete: 'off' });
    var sediuF = textField('t6-sediu', 't6SediuLabel', null, { autocomplete: 'off' });
    var reprF = textField('t6-reprezentant', 't6ReprezentantLabel', null, { autocomplete: 'off' });
    var calitF = textField('t6-calitate', 't6CalitateLabel', 't6CalitateHint', { autocomplete: 'off' });
    var bancaF = textField('t6-banca', 't6BancaLabel', null, { autocomplete: 'off' });
    var ibanF = textField('t6-iban', 't6IbanLabel', null, { autocomplete: 'off' });
    // F177 section-I extras (the form's own address grid cells, field-maps.js f177.fields)
    var anulF = textField('t6-anul', 't6AnulLabel', 't6AnulHint', { maxlength: '4', inputmode: 'numeric', autocomplete: 'off' });
    anulF.input.value = defaultYear;
    var judF = textField('t6-judet', 't6JudetLabel', null, { autocomplete: 'off' });
    var locF = textField('t6-localitate', 't6LocalitateLabel', null, { autocomplete: 'off' });
    var strF = textField('t6-strada', 't6StradaLabel', null, { autocomplete: 'off' });
    var nrF = textField('t6-numar', 't6NumarLabel', null, { autocomplete: 'off' });
    var blocF = textField('t6-bloc', 't6BlocLabel', null, { autocomplete: 'off' });
    var scaraF = textField('t6-scara', 't6ScaraLabel', null, { autocomplete: 'off' });
    var apF = textField('t6-ap', 't6ApLabel', null, { autocomplete: 'off' });
    var cpF = textField('t6-codpostal', 't6CodPostalLabel', null, { autocomplete: 'off' });
    var telF = textField('t6-telefon', 't6TelefonLabel', 't6OptionalHint', { autocomplete: 'off' });
    var emF = textField('t6-emailfirma', 't6EmailFirmaLabel', 't6OptionalHint', { autocomplete: 'off' });
    var bSection = el('div', { hidden: '' }, [
      el('h3', { text: t('t6F177SectionTitle') }),
      el('p', null, [el('small', { text: t('t6F177SectionHint') })]),
      anulF.wrap, judF.wrap, locF.wrap, strF.wrap, nrF.wrap, blocF.wrap, scaraF.wrap,
      apF.wrap, cpF.wrap, telF.wrap, emF.wrap
    ]);
    var s3 = el('section', { className: 'donate-step', 'data-step': '3' }, [
      el('h2', { tabindex: '-1', text: t('t6Step3Title') }),
      el('p', { text: t('t6Step3Intro') }),
      denF.wrap, cuiF.wrap, regComF.wrap, sediuF.wrap, reprF.wrap, calitF.wrap,
      bancaF.wrap, ibanF.wrap,
      bSection
    ]);

    function validStep3() {
      var firstBad = null;
      function req(field, key) {
        var v = field.input.value.trim();
        if (v === '') { fail(field, 'required'); firstBad = firstBad || { f: field, k: 'required' }; }
        else { pass(field); if (key) state[key] = v; }
        return v;
      }
      req(denF, 'denumire');
      var cui = cuiF.input.value.trim();
      if (E.validCUI(cui)) { pass(cuiF); state.cui = cui.toUpperCase().replace(/\s/g, ''); }
      else { fail(cuiF, 'invalidCUI'); firstBad = firstBad || { f: cuiF, k: 'invalidCUI' }; }
      req(regComF, 'regCom');
      req(sediuF, 'sediu');
      req(reprF, 'reprezentant');
      req(calitF, 'calitate');
      req(bancaF, 'banca');
      var iban = ibanF.input.value.trim();
      if (E.validIBAN(iban)) { pass(ibanF); state.iban = iban.toUpperCase(); }
      else { fail(ibanF, 'invalidIBAN'); firstBad = firstBad || { f: ibanF, k: 'invalidIBAN' }; }
      if (state.subpath === 'b') {
        var an = anulF.input.value.trim();
        if (/^\d{4}$/.test(an)) { pass(anulF); state.anul = an; }
        else { fail(anulF, 'invalidYear'); firstBad = firstBad || { f: anulF, k: 'invalidYear' }; }
        req(judF, 'judet');
        req(locF, 'localitate');
        req(strF, 'strada');
        req(nrF, 'numar');
        state.bloc = blocF.input.value.trim();
        state.scara = scaraF.input.value.trim();
        state.ap = apF.input.value.trim();
        state.codPostal = cpF.input.value.trim();
        state.telefon = telF.input.value.trim();
        state.emailFirma = emF.input.value.trim();
      }
      if (firstBad) {
        steps.announce(t(firstBad.k));
        firstBad.f.input.focus();
        return false;
      }
      return true;
    }

    // ---------- step 4: review ----------
    var reviewDl = el('dl');
    var s4 = el('section', { className: 'donate-step', 'data-step': '4' }, [
      el('h2', { tabindex: '-1', text: t('t6Step4Title') }),
      reviewDl
    ]);
    function fillReview() {
      while (reviewDl.firstChild) reviewDl.removeChild(reviewDl.firstChild);
      function row(labelKey, value) {
        reviewDl.appendChild(el('dt', { text: t(labelKey) }));
        reviewDl.appendChild(el('dd', { text: value }));
      }
      row('t6ReviewRegime', t({ profit: 't6RegimeProfit', micro: 't6RegimeMicro', imca: 't6RegimeImca' }[state.regime]));
      row('t6ReviewSubpath', t(state.subpath === 'b' ? 't6SubpathB' : 't6SubpathA'));
      if (state.regime === 'profit') {
        row('t6ReviewCeiling', fmtNumber(state.ceiling) + ' lei');
        row('t6ReviewAvailable', fmtNumber(state.available) + ' lei');
      }
      row('t6ReviewSuma', fmtNumber(state.suma) + ' lei (' + roWordsLei(state.suma) + ' lei)');
      row('t6DenumireLabel', state.denumire);
      row('t6CuiLabel', state.cui);
      row('t6RegComLabel', state.regCom);
      row('t6SediuLabel', state.sediu);
      row('t6ReprezentantLabel', state.reprezentant + ' (' + state.calitate + ')');
      row('t6BancaLabel', state.banca);
      row('t6IbanLabel', state.iban);
      if (state.subpath === 'b') {
        row('t6AnulLabel', state.anul);
        row('t6ReviewAddress', [state.strada, state.numar, state.bloc, state.scara, state.ap,
          state.localitate, state.judet, state.codPostal].filter(Boolean).join(', '));
        if (state.telefon) row('t6TelefonLabel', state.telefon);
        if (state.emailFirma) row('t6EmailFirmaLabel', state.emailFirma);
      }
    }

    // ---------- step 5: signature (contract ONLY, D3) + GDPR consent ----------
    var canvas = el('canvas', { className: 'donate-signature-frame', width: '480', height: '150' });
    var pad = null;
    var sigErr = el('span', { className: 'donate-error', id: 't6-sig-err' });
    var clearBtn = el('button', { type: 'button', text: t('t6SignClear') });
    var typedIn = el('input', { type: 'text', id: 't6-typed', autocomplete: 'off' });
    var typedBtn = el('button', { type: 'button', text: t('t6TypedApply') });
    var gdpr = checkboxField('t6-gdpr', 'consentLabel');
    var s5 = el('section', { className: 'donate-step', 'data-step': '5' }, [
      el('h2', { tabindex: '-1', text: t('t6Step5Title') }),
      el('p', { text: t('t6SignIntro') }),
      el('p', null, [el('small', { text: t('t6SignDraftNote') })]),
      canvas,
      el('div', { className: 'donate-nav' }, [clearBtn]),
      el('label', { className: 'donate-field', htmlFor: 't6-typed' }, [
        el('span', { text: t('t6TypedLabel') }), typedIn
      ]),
      el('div', { className: 'donate-nav' }, [typedBtn]),
      sigErr,
      el('h3', { text: t('t6GdprTitle') }),
      el('p', { text: t('t6GdprIntro') }),
      gdpr.wrap,
      el('p', null, [
        el('a', { href: t('t6PrivacyUrl'), text: t('t6PrivacyLinkText') })
      ]),
      el('p', null, [el('small', { text: t('noPiiPing') })])
    ]);

    // signature.js loads lazily on first entry to step 5 (like the other modules)
    function ensurePad() {
      return root.oncoLoad('signature.js').then(function () {
        if (!pad) pad = root.oncoSignature.createSignaturePad(canvas);
        return pad;
      });
    }
    clearBtn.addEventListener('click', function () { if (pad) { pad.clear(); sigErr.textContent = ''; } });
    typedBtn.addEventListener('click', function () {
      ensurePad().then(function (p) {
        p.fromTypedName(typedIn.value);
        if (!p.isEmpty()) sigErr.textContent = '';
      });
    });

    function validStep5() {
      if (!pad || pad.isEmpty()) {
        sigErr.textContent = t('t6SignRequired');
        steps.announce(t('t6SignRequired'));
        canvas.focus && canvas.focus();
        return false;
      }
      sigErr.textContent = '';
      return true;
    }

    // ---------- step 6: generate + done (7.4 routes, D3 instructions) ----------
    var genBtn = el('button', { type: 'button', className: 'donate-generate-btn', text: t('generate') });
    var statusP = el('p', { className: 'donate-status', text: '' });
    var sendBtn = el('button', { type: 'button', className: 'donate-generate-btn', text: t('sendCopy') });
    var routesOl = el('ol');
    var doneBox = el('div', { hidden: '' }, [
      el('h3', { text: t('t6RoutesTitle') }),
      routesOl,
      sendBtn,
      el('p', null, [el('small', { text: t('sendCopyHint') + ' ' + t('t6SendCopyGate') })])
    ]);
    var s6 = el('section', { className: 'donate-step', 'data-step': '6' }, [
      el('h2', { tabindex: '-1', text: t('t6Step6Title') }),
      el('p', { text: t('t6GenerateHint') }),
      genBtn,
      statusP,
      doneBox
    ]);
    function fillRoutes() {
      while (routesOl.firstChild) routesOl.removeChild(routesOl.firstChild);
      routesOl.appendChild(el('li', { text: t('t6RoutePrint') }));
      routesOl.appendChild(el('li', { text: t('t6RouteCountersign') }));
      if (state.subpath === 'a') {
        routesOl.appendChild(el('li', { text: t('t6RoutePay') }));
      } else {
        routesOl.appendChild(el('li', {
          text: t('t6Route177').replace('{data}', fmtDateRo(deadlineIso))
        }));
        routesOl.appendChild(el('li', { text: t('t6Route177Note') }));
      }
    }

    genBtn.addEventListener('click', function () {
      genBtn.disabled = true;
      statusP.textContent = t('t6Generating');
      steps.announce(t('t6Generating'));
      var dateRo = todayRo();
      var slug = slugify(state.denumire);
      // pdf-lib loads ONLY now (lazy, S7.1); the engine needs window.PDFLib.
      root.oncoLoad('pdf-lib.min.js')
        .then(function () {
          return E.fillContract('sponsorship-contract-ro.pdf',
            buildContractValues(state, D.assoc, dateRo), pad ? pad.toPngDataUrl() : null);
        })
        .then(function (bytes) {
          E.downloadPdf(bytes, 'Contract-Sponsorizare-OncoGuide-' + slug + '.pdf');
          if (state.subpath !== 'b') return null;
          return E.fillAnafForm('f177', buildF177Values(state, dateRo)).then(function (b177) {
            E.downloadPdf(b177, 'Formular-177-OncoGuide-' + slug + '.pdf');
          });
        })
        .then(function () {
          statusP.textContent = t(state.subpath === 'b' ? 't6GeneratedBoth' : 't6Generated');
          steps.announce(statusP.textContent);
          fillRoutes();
          doneBox.hidden = false;
          // NO sendPing here: the ping is opt-in and fires only in the send-copy click (S11).
        })
        .catch(function () {
          statusP.textContent = t('t6GenerateError');
          steps.announce(t('t6GenerateError'));
        })
        .then(function () { genBtn.disabled = false; });
    });

    sendBtn.addEventListener('click', function () {
      // Same click handler: no-PII ping + the supporter's own mail client (S11, 7.5).
      E.sendPing('sponsorship', D.locale);
      root.location.href = E.buildMailto((D.assoc || {}).email || '', t('mailSubject'), t('mailBody'));
    });
    E.consentGate(gdpr.input, [sendBtn]); // GDPR consent gates ONLY the send-copy action

    // ---------- navigation ----------
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

    s1.appendChild(nav(false, true, validStep1));
    s2.appendChild(nav(true, true, validStep2));
    s3.appendChild(nav(true, true, validStep3));
    s4.appendChild(nav(true, true));
    s5.appendChild(nav(true, true, validStep5));
    s6.appendChild(nav(true, false));

    genEl.appendChild(el('div', { className: 'donate-steps' }, [s1, s2, s3, s4, s5, s6]));
    steps = E.createSteps(genEl, {
      onChange: function (i) {
        if (i === 1) syncStep2();
        if (i === 2) bSection.hidden = state.subpath !== 'b';
        if (i === 3) fillReview();
        if (i === 4) ensurePad(); // lazy-load the signature pad on entering step 5
      }
    });
    genEl.removeAttribute('hidden');
    steps.start();
  };

  // Test hooks (Node harness): pure builders, no DOM required.
  root.oncoDonateCompanies = {
    computeCeiling: computeCeiling,
    parseAmount: parseAmount,
    fmtNumber: fmtNumber,
    roWordsLei: roWordsLei,
    slugify: slugify,
    fmtDateRo: fmtDateRo,
    todayRo: todayRo,
    buildContractValues: buildContractValues,
    buildF177Values: buildF177Values
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = root.oncoDonateCompanies;
})(typeof window !== 'undefined' ? window : globalThis);
