const $ = id => document.getElementById(id);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
let current = null;          // nutrition result being shown
let dishes = [];

fetch("/api/dishes").then(r => r.json()).then(list => {
  dishes = list;
  $("dish-list").innerHTML = list.map(d => `<span class="chip ${d.status === "ok" ? "" : "dim"}" title="${d.status === "ok" ? "" : "No nutrition data"}">${esc(d.name)}</span>`).join("");
  $("pick").innerHTML = `<option value="">Other dish…</option>` + list.map(d => `<option value="${d.dish}">${esc(d.name)}</option>`).join("");
});

// ---------- upload: click, camera or drag and drop ----------
$("file").onchange = e => e.target.files[0] && upload(e.target.files[0]);
const drop = $("drop");
["dragenter", "dragover"].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.add("over"); }));
["dragleave", "drop"].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.remove("over"); }));
drop.addEventListener("drop", e => e.dataTransfer.files[0] && upload(e.dataTransfer.files[0]));

async function upload(file) {
  $("preview").src = URL.createObjectURL(file);
  $("preview").classList.remove("hidden"); $("placeholder").classList.add("hidden");
  $("empty").textContent = "Looking at your photo…"; $("empty").classList.remove("hidden"); $("body").classList.add("hidden");
  const form = new FormData(); form.append("image", file);
  try {
    const res = await fetch("/api/analyze", { method: "POST", body: form });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Something went wrong");
    showPrediction(data);
  } catch (err) { $("empty").textContent = err.message; }
}

function showPrediction(data) {
  const best = data.predictions[0];
  $("empty").classList.add("hidden"); $("body").classList.remove("hidden");
  $("conf").textContent = Math.round(best.confidence * 100) + "% sure";
  $("conf").classList.toggle("low", data.low_confidence);
  $("low").classList.toggle("hidden", !data.low_confidence);
  $("alts").innerHTML = data.predictions.map((p, i) =>
    `<button type="button" class="chip ${i === 0 ? "on" : ""}" data-d="${p.dish}">${esc(p.name)} · ${Math.round(p.confidence * 100)}%</button>`).join("");
  $("alts").querySelectorAll("button").forEach(b => b.onclick = () => choose(b.dataset.d));
  showNutrition(data.nutrition);
}

async function choose(dish, grams) {
  if (!dish) return;
  $("alts").querySelectorAll("button").forEach(b => b.classList.toggle("on", b.dataset.d === dish));
  const q = grams ? `?grams=${grams}` : "";
  const res = await fetch(`/api/nutrition/${dish}${q}`);
  showNutrition(await res.json());
}
$("pick").onchange = e => { choose(e.target.value); e.target.value = ""; };

// ---------- nutrition ----------
const fmt = (v, unit) => v == null ? "–" : (v >= 100 ? Math.round(v) : v >= 10 ? v.toFixed(1) : v.toFixed(2)) + " " + unit;

function showNutrition(n) {
  current = n;
  $("dish-name").textContent = n.name;
  const ok = n.status === "ok";
  $("nutri").classList.toggle("hidden", !ok);
  $("no-data").classList.toggle("hidden", ok);
  if (!ok) { $("no-data").textContent = n.note; return; }

  $("grams").value = n.grams;
  $("serving-note").textContent = `Standard serving: 1 ${n.serving.unit} ≈ ${n.serving.grams} g`;
  const v = Object.fromEntries(n.nutrients.map(x => [x.key, x]));
  const macro = (key, label, cls = "") => `<div class="macro ${cls}"><span>${label}</span><b>${fmt(v[key].amount, `<small>${v[key].unit}</small>`)}</b></div>`;
  $("macros").innerHTML = macro("energy_kcal", "Energy", "energy") + macro("protein_g", "Protein") + macro("carb_g", "Carbs") +
    macro("fat_g", "Fat") + macro("fibre_g", "Fibre") + macro("freesugar_g", "Free sugar");

  // where the calories come from: protein and carbs 4 kcal/g, fat 9 kcal/g
  const kcal = { Protein: 4 * (v.protein_g.amount || 0), Carbs: 4 * (v.carb_g.amount || 0), Fat: 9 * (v.fat_g.amount || 0) };
  const total = Object.values(kcal).reduce((a, b) => a + b, 0) || 1;
  const colors = { Protein: "var(--protein)", Carbs: "var(--carb)", Fat: "var(--fat)" };
  $("split-bar").innerHTML = Object.entries(kcal).map(([k, x]) => `<div style="width:${x / total * 100}%;background:${colors[k]}"></div>`).join("");
  $("split-legend").innerHTML = Object.entries(kcal).map(([k, x]) => `<span><i style="background:${colors[k]}"></i>${k} ${Math.round(x / total * 100)}% of calories</span>`).join("");

  const rows = group => n.nutrients.filter(x => x.group === group).map(x => `<tr><td>${esc(x.label)}</td><td>${fmt(x.amount, x.unit)}</td></tr>`).join("");
  $("minerals").innerHTML = rows("mineral");
  $("vitamins").innerHTML = rows("vitamin");
  $("source").textContent = `Source: ${n.source}. Recipe used: ${n.indb_recipes.join(", ")}. Values are estimates for a standard recipe.`;
}

const setGrams = g => current && current.status === "ok" && choose(current.dish, Math.max(10, Math.min(2000, Math.round(g))));
$("grams").onchange = e => setGrams(+e.target.value);
$("minus").onclick = () => setGrams(+$("grams").value - (current?.serving.grams || 50) / 2);
$("plus").onclick = () => setGrams(+$("grams").value + (current?.serving.grams || 50) / 2);

// ---------- model scores ----------
fetch("/api/model").then(r => r.json()).then(m => {
  $("scores").innerHTML = `<tr><th>Model (test set, ${m.test_size} photos)</th><th>Accuracy</th><th>Top-3 accuracy</th><th>Macro F1</th></tr>` +
    Object.entries(m.test_results).map(([name, s]) => `<tr class="${name === m.chosen_model ? "best" : ""}"><td>${esc(name)}${name === m.chosen_model ? " · used here" : ""}</td>
      <td>${(s.accuracy * 100).toFixed(1)}%</td><td>${(s.top3_accuracy * 100).toFixed(1)}%</td><td>${s.macro_f1.toFixed(3)}</td></tr>`).join("");
}).catch(() => {});
