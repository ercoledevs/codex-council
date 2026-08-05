"use strict";

const incidents = [
  { id: "INC-1042", title: "Checkout latency", status: "open", severity: 1 },
  { id: "INC-1041", title: "Delayed webhook delivery", status: "monitoring", severity: 2 },
  { id: "INC-1038", title: "Search indexing backlog", status: "resolved", severity: 3 },
  { id: "INC-1037", title: "EU image upload failures", status: "open", severity: 2 },
  { id: "INC-1035", title: "Stale billing totals", status: "monitoring", severity: 2 }
];

const query = document.querySelector("#query");
const status = document.querySelector("#status");
const form = document.querySelector(".filters");
const summary = document.querySelector("#summary");
const list = document.querySelector("#incidents");

function render() {
  const needle = query.value.trim().toLowerCase();
  const selectedStatus = status.value;
  const visible = incidents.filter((incident) => {
    const matchesQuery = `${incident.id} ${incident.title}`.toLowerCase().includes(needle);
    const matchesStatus = selectedStatus === "all" || incident.status === selectedStatus;
    return matchesQuery && matchesStatus;
  });

  summary.textContent = `${visible.length} of ${incidents.length} incidents`;
  list.replaceChildren(...visible.map((incident) => {
    const item = document.createElement("li");
    item.className = "incident";
    item.innerHTML = `
      <span class="severity">S${incident.severity}</span>
      <div>
        <h2>${incident.title}</h2>
        <p>${incident.id}</p>
      </div>
      <span class="status">${incident.status}</span>
    `;
    return item;
  }));
}

form.addEventListener("input", render);
form.addEventListener("reset", () => requestAnimationFrame(render));
render();
