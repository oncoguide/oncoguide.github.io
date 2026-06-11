/* i18n.js -- DONATIONS.md T4. UI strings for the donation generator flows, keyed per locale.
 * The generators are Romanian-first (DONATIONS.md 5.1): RO is complete; other locales fall back
 * to RO until/if a generator is localized. Page-level chrome uses Hugo i18n (i18n/*.yaml); these
 * are the strings used by the browser flow scripts (donate-common/individuals/companies).
 * Access via window.oncoI18n.t(key, locale). T5/T6 add flow-specific keys here.
 */
(function (root) {
  'use strict';

  var STRINGS = {
    ro: {
      // navigation
      next: 'Continua',
      prev: 'Inapoi',
      review: 'Verifica datele',
      edit: 'Modifica',
      generate: 'Genereaza si descarca',
      done: 'Gata',
      // delivery
      sendCopy: 'Trimite-ne o copie',
      sendCopyHint: 'Se deschide aplicatia ta de email. Ataseaza fisierul descarcat si trimite-l.',
      mailSubject: 'Document donatie OncoGuide',
      mailBody: 'Buna ziua, atasez documentul generat pe site pentru donatia catre Asociatia OncoGuide. Multumesc.',
      // consent / privacy
      consentLabel: 'Sunt de acord ca datele din document sa fie comunicate Asociatiei OncoGuide, conform politicii de confidentialitate.',
      consentRequired: 'Bifeaza acordul ca sa poti trimite o copie.',
      noPiiPing: 'Daca trimiti o copie, anuntam asociatia printr-un mesaj fara date personale (doar tipul si limba).',
      // validation
      required: 'Camp obligatoriu',
      invalidCNP: 'CNP invalid (13 cifre, cu cifra de control corecta).',
      invalidCUI: 'CUI invalid.',
      invalidIBAN: 'IBAN invalid.',
      invalidYear: 'An invalid.',
      invalidAmount: 'Suma invalida.',
      // gate (registru163 not yet active)
      gateClosed: 'Indisponibil in acest ciclu, pana la inscrierea Asociatiei OncoGuide in Registrul entitatilor nonprofit (ANAF). Pana atunci, poti face o donatie directa prin transfer bancar.',
      // after-print guidance
      manualAfterPrintTitle: 'Dupa printare, completeaza de mana:',
      printSign: 'Printeaza documentul si semneaza-l de mana.'
    }
  };

  function t(key, locale) {
    var l = STRINGS[locale] || STRINGS.ro;
    var v = (l[key] != null) ? l[key] : STRINGS.ro[key];
    return (v != null) ? v : key;
  }

  root.oncoI18n = { t: t, strings: STRINGS };
  if (typeof module !== 'undefined' && module.exports) module.exports = root.oncoI18n;
})(typeof window !== 'undefined' ? window : globalThis);
