const themeToggle = document.querySelector(".theme-toggle");

themeToggle?.addEventListener("click", () => {
  const isDark = document.documentElement.dataset.theme === "dark";
  if (isDark) {
    delete document.documentElement.dataset.theme;
    localStorage.setItem("theme", "light");
  } else {
    document.documentElement.dataset.theme = "dark";
    localStorage.setItem("theme", "dark");
  }
});

const year = document.querySelector("#year");
if (year) year.textContent = new Date().getFullYear();
