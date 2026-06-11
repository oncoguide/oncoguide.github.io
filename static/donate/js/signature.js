/* signature.js -- DONATIONS.md T4. Canvas signature capture for the sponsorship contract ONLY
 * (never on ANAF forms, D3). Pointer events cover mouse, touch, and pen. Output: PNG data URL
 * embedded into the contract's sponsor_semnatura field via pdf-lib setImage (donate-common.js).
 * The canvas element should set CSS `touch-action: none` so drawing does not scroll the page.
 */
(function (root) {
  'use strict';

  function createSignaturePad(canvas) {
    var ctx = canvas.getContext('2d');
    var drawing = false, has = false, last = null;

    function point(e) {
      var r = canvas.getBoundingClientRect();
      return {
        x: (e.clientX - r.left) * (canvas.width / r.width),
        y: (e.clientY - r.top) * (canvas.height / r.height)
      };
    }
    function down(e) { e.preventDefault(); drawing = true; last = point(e); if (canvas.setPointerCapture) try { canvas.setPointerCapture(e.pointerId); } catch (x) {} }
    function move(e) {
      if (!drawing) return;
      e.preventDefault();
      var p = point(e);
      ctx.strokeStyle = '#111'; ctx.lineWidth = 2; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
      ctx.beginPath(); ctx.moveTo(last.x, last.y); ctx.lineTo(p.x, p.y); ctx.stroke();
      last = p; has = true;
    }
    function up() { drawing = false; }

    canvas.addEventListener('pointerdown', down);
    canvas.addEventListener('pointermove', move);
    canvas.addEventListener('pointerup', up);
    canvas.addEventListener('pointercancel', up);

    return {
      clear: function () { ctx.clearRect(0, 0, canvas.width, canvas.height); has = false; },
      isEmpty: function () { return !has; },
      // typed-name fallback for users who cannot draw (accessibility)
      fromTypedName: function (name) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = '#111';
        ctx.font = Math.round(canvas.height * 0.42) + 'px Georgia, "Times New Roman", serif';
        ctx.textBaseline = 'middle';
        ctx.fillText(String(name || ''), 14, canvas.height / 2);
        has = !!(name && String(name).trim());
      },
      toPngDataUrl: function () { return canvas.toDataURL('image/png'); }
    };
  }

  root.oncoSignature = { createSignaturePad: createSignaturePad };
  if (typeof module !== 'undefined' && module.exports) module.exports = root.oncoSignature;
})(typeof window !== 'undefined' ? window : globalThis);
