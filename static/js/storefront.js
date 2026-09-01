/* Progressive enhancement for the Sondermark storefront. Everything works without JS. */
(function () {
  "use strict";
  document.documentElement.classList.add("js");
  var currency = document.querySelector("[data-price]") ? (document.querySelector("[data-price]").textContent.trim().replace(/[\d.,\s]/g, "") || "€") : "€";
  var fmt = function (n) { return currency + n.toFixed(2); };

  // Mobile navigation
  var toggle = document.querySelector("[data-nav-toggle]"), nav = document.getElementById("site-nav");
  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }

  // Catalog filter drawer (mobile)
  var filters = document.getElementById("filters");
  document.querySelectorAll("[data-filters-open]").forEach(function (b) { b.addEventListener("click", function () { filters.classList.add("open"); }); });
  document.querySelectorAll("[data-filters-close]").forEach(function (b) { b.addEventListener("click", function () { filters.classList.remove("open"); }); });
  document.querySelectorAll("[data-autosubmit]").forEach(function (el) { el.addEventListener("change", function () { el.form.submit(); }); });

  // Gallery thumbnails
  var main = document.getElementById("main-image");
  document.querySelectorAll(".thumb").forEach(function (thumb) {
    thumb.addEventListener("click", function () {
      if (!main) return;
      main.src = thumb.getAttribute("data-full");
      main.alt = thumb.getAttribute("data-alt") || main.alt;
      document.querySelectorAll(".thumb").forEach(function (t) { t.classList.remove("active"); });
      thumb.classList.add("active");
    });
  });

  // Quantity steppers
  document.querySelectorAll("[data-qty]").forEach(function (box) {
    var input = box.querySelector("input"), form = box.closest("form");
    var min = parseInt(input.min || "1", 10), max = parseInt(input.max || "99", 10);
    var change = function (delta) {
      var value = Math.min(max, Math.max(min, (parseInt(input.value, 10) || min) + delta));
      input.value = value;
      input.dispatchEvent(new Event("change", { bubbles: true }));
      if (form && form.hasAttribute("data-qty-form")) form.submit();
    };
    box.querySelector("[data-qty-minus]").addEventListener("click", function () { change(-1); });
    box.querySelector("[data-qty-plus]").addEventListener("click", function () { change(1); });
    if (form && form.hasAttribute("data-qty-form")) input.addEventListener("change", function () { form.submit(); });
  });

  // Variant picker → price, stock and button total
  var buyForm = document.querySelector("[data-add-to-cart]");
  if (buyForm) {
    var price = document.querySelector("[data-price]"), total = buyForm.querySelector("[data-total]"),
        stockLine = buyForm.querySelector("[data-stock-line]"), qty = buyForm.querySelector("input[name=quantity]");
    var update = function () {
      var chosen = buyForm.querySelector("input[name=variant]:checked") || buyForm.querySelector("input[name=variant][type=hidden]");
      if (!chosen) return;
      var unit = parseFloat(chosen.getAttribute("data-price")), stock = parseInt(chosen.getAttribute("data-stock"), 10),
          quantity = Math.max(1, parseInt(qty.value, 10) || 1);
      if (price) price.textContent = fmt(unit);
      if (total) total.textContent = fmt(unit * quantity);
      qty.max = Math.max(1, Math.min(99, stock));
      if (quantity > stock) { qty.value = stock; if (total) total.textContent = fmt(unit * stock); }
      if (stockLine) {
        var dot = stockLine.querySelector(".dot");
        stockLine.lastChild.textContent = stock <= 0 ? "Sold out in this option" : (stock <= 12 ? "In stock · only " + stock + " left · ships within 48 hours" : "In stock · ships within 48 hours");
        if (dot) dot.className = "dot " + (stock <= 0 ? "out" : stock <= 12 ? "low" : "in");
      }
    };
    buyForm.querySelectorAll("input[name=variant]").forEach(function (r) { r.addEventListener("change", update); });
    qty.addEventListener("change", update);
    qty.addEventListener("input", update);
    update();
  }
})();
