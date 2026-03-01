// ---------- Theme Toggle ----------
const toggleBtn = document.getElementById("themeToggle");

function setTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem("theme", theme);
  toggleBtn.textContent = theme === "dark" ? "☀️ Light" : "🌙 Dark";
}

const savedTheme = localStorage.getItem("theme") || "light";
setTheme(savedTheme);

toggleBtn.addEventListener("click", () => {
  const current = document.documentElement.getAttribute("data-theme") || "light";
  setTheme(current === "dark" ? "light" : "dark");
});

// ---------- Charts ----------
const categoryData = JSON.parse(document.getElementById("categoryData").textContent || "{}");
const dmData = JSON.parse(document.getElementById("dmData").textContent || "{}");

const pieEmpty = document.getElementById("pieEmpty");
const barEmpty = document.getElementById("barEmpty");

// Make sure IDs match index.html
const pieCanvas = document.getElementById("expenseChart");
const barCanvas = document.getElementById("dmChart");

// If no data, show a friendly message
const hasPieData = Object.keys(categoryData).length > 0 && Object.values(categoryData).some(v => Number(v) > 0);
const hasBarData = Object.keys(dmData).length > 0 && Object.values(dmData).some(v => Number(v) > 0);

if (!hasPieData) pieEmpty.style.display = "block";
if (!hasBarData) barEmpty.style.display = "block";

// Pie chart
if (hasPieData && pieCanvas) {
  new Chart(pieCanvas, {
    type: "pie",
    data: {
      labels: Object.keys(categoryData),
      datasets: [
        {
          data: Object.values(categoryData),
          borderWidth: 1,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "bottom" },
        tooltip: { enabled: true },
      },
    },
  });
}

// Bar chart
if (hasBarData && barCanvas) {
  new Chart(barCanvas, {
    type: "bar",
    data: {
      labels: Object.keys(dmData),
      datasets: [
        {
          label: "Expenses by MM-DD",
          data: Object.values(dmData),
          borderWidth: 1,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
      },
      scales: {
        y: { beginAtZero: true },
      },
    },
  });
}