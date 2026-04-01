const reloadBtn = document.getElementById("reloadBtn");
const filterInput = document.getElementById("filterInput");
const resultSection = document.getElementById("resultSection");
const hostsList = document.getElementById("hostsList");
const message = document.getElementById("message");

let allHosts = [];

reloadBtn.addEventListener("click", loadHosts);
filterInput.addEventListener("input", applyFilter);
loadHosts();

async function loadHosts() {
  hostsList.innerHTML = "";
  resultSection.classList.add("hidden");
  message.textContent = "Загружаю данные...";

  try {
    const response = await fetch("data/hosts.json", { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const payload = await response.json();
    const hosts = Array.isArray(payload.hosts) ? payload.hosts : [];

    if (hosts.length === 0) {
      message.textContent = "Хосты не найдены. Проверьте путь к конфигам Nginx.";
      return;
    }

    allHosts = hosts;
    applyFilter();

    const hostsWithUpstreams = hosts.filter((host) => host.upstreams.length > 0).length;
    const sourceText = Array.isArray(payload.configDirs)
      ? payload.configDirs.join(", ")
      : "не указано";
    const filesCount = Number.isInteger(payload.configFilesCount) ? payload.configFilesCount : "?";
    message.textContent = `Хостов: ${hosts.length}, с upstream: ${hostsWithUpstreams}, файлов: ${filesCount}. Источник: ${sourceText}`;
  } catch (error) {
    message.textContent = `Ошибка загрузки: ${error.message}. Проверьте, что data/hosts.json существует на сервере и скрипт из /opt его обновляет`;
  }
}

function applyFilter() {
  const q = (filterInput.value || "").trim().toLowerCase();
  hostsList.innerHTML = "";

  const filtered = !q
    ? allHosts
    : allHosts.filter((host) => {
        if (host.host.toLowerCase().includes(q)) return true;
        if ((host.confFile || "").toLowerCase().includes(q)) return true;
        for (const n of host.hostNames || []) {
          if (n.toLowerCase().includes(q)) return true;
        }
        for (const up of host.upstreams) {
          if (up.name.toLowerCase().includes(q)) return true;
          if (up.source.toLowerCase().includes(q)) return true;
          for (const s of up.servers) {
            if (s.toLowerCase().includes(q)) return true;
          }
        }
        return false;
      });

  if (filtered.length === 0) {
    resultSection.classList.add("hidden");
    if (q) {
      message.textContent = "Ничего не найдено по фильтру.";
    }
    return;
  }

  for (const host of filtered) {
    hostsList.appendChild(renderHostItem(host));
  }
  resultSection.classList.remove("hidden");
}

function renderHostItem(host) {
  const details = document.createElement("details");
  details.className = "host-item";

  const summary = document.createElement("summary");
  summary.className = "host-header";
  const countText = host.upstreams.length > 0 ? `upstream: ${host.upstreams.length}` : "upstream: нет";
  summary.textContent = `${host.host} (${countText})`;
  details.appendChild(summary);

  const body = document.createElement("div");
  body.className = "host-body";
  const confFile = host.confFile ? escapeHtml(host.confFile) : "unknown";
  const blockIndex = Number.isInteger(host.serverBlockIndex) ? host.serverBlockIndex : "-";
  body.innerHTML = `<p class="meta">файл: ${confFile}, server-блок: #${blockIndex}</p>`;

  if (host.upstreams.length === 0) {
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = "Для этого хоста не найдено активных proxy_pass/upstream.";
    body.appendChild(empty);
    details.appendChild(body);
    return details;
  }

  const list = document.createElement("ul");
  list.className = "upstream-list";

  for (const upstream of host.upstreams) {
    const li = document.createElement("li");
    li.innerHTML = `
      <span class="upstream-name">${escapeHtml(upstream.name)}</span>
      <span class="upstream-source">(${escapeHtml(upstream.source)})</span>
    `;

    if (upstream.servers.length > 0) {
      const backends = document.createElement("ul");
      backends.className = "backend-list";
      for (const backend of upstream.servers) {
        const backendItem = document.createElement("li");
        backendItem.textContent = backend;
        backends.appendChild(backendItem);
      }
      li.appendChild(backends);
    }

    list.appendChild(li);
  }

  body.appendChild(list);
  details.appendChild(body);
  return details;
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}
