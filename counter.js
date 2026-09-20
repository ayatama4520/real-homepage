(function () {
  var el = document.querySelector(".counter");
  if (!el) return;
  fetch("https://abacus.jasoncameron.dev/hit/ayatama-real-homepage/hits")
    .then(function (res) { return res.json(); })
    .then(function (data) {
      if (data && typeof data.value === "number") {
        el.textContent = String(data.value).padStart(6, "0");
      }
    })
    .catch(function () {
      /* API unreachable: leave the placeholder number shown in the page */
    });
})();
