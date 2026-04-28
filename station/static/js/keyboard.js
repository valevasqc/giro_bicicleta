(function () {
  'use strict';

  function init() {
    if (!window.SimpleKeyboard) return;

    var canvas = document.getElementById('kv2');
    if (!canvas) return;

    /* Only activate if this page has text / password inputs */
    if (!canvas.querySelector(
          'input[type="text"], input[type="password"], input:not([type])')) return;

    /* ── Build overlay DOM ──────────────────────────────────────────────── */
    var wrap  = document.createElement('div');
    wrap.id   = 'vk-wrap';
    var inner = document.createElement('div');
    inner.id        = 'vk-inner';
    inner.className = 'vk-inner';
    wrap.appendChild(inner);
    canvas.appendChild(wrap);

    /* ── State ──────────────────────────────────────────────────────────── */
    var activeInput = null;
    var layoutName  = 'default';

    /* ── Keyboard instance ──────────────────────────────────────────────── */
    var Keyboard = window.SimpleKeyboard.default || window.SimpleKeyboard;
    var kb = new Keyboard(inner, {
      preventMouseDownDefault: true,
      onKeyPress: handleKey,
      layout: {
        default: [
          'q w e r t y u i o p',
          'a s d f g h j k l',
          '{shift} z x c v b n m {bksp}',
          '{numbers} {space} {enter}'
        ],
        shift: [
          'Q W E R T Y U I O P',
          'A S D F G H J K L',
          '{shift} Z X C V B N M {bksp}',
          '{numbers} {space} {enter}'
        ],
        numbers: [
          '1 2 3 4 5 6 7 8 9 0',
          '- / : ; ( ) & @ . ,',
          '% * " \' ! ? _ {bksp}',
          '{abc} {space} {enter}'
        ]
      },
      display: {
        '{bksp}':    '⌫',
        '{enter}':   '↵',
        '{shift}':   '⇧',
        '{space}':   'Espacio',
        '{numbers}': '123',
        '{abc}':     'abc'
      },
      layoutName: 'default',
      theme: 'hg-theme-default'
    });

    /* ── Visibility ─────────────────────────────────────────────────────── */
    function showKeyboard(input) {
      activeInput = input;
      wrap.classList.add('vk-visible');
      canvas.classList.add('vk-open');
      /* Scroll focused field above the keyboard after CSS reflow */
      setTimeout(function () {
        input.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      }, 80);
    }

    function hideKeyboard() {
      wrap.classList.remove('vk-visible');
      canvas.classList.remove('vk-open');
      activeInput = null;
    }

    function setLayout(name) {
      layoutName = name;
      kb.setOptions({ layoutName: name });
      var shiftBtn = wrap.querySelector('[data-skbtn="{shift}"]');
      if (shiftBtn) shiftBtn.classList.toggle('vk-shift-active', name === 'shift');
    }

    /* Prevent keyboard taps from stealing focus away from the active input */
    wrap.addEventListener('mousedown', function (e) { e.preventDefault(); });

    /* ── Focus / blur ───────────────────────────────────────────────────── */
    canvas.addEventListener('focusin', function (e) {
      var t = e.target;
      if (t.tagName !== 'INPUT') return;
      var type = (t.getAttribute('type') || 'text').toLowerCase();
      if (type !== 'text' && type !== 'password') return;
      showKeyboard(t);
    });

    canvas.addEventListener('focusout', function () {
      setTimeout(function () {
        var ae = document.activeElement;
        if (!wrap.contains(ae) && (!ae || ae.tagName !== 'INPUT')) {
          hideKeyboard();
        }
      }, 150);
    });

    /* Tap/click outside input + keyboard → hide.
       Uses a flag instead of wrap.contains(e.target) because layout-switching
       keys (numbers/shift/abc) re-render the keyboard DOM during their own
       pointerdown handler, detaching e.target before this check runs. */
    var pointerDownInWrap = false;
    wrap.addEventListener('pointerdown', function () { pointerDownInWrap = true; });

    canvas.addEventListener('pointerdown', function (e) {
      var wasInWrap = pointerDownInWrap;
      pointerDownInWrap = false;
      if (!wasInWrap && e.target.tagName !== 'INPUT') {
        hideKeyboard();
      }
    });

    /* ── Key handler ────────────────────────────────────────────────────── */
    function handleKey(button) {
      if (!activeInput) return;

      switch (button) {

        case '{shift}':
          setLayout(layoutName === 'shift' ? 'default' : 'shift');
          return;

        case '{numbers}':
          setLayout('numbers');
          return;

        case '{abc}':
          setLayout('default');
          return;

        case '{enter}':
          hideKeyboard();
          var form = activeInput.closest('form');
          if (form) {
            if (form.requestSubmit) { form.requestSubmit(); }
            else                    { form.submit(); }
          }
          return;

        case '{bksp}':
          deletePrev();
          return;

        case '{space}':
          insertAt(activeInput, ' ');
          return;

        default:
          var ch = button;
          /* Honour autocapitalize="characters" (e.g. the top-up code input) */
          if ((activeInput.getAttribute('autocapitalize') || '') === 'characters') {
            ch = ch.toUpperCase();
          }
          insertAt(activeInput, ch);
          /* One-shot shift: revert after typing one character */
          if (layoutName === 'shift') setLayout('default');
      }
    }

    /* ── Text helpers ───────────────────────────────────────────────────── */
    function deletePrev() {
      var s  = activeInput.selectionStart;
      var e  = activeInput.selectionEnd;
      var v  = activeInput.value;
      var nv, np;
      if (s !== e)  { nv = v.slice(0, s) + v.slice(e);   np = s;     }
      else if (s>0) { nv = v.slice(0, s-1) + v.slice(s); np = s - 1; }
      else          { return; }
      writeValue(activeInput, nv, np);
    }

    function insertAt(input, ch) {
      var s  = input.selectionStart;
      var e  = input.selectionEnd;
      var nv = input.value.slice(0, s) + ch + input.value.slice(e);
      writeValue(input, nv, s + ch.length);
    }

    /* Uses the native setter so React-style frameworks pick up the change */
    function writeValue(input, value, cursor) {
      var desc = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value');
      if (desc && desc.set) { desc.set.call(input, value); }
      else                  { input.value = value; }
      input.dispatchEvent(new Event('input',  { bubbles: true }));
      input.dispatchEvent(new Event('change', { bubbles: true }));
      if (cursor != null) input.setSelectionRange(cursor, cursor);
    }
  }

  /* Run after DOM is ready, whether script is in <head> or end of <body> */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
