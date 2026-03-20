const isDark = document.documentElement.getAttribute('data-theme') === 'dark'
  || localStorage.getItem('theme') === 'dark';

const gridColor  = isDark ? '#262626' : '#f3f4f6';
const labelColor = isDark ? '#a3a3a3' : '#6b7280';

const PALETTE = ['#6366f1','#8b5cf6','#06b6d4','#10b981','#f59e0b','#ef4444','#ec4899','#14b8a6'];

Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.font.size   = 11;

const catData = JSON.parse(document.getElementById('categoryData').textContent);
const catKeys = Object.keys(catData);
const catVals = Object.values(catData);
const pieCtx  = document.getElementById('expenseChart');

if (pieCtx) {
  if (catKeys.length === 0) {
    document.getElementById('pieEmpty').style.display = 'block';
    pieCtx.style.display = 'none';
  } else {
    new Chart(pieCtx, {
      type: 'doughnut',
      data: {
        labels: catKeys,
        datasets: [{ data: catVals, backgroundColor: PALETTE.slice(0, catKeys.length), borderWidth: 0, hoverOffset: 4 }]
      },
      options: {
        responsive: true, maintainAspectRatio: false, cutout: '68%',
        plugins: {
          legend: { position: 'bottom', labels: { color: labelColor, boxWidth: 8, padding: 8, font: { size: 10 } } },
          tooltip: {
            backgroundColor: isDark ? '#1a1a1a' : '#ffffff',
            titleColor: isDark ? '#fafafa' : '#111827',
            bodyColor: labelColor, borderColor: isDark ? '#262626' : '#e5e7eb', borderWidth: 1, padding: 8,
            callbacks: { label: ctx => ` ₹${ctx.parsed.toLocaleString('en-IN', {minimumFractionDigits:2})}` }
          }
        },
        animation: { duration: 600 }
      }
    });
  }
}

const dmData = JSON.parse(document.getElementById('dmData').textContent);
const dmKeys = Object.keys(dmData);
const dmVals = Object.values(dmData);
const barCtx = document.getElementById('dmChart');

if (barCtx) {
  if (dmKeys.length === 0) {
    document.getElementById('barEmpty').style.display = 'block';
    barCtx.style.display = 'none';
  } else {
    new Chart(barCtx, {
      type: 'bar',
      data: {
        labels: dmKeys,
        datasets: [{
          data: dmVals,
          backgroundColor: isDark ? 'rgba(99,102,241,0.5)' : 'rgba(99,102,241,0.15)',
          borderColor: '#6366f1', borderWidth: 1.5, borderRadius: 4, borderSkipped: false,
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: isDark ? '#1a1a1a' : '#ffffff',
            titleColor: isDark ? '#fafafa' : '#111827',
            bodyColor: labelColor, borderColor: isDark ? '#262626' : '#e5e7eb', borderWidth: 1, padding: 8,
            callbacks: { label: ctx => ` ₹${ctx.parsed.y.toLocaleString('en-IN', {minimumFractionDigits:2})}` }
          }
        },
        scales: {
          x: { grid: { color: gridColor, drawBorder: false }, ticks: { color: labelColor } },
          y: { grid: { color: gridColor, drawBorder: false }, ticks: { color: labelColor, callback: v => '₹' + v.toLocaleString('en-IN') } }
        },
        animation: { duration: 600 }
      }
    });
  }
}