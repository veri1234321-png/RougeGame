// =========================
// Смена темы
// =========================

const themeBtn = document.getElementById("themeBtn");

themeBtn.addEventListener("click", () => {
  document.body.classList.toggle("dark-theme");
});


// =========================
// Слайдер
// =========================

const slides = document.querySelectorAll(".slide");
const nextBtn = document.querySelector(".next");
const prevBtn = document.querySelector(".prev");

let currentSlide = 0;

function showSlide(index){

  slides.forEach(slide => {
    slide.classList.remove("active");
  });

  slides[index].classList.add("active");
}

nextBtn.addEventListener("click", () => {

  currentSlide++;

  if(currentSlide >= slides.length){
    currentSlide = 0;
  }

  showSlide(currentSlide);
});

prevBtn.addEventListener("click", () => {

  currentSlide--;

  if(currentSlide < 0){
    currentSlide = slides.length - 1;
  }

  showSlide(currentSlide);
});


// =========================
// Прогресс проекта
// =========================

const progress = document.getElementById("progress");
const progressBtn = document.getElementById("progressBtn");
const completeMessage = document.getElementById("completeMessage");

const stages = [
  "🧩 Этап 1 — Базовая архитектура",
  "🏰 Этап 2 — Генерация уровней",
  "🚶 Этап 3 — Система перемещения",
  "⚔️ Этап 4 — Боевая система",
  "👾 Этап 5 — AI врагов",
  "✨ Этап 6 — Способности",
  "❄️ Этап 7 — Freeze Ability",
  "🛠️ Этап 8 — Полировка проекта"
];

let currentStage = 0;
let progressWidth = 0;
let animationActive = false;

completeMessage.innerHTML = stages[currentStage];

progressBtn.addEventListener("click", () => {

  if(animationActive){
    return;
  }

  if(currentStage >= stages.length){
    return;
  }

  progressWidth += 25;

  if(progressWidth > 100){
    progressWidth = 100;
  }

  progress.style.width = progressWidth + "%";

  if(progressWidth >= 100){

    animationActive = true;

    completeMessage.innerHTML =
      "✅ " + stages[currentStage] + " завершён";

    document.body.classList.add("event-theme");

    setTimeout(() => {

      document.body.classList.remove("event-theme");

      currentStage++;

      if(currentStage < stages.length){

        progressWidth = 0;

        progress.style.width = "0%";

        completeMessage.innerHTML =
          stages[currentStage];

      }

      else{

        progress.style.width = "100%";

        completeMessage.innerHTML =
          "🏆 Проект полностью завершён";

        progressBtn.innerText =
          "Все этапы завершены";

        progressBtn.disabled = true;
      }

      animationActive = false;

    }, 2500);
  }
});