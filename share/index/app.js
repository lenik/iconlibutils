(() => {
  const cfg = window.ICONLIB_PREVIEW || {};
  const grid = document.getElementById("grid");
  const q = document.getElementById("q");
  const size = document.getElementById("size");
  const status = document.getElementById("status");
  const shown = document.getElementById("shown");
  const dlg = document.getElementById("dlg");
  const dlgImg = document.getElementById("dlg-img");
  const dlgName = document.getElementById("dlg-name");
  const dlgPath = document.getElementById("dlg-path");
  const copyName = document.getElementById("copy-name");
  const copyPath = document.getElementById("copy-path");

  let icons = [];
  let active = null;

  function setStatus(msg) {
    if (!msg) {
      status.hidden = true;
      status.textContent = "";
      return;
    }
    status.hidden = false;
    status.textContent = msg;
  }

  function render(list) {
    const frag = document.createDocumentFragment();
    for (const icon of list) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "card";
      btn.title = icon.name;
      const img = document.createElement("img");
      img.loading = "lazy";
      img.decoding = "async";
      img.alt = "";
      img.src = icon.href;
      const label = document.createElement("span");
      label.textContent = icon.name;
      btn.append(img, label);
      btn.addEventListener("click", () => openDlg(icon));
      frag.append(btn);
    }
    grid.replaceChildren(frag);
    shown.textContent = `${list.length} shown`;
  }

  function filter() {
    const needle = (q.value || "").trim().toLowerCase();
    if (!needle) {
      render(icons);
      return;
    }
    render(icons.filter((i) => i.name.toLowerCase().includes(needle) || i.path.toLowerCase().includes(needle)));
  }

  function openDlg(icon) {
    active = icon;
    dlgImg.src = icon.href;
    dlgName.textContent = icon.name;
    dlgPath.textContent = icon.path;
    dlg.showModal();
  }

  async function copyText(text) {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const ta = document.createElement("textarea");
      ta.value = text;
      document.body.append(ta);
      ta.select();
      document.execCommand("copy");
      ta.remove();
    }
  }

  size.addEventListener("input", () => {
    grid.style.setProperty("--icon-size", `${size.value}px`);
  });
  q.addEventListener("input", filter);
  copyName.addEventListener("click", () => active && copyText(active.name));
  copyPath.addEventListener("click", () => active && copyText(active.path));

  setStatus("Loading icon manifest…");
  fetch(cfg.manifest || "icons.json")
    .then((r) => {
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.json();
    })
    .then((data) => {
      icons = Array.isArray(data) ? data : (data.icons || []);
      document.getElementById("count").textContent = String(icons.length);
      setStatus("");
      filter();
    })
    .catch((err) => {
      setStatus(`Failed to load icons.json: ${err.message}`);
    });
})();
