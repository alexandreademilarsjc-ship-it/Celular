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
