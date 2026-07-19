const STORAGE_KEYS = {
  url: "watchlist_supabase_url",
  anonKey: "watchlist_supabase_anon_key",
  secret: "watchlist_shared_secret",
};

let supabaseClient = null;
let sharedSecret = null;

function headers() {
  return { "x-watchlist-secret": sharedSecret };
}

function showApp() {
  document.getElementById("setup").classList.remove("visible");
  document.getElementById("app").classList.add("visible");
}

function showSetup() {
  document.getElementById("app").classList.remove("visible");
  document.getElementById("setup").classList.add("visible");
}

function setError(id, msg) {
  const el = document.getElementById(id);
  if (el) el.textContent = msg || "";
}

function setStatus(msg) {
  const el = document.getElementById("app-status");
  if (el) {
    el.textContent = msg || "";
    if (msg) setTimeout(() => { el.textContent = ""; }, 2500);
  }
}

async function connect(url, anonKey, secret) {
  sharedSecret = secret;
  supabaseClient = supabase.createClient(url, anonKey, {
    global: { headers: headers() },
  });

  localStorage.setItem(STORAGE_KEYS.url, url);
  localStorage.setItem(STORAGE_KEYS.anonKey, anonKey);
  localStorage.setItem(STORAGE_KEYS.secret, secret);

  showApp();
  await loadRows();
}

function disconnect() {
  localStorage.removeItem(STORAGE_KEYS.url);
  localStorage.removeItem(STORAGE_KEYS.anonKey);
  localStorage.removeItem(STORAGE_KEYS.secret);
  supabaseClient = null;
  sharedSecret = null;
  showSetup();
}

function escapeHtml(str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

async function loadRows() {
  const { data, error } = await supabaseClient
    .from("watchlist")
    .select("*")
    .order("ticker");

  const container = document.getElementById("watchlist-content");

  if (error) {
    setError("app-error", error.message);
    return;
  }
  setError("app-error", "");

  if (!data || data.length === 0) {
    container.innerHTML = '<div class="empty-state">No tickers yet — add one below.</div>';
    return;
  }

  const rows = data.map(row => {
    const badge = row.owned
      ? '<span class="badge badge-owned">Owned</span>'
      : '<span class="badge badge-watching">Watching</span>';

    const position = row.owned && row.shares != null
      ? `${escapeHtml(row.shares)} @ $${Number(row.cost_basis ?? 0).toFixed(2)}`
      : row.owned ? "Owned" : "—";

    return `
      <tr>
        <td style="font-weight:600;">${escapeHtml(row.ticker)}</td>
        <td>${badge}</td>
        <td style="color:#6b7280;">${escapeHtml(position)}</td>
        <td style="color:#6b7280;max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${escapeHtml(row.notes ?? "")}</td>
        <td style="text-align:right;">
          <button class="btn-delete" data-id="${escapeHtml(row.id)}" title="Remove">&#x2715;</button>
        </td>
      </tr>`;
  }).join("");

  container.innerHTML = `
    <table class="watchlist-table">
      <thead>
        <tr>
          <th>Ticker</th><th>Status</th><th>Position</th><th>Notes</th><th></th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>`;

  container.querySelectorAll(".btn-delete").forEach(btn => {
    btn.addEventListener("click", () => deleteRow(btn.dataset.id));
  });
}

async function addRow() {
  const ticker = document.getElementById("new-ticker").value.trim().toUpperCase();
  const owned = document.getElementById("new-owned").checked;
  const sharesRaw = document.getElementById("new-shares").value;
  const costBasisRaw = document.getElementById("new-cost-basis").value;
  const notes = document.getElementById("new-notes").value.trim() || null;

  if (!ticker) {
    setError("app-error", "Ticker symbol is required.");
    document.getElementById("new-ticker").focus();
    return;
  }

  const addBtn = document.getElementById("add-btn");
  addBtn.disabled = true;
  addBtn.textContent = "Adding…";

  const { error } = await supabaseClient.from("watchlist").insert({
    ticker,
    owned,
    shares: sharesRaw ? Number(sharesRaw) : null,
    cost_basis: costBasisRaw ? Number(costBasisRaw) : null,
    notes,
  });

  addBtn.disabled = false;
  addBtn.textContent = "Add to watchlist";

  if (error) {
    setError("app-error", error.message);
    return;
  }

  setError("app-error", "");
  setStatus(`${ticker} added.`);

  // Reset form to clean "Watching" state
  document.getElementById("new-ticker").value = "";
  document.getElementById("new-notes").value = "";
  document.getElementById("new-shares").value = "";
  document.getElementById("new-cost-basis").value = "";
  document.getElementById("btn-watching").classList.add("active");
  document.getElementById("btn-owned").classList.remove("active");
  document.getElementById("new-owned").checked = false;
  document.getElementById("position-fields").classList.remove("visible");

  await loadRows();
  document.getElementById("new-ticker").focus();
}

async function deleteRow(id) {
  const { error } = await supabaseClient.from("watchlist").delete().eq("id", id);
  if (error) {
    setError("app-error", error.message);
    return;
  }
  await loadRows();
}

// Segmented "Watching / I own it" control
document.getElementById("btn-watching").addEventListener("click", function () {
  document.getElementById("btn-watching").classList.add("active");
  document.getElementById("btn-owned").classList.remove("active");
  document.getElementById("new-owned").checked = false;
  document.getElementById("position-fields").classList.remove("visible");
});

document.getElementById("btn-owned").addEventListener("click", function () {
  document.getElementById("btn-owned").classList.add("active");
  document.getElementById("btn-watching").classList.remove("active");
  document.getElementById("new-owned").checked = true;
  document.getElementById("position-fields").classList.add("visible");
  document.getElementById("new-shares").focus();
});

// Submit on Enter in ticker field
document.getElementById("new-ticker").addEventListener("keydown", function (e) {
  if (e.key === "Enter") addRow();
});

document.getElementById("connect-btn").addEventListener("click", async () => {
  const url = document.getElementById("supabase-url").value.trim();
  const anonKey = document.getElementById("supabase-anon-key").value.trim();
  const secret = document.getElementById("shared-secret").value.trim();

  if (!url || !anonKey || !secret) {
    setError("setup-error", "All fields are required.");
    return;
  }

  setError("setup-error", "");
  document.getElementById("connect-btn").textContent = "Connecting…";
  document.getElementById("connect-btn").disabled = true;

  await connect(url, anonKey, secret);

  document.getElementById("connect-btn").textContent = "Connect";
  document.getElementById("connect-btn").disabled = false;
});

document.getElementById("add-btn").addEventListener("click", addRow);
document.getElementById("disconnect-btn").addEventListener("click", disconnect);

(async function autoConnect() {
  // A one-time setup link (#url=...&anonKey=...&secret=...) takes priority.
  // Uses URL fragment (#), not query string (?): fragments are never sent to
  // any server, excluded from Referer headers, and never appear in server logs.
  const params = new URLSearchParams(window.location.hash.slice(1));
  const linkUrl = params.get("url");
  const linkAnonKey = params.get("anonKey");
  const linkSecret = params.get("secret");

  if (linkUrl && linkAnonKey && linkSecret) {
    window.history.replaceState({}, document.title, window.location.pathname);
    document.getElementById("supabase-url").value = linkUrl;
    document.getElementById("supabase-anon-key").value = linkAnonKey;
    document.getElementById("shared-secret").value = linkSecret;
    await connect(linkUrl, linkAnonKey, linkSecret);
    return;
  }

  const url = localStorage.getItem(STORAGE_KEYS.url);
  const anonKey = localStorage.getItem(STORAGE_KEYS.anonKey);
  const secret = localStorage.getItem(STORAGE_KEYS.secret);

  if (url && anonKey && secret) {
    document.getElementById("supabase-url").value = url;
    document.getElementById("supabase-anon-key").value = anonKey;
    document.getElementById("shared-secret").value = secret;
    await connect(url, anonKey, secret);
  }
})();
