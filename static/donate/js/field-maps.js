/* field-maps.js -- DONATIONS.md T3. VERIFIED 2026-06-11 against the blank ANAF originals and
 * the .private precompletate (same page geometry: 595.276 x 841.890).
 *
 * IMPORTANT FINDING (corrects Appendix A): ANAF Forms 230 and 177 are plain AcroForms, but the
 * BENEFICIARY/ENTITY sections (where OncoGuide's data goes) have NO fillable fields -- they are
 * comb-cell pushbuttons / plain print regions. So pre-filling OncoGuide's data is done by a
 * positioned TEXT OVERLAY on the original page (exactly how the .private precompletate were made),
 * while the few real AcroForm fields (year, donor CNP on 230; the company's own section on 177)
 * are set via pdf-lib setText/check. The official form is never modified: no field is renamed,
 * moved, resized, or restyled; we only add values (in fields or as a text layer at the form's own
 * positions). See DONATIONS.md S7 + Appendix A.
 *
 * No PII here: only public association data positions and ANAF field names. Overlay TEXT values
 * come from window.oncoDonate.assoc at runtime (single source = data/association.yaml); this file
 * holds only WHERE each value goes, not the donor's data.
 *
 * Coordinate system: pdf-lib drawText uses a bottom-left origin (y up). The y values below are
 * pageHeight(841.89) - yMax(from pdftotext, top-left origin) = the glyph baseline (approx; the
 * T4 fill-test fine-tunes font size ~9pt and any +/-2pt baseline nudge against a real viewer).
 */
(function (root) {
  'use strict';

  // Page height for the OVERLAY pages only (form page 0/1 = A4, 595.276 x 841.890).
  // Note: pages 3+ of both PDFs are US Letter (612 x 792); never reuse PAGE_H there. All overlay
  // entries below target page 0, so PAGE_H is correct for every entry in this file.
  var PAGE_H = 841.89;

  var FIELD_MAPS = {
    // ===================== FORM 230 (individuals, 3.5%) =====================
    f230: {
      template: 'form-230-original.pdf',
      sha256: '4908d9426c04ebaba2eb72c399af87c63c77f71468ffcb28d6b04d435124589d',
      // Real AcroForm fields we set (donor's own data + year). Names are exact.
      fields: {
        year:      'form1[0].#subform[0].TextField13[0]',           // maxLen 4  (Anul)
        yearCopy:  '1.form1[0].#subform[0].TextField13[0]',         // page-2 mirror
        cnp:       'form1[0].#subform[0].TextField2[0]',            // maxLen 13 (donor CNP)
        cnpCopy:   '1.form1[0].#subform[0].TextField2[0]'           // page-2 mirror
      },
      // Real checkboxes. supportEntity is ALWAYS checked (donor redirects to a non-profit).
      checkboxes: {
        supportEntity:     'form1[0].#subform[0].#field[43]',       // "2. Sustinerea unei entitati nonprofit" -> ALWAYS
        supportEntityCopy: '1.form1[0].#subform[0].#field[11]',     // page-2 mirror
        twoYear:           'form1[0].#subform[0].#field[46]',       // "Optiune ... 2 ani" -> optional
        twoYearCopy:       '1.form1[0].#subform[0].#field[14]',
        shareConsent:      'form1[0].#subform[0].CheckBox1[0]',     // "comunicate entitatii beneficiare" -> optional
        shareConsentCopy:  '1.form1[0].#subform[0].CheckBox1[0]'
      },
      // Fields we deliberately leave blank (tax office / proxy / other option):
      leaveBlank: [
        'form1[0].#subform[0].TextField4[0]',  // Nr. inregistrare (organ fiscal)
        'form1[0].#subform[0].TextField4[1]',  // Data (organ fiscal)
        'form1[0].#subform[0].TextField2[1]',  // Cod fiscal imputernicit (sectiunea III)
        'form1[0].#subform[0].#field[40]'      // "1. Bursa privata" (not our case)
      ],
      // Constant OncoGuide entity block -- TEXT OVERLAY, page 1 (no fillable fields here).
      // src = key in window.oncoDonate.assoc; literals are quoted.
      overlay: [
        { page: 0, x: 244.8, y: PAGE_H - 444.903, size: 9, src: 'assoc.cif' },                  // Cod fiscal entitate
        { page: 0, x: 180.5, y: PAGE_H - 466.503, size: 9, src: 'assoc.name' },                 // Denumire entitate
        { page: 0, x: 102.2, y: PAGE_H - 489.543, size: 9, src: 'assoc.iban' },                 // Cont bancar (IBAN)
        { page: 0, x: 123.8, y: PAGE_H - 511.623, size: 9, text: '3,5' }                        // Procentul din impozit
      ],
      // Boxes with no field that the SUPPORTER completes by hand after printing (8.2):
      manualAfterPrint: ['Nume', 'Prenume', 'Initiala tatalui', 'Strada/Numar/Bloc/Scara/Etaj/Ap',
                         'Judet/Sector', 'Localitate', 'Cod postal', 'Semnatura contribuabil'],
      // Page 2 carries a copy; its entity block (if submitted) needs the same overlay at page-2
      // coordinates -- VERIFY in T4 whether page 2 must also carry the entity block (the CNP/year
      // mirror fields above are already handled).
      verifyTodo: ['page-2 entity-block overlay coordinates']
    },

    // ===================== FORM 177 (companies, profit-tax redirection) =====================
    f177: {
      template: 'form-177-original.pdf',
      sha256: 'f1acae4e4221fadd61831aa1d20ed5c42b869260a03ba82f73d3ffc050b46053',
      // The COMPANY fills its OWN identification (section I) -- these are real fields, set from the
      // company form state (not from association data):
      fields: {
        year:        'form1[0].#subform[0].TextField7[0]',     // maxLen 4
        cifAttr:     'form1[0].#subform[0].cif_nr[0]',         // maxLen 1 (RO attribute char)
        cif:         'form1[0].#subform[0].cif_nr[1]',         // maxLen 13 (company CIF)
        denumire:    'form1[0].#subform[0].TextField2[0]',     // company name
        judet:       'form1[0].#subform[0].TextField8[0]',
        localitate:  'form1[0].#subform[0].TextField3[0]',
        strada:      'form1[0].#subform[0].TextField3[1]',
        numar:       'form1[0].#subform[0].TextField3[2]',
        bloc:        'form1[0].#subform[0].TextField3[3]',
        scara:       'form1[0].#subform[0].TextField3[4]',
        ap:          'form1[0].#subform[0].TextField3[5]',
        codPostal:   'form1[0].#subform[0].TextField3[6]',
        telefon:     'form1[0].#subform[0].TextField3[7]',
        fax:         'form1[0].#subform[0].TextField3[8]',
        email:       'form1[0].#subform[0].TextField3[9]',
        sumaMaxima:  'form1[0].#subform[0].TextField8[4]',     // suma maxima redirectionabila
        sumaAnterior:'form1[0].#subform[0].TextField8[2]',     // redirectionat anterior
        sumaRamasa:  'form1[0].#subform[0].TextField8[3]'      // ramasa de redirectionat
      },
      checkboxes: {
        beneficiaryNonprofit: 'form1[0].#subform[0].#field[2]'  // "1. Sponsorizare catre entitati ... fara scop lucrativ" -> ALWAYS
      },
      leaveBlank: [
        'form1[0].#subform[0].CheckBox1[0]',  // Cerere rectificativa
        'form1[0].#subform[0].#field[21]',    // 2. Sponsorizare catre alti beneficiari
        'form1[0].#subform[0].CheckBox1[1]'   // rectificativa ca urmare a notificarii
      ],
      // Constant OncoGuide beneficiary block (point 1) -- TEXT OVERLAY, page 1.
      overlay: [
        { page: 0, x: 120.96, y: PAGE_H - 531.783, size: 9, src: 'assoc.name' },                 // Denumire
        { page: 0, x: 126.72, y: PAGE_H - 555.783, size: 9, src: 'assoc.cif' },                  // Cod fiscal
        { page: 0, x: 63.36,  y: PAGE_H - 578.343, size: 9, src: 'assoc.address_parts.strada' }, // Strada
        { page: 0, x: 355.20, y: PAGE_H - 578.343, size: 9, src: 'assoc.address_parts.numar' },
        { page: 0, x: 411.84, y: PAGE_H - 578.343, size: 9, src: 'assoc.address_parts.bloc' },
        { page: 0, x: 465.0,  y: PAGE_H - 578.343, size: 9, src: 'assoc.address_parts.scara' }, // empty for OncoGuide -> draws nothing; entry kept so the map matches the form
        { page: 0, x: 512.64, y: PAGE_H - 578.343, size: 9, src: 'assoc.address_parts.etaj' },
        { page: 0, x: 552.00, y: PAGE_H - 578.343, size: 9, src: 'assoc.address_parts.ap' },
        { page: 0, x: 71.04,  y: PAGE_H - 602.823, size: 9, src: 'assoc.address_parts.localitate' },
        { page: 0, x: 351.36, y: PAGE_H - 602.823, size: 9, src: 'assoc.address_parts.judet' },
        { page: 0, x: 510.24, y: PAGE_H - 602.823, size: 9, src: 'assoc.address_parts.cod_postal' },
        { page: 0, x: 250.56, y: PAGE_H - 626.616, size: 9, src: 'assoc.iban' }                  // Cont bancar (IBAN)
        // "Suma de redirectionat" (beneficiary amount) is overlaid from the company's chosen
        // amount; x verified in T6 (right side of the IBAN line, y = PAGE_H - 626.616).
      ],
      manualAfterPrint: ['Suma de redirectionat (in dreptul beneficiarului OncoGuide)',
                         'Semnatura reprezentant legal firma'],
      verifyTodo: ['beneficiary amount overlay x', 'subform[4] page-2 codes if used']
    }
  };

  if (typeof module !== 'undefined' && module.exports) module.exports = FIELD_MAPS;
  else root.ONCO_FIELD_MAPS = FIELD_MAPS;
})(typeof window !== 'undefined' ? window : globalThis);
