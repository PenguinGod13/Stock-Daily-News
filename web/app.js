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

async function loadRows() {
  const { data, error } = await supabaseClient
    .from("watchlist")
    .select("*")
    .order("ticker");

  const errorEl = document.getElementById("app-error");
  if (error) {
    errorEl.textContent = error.message;
    return;
  }
  errorEl.textContent = "";

  const tbody = document.getElementById("rows");
  tbody.innerHTML = "";
  for (const row of data) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${row.ticker}</td>
      <td>${row.owned ? "yes" : "no"}</td>
      <td>${row.shares ?? ""}</td>
      <td>${row.cost_basis ?? ""}</td>
      <td>${row.notes ?? ""}</td>
      <td><button data-id="${row.id}" class="delete-btn">Delete</button></td>
    `;
    tbody.appendChild(tr);
  }

  for (const btn of document.querySelectorAll(".delete-btn")) {
    btn.addEventListener("click", () => deleteRow(btn.dataset.id));
  }
}

async function addRow() {
  const ticker = document.getElementById("new-ticker").value.trim().toUpperCase();
  const owned = document.getElementById("new-owned").checked;
  const sharesRaw = document.getElementById("new-shares").value;
  const costBasisRaw = document.getElementById("new-cost-basis").value;
  const notes = document.getElementById("new-notes").value.trim() || null;

  if (!ticker) {
    document.getElementById("app-error").textContent = "Ticker is required.";
    return;
  }

  const { error } = await supabaseClient.from("watchlist").insert({
    ticker,
    owned,
    shares: sharesRaw ? Number(sharesRaw) : null,
    cost_basis: costBasisRaw ? Number(costBasisRaw) : null,
    notes,
  });

  const errorEl = document.getElementById("app-error");
  if (error) {
    errorEl.textContent = error.message;
    return;
  }
  errorEl.textContent = "";
  document.getElementById("new-ticker").value = "";
  document.getElementById("new-owned").checked = false;
  document.getElementById("new-shares").value = "";
  document.getElementById("new-cost-basis").value = "";
  document.getElementById("new-notes").value = "";
  await loadRows();
}

async function deleteRow(id) {
  const { error } = await supabaseClient.from("watchlist").delete().eq("id", id);
  if (error) {
    document.getElementById("app-error").textContent = error.message;
    return;
  }
  await loadRows();
}

document.getElementById("connect-btn").addEventListener("click", async () => {
  const url = document.getElementById("supabase-url").value.trim();
  const anonKey = document.getElementById("supabase-anon-key").value.trim();
  const secret = document.getElementById("shared-secret").value.trim();

  if (!url || !anonKey || !secret) {
    document.getElementById("setup-error").textContent = "All fields are required.";
    return;
  }

  await connect(url, anonKey, secret);
});

document.getElementById("add-btn").addEventListener("click", addRow);

document.getElementById("disconnect-btn").addEventListener("click", disconnect);

(async function autoConnect() {
  // A one-time setup link (#url=...&anonKey=...&secret=...) takes priority
  // over anything already saved, so sharing a fresh link always works even
  // if this browser previously connected to something else. This uses the
  // URL fragment (#), not the query string (?): fragments are never sent
  // to any server, are excluded from Referer headers, and never appear in
  // server/CDN access logs — unlike query params, which are. The fragment
  // is also stripped from the address bar immediately after reading it so
  // it doesn't linger in browser history either.
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
