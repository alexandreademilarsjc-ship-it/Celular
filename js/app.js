const STORAGE_KEY = "celular-transactions";

const CATEGORIES = {
  expense: ["Alimentação", "Transporte", "Moradia", "Lazer", "Saúde", "Educação", "Compras", "Contas", "Outros"],
  income: ["Salário", "Freelance", "Investimentos", "Presente", "Outros"],
};

let transactions = loadTransactions();
let currentType = "expense";
let monthFilter = "all";

const form = document.getElementById("transactionForm");
const descriptionInput = document.getElementById("description");
const amountInput = document.getElementById("amount");
const categorySelect = document.getElementById("category");
const dateInput = document.getElementById("date");
const btnExpense = document.getElementById("btnExpense");
const btnIncome = document.getElementById("btnIncome");
const monthFilterSelect = document.getElementById("monthFilter");

function loadTransactions() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY)) || [];
  } catch {
    return [];
  }
}

function saveTransactions() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(transactions));
}

function formatCurrency(value) {
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function formatDate(isoDate) {
  const [year, month, day] = isoDate.split("-");
  return `${day}/${month}/${year}`;
}

function monthKey(isoDate) {
  return isoDate.slice(0, 7);
}

function monthLabel(key) {
  const [year, month] = key.split("-").map(Number);
  const date = new Date(year, month - 1, 1);
  const label = date.toLocaleDateString("pt-BR", { month: "long", year: "numeric" });
  return label.charAt(0).toUpperCase() + label.slice(1);
}

function setType(type) {
  currentType = type;
  btnExpense.classList.toggle("active", type === "expense");
  btnIncome.classList.toggle("active", type === "income");
  populateCategorySelect();
}

function populateCategorySelect() {
  categorySelect.innerHTML = "";
  for (const category of CATEGORIES[currentType]) {
    const option = document.createElement("option");
    option.value = category;
    option.textContent = category;
    categorySelect.appendChild(option);
  }
}

function populateMonthFilter() {
  const keys = [...new Set(transactions.map((t) => monthKey(t.date)))].sort().reverse();
  monthFilterSelect.innerHTML = '<option value="all">Todos os meses</option>';
  for (const key of keys) {
    const option = document.createElement("option");
    option.value = key;
    option.textContent = monthLabel(key);
    monthFilterSelect.appendChild(option);
  }
  monthFilterSelect.value = monthFilter;
}

function getFilteredTransactions() {
  if (monthFilter === "all") return transactions;
  return transactions.filter((t) => monthKey(t.date) === monthFilter);
}

function render() {
  populateMonthFilter();
  const filtered = getFilteredTransactions();

  const totalIncome = filtered.filter((t) => t.type === "income").reduce((sum, t) => sum + t.amount, 0);
  const totalExpense = filtered.filter((t) => t.type === "expense").reduce((sum, t) => sum + t.amount, 0);

  document.getElementById("totalIncome").textContent = formatCurrency(totalIncome);
  document.getElementById("totalExpense").textContent = formatCurrency(totalExpense);
  document.getElementById("balance").textContent = formatCurrency(totalIncome - totalExpense);

  renderBreakdown(filtered, totalExpense);
  renderList(filtered);
  renderMonthlyChart("expense");
  renderMonthlyChart("income");
}

function renderBreakdown(filtered, totalExpense) {
  const container = document.getElementById("categoryBreakdown");
  container.innerHTML = "";

  const expensesByCategory = {};
  for (const t of filtered) {
    if (t.type !== "expense") continue;
    expensesByCategory[t.category] = (expensesByCategory[t.category] || 0) + t.amount;
  }

  const entries = Object.entries(expensesByCategory).sort((a, b) => b[1] - a[1]);

  if (entries.length === 0) {
    container.innerHTML = '<p class="empty-state">Sem gastos registrados neste período.</p>';
    return;
  }

  for (const [category, amount] of entries) {
    const percent = totalExpense > 0 ? Math.round((amount / totalExpense) * 100) : 0;
    const item = document.createElement("div");
    item.className = "breakdown-item";
    item.innerHTML = `
      <div class="breakdown-item-top">
        <span>${category}</span>
        <span>${formatCurrency(amount)} (${percent}%)</span>
      </div>
      <div class="breakdown-bar-track">
        <div class="breakdown-bar-fill" style="width:${percent}%"></div>
      </div>
    `;
    container.appendChild(item);
  }
}

function renderList(filtered) {
  const list = document.getElementById("transactionList");
  const emptyState = document.getElementById("emptyState");
  list.innerHTML = "";

  const sorted = [...filtered].sort((a, b) => b.date.localeCompare(a.date) || b.id.localeCompare(a.id));

  emptyState.style.display = sorted.length === 0 ? "block" : "none";

  for (const t of sorted) {
    const li = document.createElement("li");
    li.className = "transaction-item";
    const sign = t.type === "income" ? "+" : "-";
    li.innerHTML = `
      <div class="transaction-info">
        <span class="transaction-desc">${t.description}</span>
        <span class="transaction-meta">${t.category} · ${formatDate(t.date)}</span>
      </div>
      <span class="transaction-amount ${t.type}">${sign} ${formatCurrency(t.amount)}</span>
      <button class="delete-btn" data-id="${t.id}" aria-label="Excluir">✕</button>
    `;
    list.appendChild(li);
  }

  list.querySelectorAll(".delete-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      transactions = transactions.filter((t) => t.id !== btn.dataset.id);
      saveTransactions();
      render();
    });
  });
}

const SVG_NS = "http://www.w3.org/2000/svg";
const CHART_HEIGHT = 200;
const CHART_PADDING_TOP = 20;
const CHART_PADDING_BOTTOM = 28;
const CHART_PADDING_LEFT = 56;
const CHART_PADDING_RIGHT = 12;
const CHART_BAR_WIDTH = 22;
const CHART_SLOT_WIDTH = 44;

function getMonthlyTotals(type) {
  const totals = {};
  for (const t of transactions) {
    if (t.type !== type) continue;
    const key = monthKey(t.date);
    totals[key] = (totals[key] || 0) + t.amount;
  }
  return Object.keys(totals)
    .sort()
    .map((key) => ({ key, label: monthShortLabel(key), amount: totals[key] }));
}

function monthShortLabel(key) {
  const [year, month] = key.split("-").map(Number);
  const date = new Date(year, month - 1, 1);
  const short = date.toLocaleDateString("pt-BR", { month: "short" }).replace(".", "");
  return `${short.charAt(0).toUpperCase()}${short.slice(1)}/${String(year).slice(2)}`;
}

function niceCeil(value) {
  if (value <= 0) return 100;
  const magnitude = Math.pow(10, Math.floor(Math.log10(value)));
  const normalized = value / magnitude;
  let niceNormalized;
  if (normalized <= 1) niceNormalized = 1;
  else if (normalized <= 2) niceNormalized = 2;
  else if (normalized <= 5) niceNormalized = 5;
  else niceNormalized = 10;
  return niceNormalized * magnitude;
}

function formatCompactCurrency(value) {
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
}

function roundedTopBarPath(x, y, width, height, baselineY) {
  if (height <= 0) return `M ${x} ${baselineY} L ${x + width} ${baselineY} Z`;
  const r = Math.min(4, height, width / 2);
  return [
    `M ${x} ${baselineY}`,
    `L ${x} ${y + r}`,
    `Q ${x} ${y} ${x + r} ${y}`,
    `L ${x + width - r} ${y}`,
    `Q ${x + width} ${y} ${x + width} ${y + r}`,
    `L ${x + width} ${baselineY}`,
    "Z",
  ].join(" ");
}

const CHART_LABELS = {
  expense: { title: "Gráfico de gastos por mês", idle: "Passe o mouse ou navegue pelas barras" },
  income: { title: "Gráfico de ganhos por mês", idle: "Passe o mouse ou navegue pelas barras" },
};

function updateChartReadout(type, text) {
  document.getElementById(`${type}ChartReadout`).textContent = text;
}

function renderMonthlyChart(type) {
  const data = getMonthlyTotals(type);
  const svg = document.getElementById(`${type}Chart`);
  const emptyState = document.getElementById(`${type}ChartEmptyState`);
  const tableDetails = document.getElementById(`${type}ChartTableDetails`);
  const tableBody = document.getElementById(`${type}ChartTableBody`);
  const idleText = CHART_LABELS[type].idle;

  svg.innerHTML = "";
  tableBody.innerHTML = "";
  updateChartReadout(type, idleText);

  if (data.length === 0) {
    emptyState.style.display = "block";
    svg.style.display = "none";
    tableDetails.style.display = "none";
    return;
  }

  emptyState.style.display = "none";
  svg.style.display = "block";
  tableDetails.style.display = "block";

  const plotWidth = data.length * CHART_SLOT_WIDTH;
  const width = CHART_PADDING_LEFT + plotWidth + CHART_PADDING_RIGHT;
  const plotHeight = CHART_HEIGHT - CHART_PADDING_TOP - CHART_PADDING_BOTTOM;
  const baselineY = CHART_PADDING_TOP + plotHeight;

  svg.setAttribute("viewBox", `0 0 ${width} ${CHART_HEIGHT}`);
  svg.setAttribute("width", width);
  svg.setAttribute("height", CHART_HEIGHT);
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", CHART_LABELS[type].title);

  const maxAmount = Math.max(...data.map((d) => d.amount));
  const niceMax = niceCeil(maxAmount);

  for (const tickValue of [0, niceMax / 2, niceMax]) {
    const y = baselineY - (tickValue / niceMax) * plotHeight;

    const line = document.createElementNS(SVG_NS, "line");
    line.setAttribute("x1", CHART_PADDING_LEFT);
    line.setAttribute("x2", width - CHART_PADDING_RIGHT);
    line.setAttribute("y1", y);
    line.setAttribute("y2", y);
    line.setAttribute("class", "chart-gridline");
    svg.appendChild(line);

    const label = document.createElementNS(SVG_NS, "text");
    label.setAttribute("x", CHART_PADDING_LEFT - 8);
    label.setAttribute("y", y);
    label.setAttribute("text-anchor", "end");
    label.setAttribute("dominant-baseline", "middle");
    label.setAttribute("class", "chart-axis-label");
    label.textContent = formatCompactCurrency(tickValue);
    svg.appendChild(label);
  }

  data.forEach((d, index) => {
    const slotX = CHART_PADDING_LEFT + index * CHART_SLOT_WIDTH;
    const barHeight = (d.amount / niceMax) * plotHeight;
    const barX = slotX + (CHART_SLOT_WIDTH - CHART_BAR_WIDTH) / 2;
    const barY = baselineY - barHeight;

    const bar = document.createElementNS(SVG_NS, "path");
    bar.setAttribute("d", roundedTopBarPath(barX, barY, CHART_BAR_WIDTH, barHeight, baselineY));
    bar.setAttribute("class", `chart-bar ${type}`);
    svg.appendChild(bar);

    const monthText = document.createElementNS(SVG_NS, "text");
    monthText.setAttribute("x", slotX + CHART_SLOT_WIDTH / 2);
    monthText.setAttribute("y", baselineY + 16);
    monthText.setAttribute("text-anchor", "middle");
    monthText.setAttribute("class", "chart-axis-label");
    monthText.textContent = d.label;
    svg.appendChild(monthText);

    const readoutText = `${monthLabel(d.key)}: ${formatCurrency(d.amount)}`;

    const hitArea = document.createElementNS(SVG_NS, "rect");
    hitArea.setAttribute("x", slotX);
    hitArea.setAttribute("y", CHART_PADDING_TOP);
    hitArea.setAttribute("width", CHART_SLOT_WIDTH);
    hitArea.setAttribute("height", plotHeight);
    hitArea.setAttribute("class", "chart-hit-area");
    hitArea.setAttribute("tabindex", "0");
    hitArea.setAttribute("role", "img");
    hitArea.setAttribute("aria-label", readoutText);
    hitArea.addEventListener("pointerenter", () => {
      bar.classList.add("chart-bar-active");
      updateChartReadout(type, readoutText);
    });
    hitArea.addEventListener("pointerleave", () => {
      bar.classList.remove("chart-bar-active");
      updateChartReadout(type, idleText);
    });
    hitArea.addEventListener("focus", () => {
      bar.classList.add("chart-bar-active");
      updateChartReadout(type, readoutText);
    });
    hitArea.addEventListener("blur", () => {
      bar.classList.remove("chart-bar-active");
      updateChartReadout(type, idleText);
    });
    svg.appendChild(hitArea);

    const row = document.createElement("tr");
    const monthCell = document.createElement("td");
    monthCell.textContent = monthLabel(d.key);
    const amountCell = document.createElement("td");
    amountCell.textContent = formatCurrency(d.amount);
    row.appendChild(monthCell);
    row.appendChild(amountCell);
    tableBody.appendChild(row);
  });
}

btnExpense.addEventListener("click", () => setType("expense"));
btnIncome.addEventListener("click", () => setType("income"));

monthFilterSelect.addEventListener("change", () => {
  monthFilter = monthFilterSelect.value;
  render();
});

form.addEventListener("submit", (event) => {
  event.preventDefault();

  const transaction = {
    id: crypto.randomUUID(),
    type: currentType,
    description: descriptionInput.value.trim(),
    amount: parseFloat(amountInput.value),
    category: categorySelect.value,
    date: dateInput.value,
  };

  if (!transaction.description || !transaction.amount || !transaction.date) return;

  transactions.push(transaction);
  saveTransactions();

  descriptionInput.value = "";
  amountInput.value = "";
  descriptionInput.focus();

  render();
});

dateInput.value = new Date().toISOString().slice(0, 10);
setType("expense");
render();
