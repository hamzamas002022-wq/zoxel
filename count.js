(function () {
  var box = document.querySelector("[data-until]");
  if (!box) return;

  var end = new Date(box.getAttribute("data-until")).getTime();
  var dEl = box.querySelector("[data-d]");
  var hEl = box.querySelector("[data-h]");
  var mEl = box.querySelector("[data-m]");
  var sEl = box.querySelector("[data-s]");
  var label = box.querySelector(".count-label");

  function pad(n) {
    return n < 10 ? "0" + n : String(n);
  }

  function tick() {
    var left = end - Date.now();
    if (left < 0) left = 0;

    var total = Math.floor(left / 1000);
    var d = Math.floor(total / 86400);
    var h = Math.floor((total % 86400) / 3600);
    var m = Math.floor((total % 3600) / 60);
    var s = total % 60;

    dEl.textContent = String(d);
    hEl.textContent = pad(h);
    mEl.textContent = pad(m);
    sEl.textContent = pad(s);

    if (left === 0 && label) {
      label.textContent = "29 September. that's the date.";
    }
  }

  tick();
  setInterval(tick, 1000);
})();
