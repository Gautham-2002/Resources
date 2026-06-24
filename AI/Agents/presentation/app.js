/* ========================================================
   AI Agents & Orchestration — Slide Navigation
   ======================================================== */

document.addEventListener('DOMContentLoaded', () => {
  const slides = document.querySelectorAll('.slide');
  const progressBar = document.querySelector('.progress-bar');
  const prevBtn = document.querySelector('#prev-btn');
  const nextBtn = document.querySelector('#next-btn');
  const counter = document.querySelector('.slide-counter');
  const sectionDots = document.querySelectorAll('.section-dot');

  let current = 0;
  const total = slides.length;

  function goTo(index) {
    if (index < 0 || index >= total) return;

    // Remove all states
    slides.forEach(s => {
      s.classList.remove('active', 'prev');
    });

    // Mark previous slides
    for (let i = 0; i < index; i++) {
      slides[i].classList.add('prev');
    }

    // Activate current
    slides[index].classList.add('active');
    current = index;

    // Update progress
    const pct = ((current + 1) / total) * 100;
    progressBar.style.width = pct + '%';

    // Update counter
    counter.textContent = `${current + 1} / ${total}`;

    // Update buttons
    prevBtn.disabled = current === 0;
    nextBtn.disabled = current === total - 1;

    // Update section dots
    const currentSection = slides[current].dataset.section;
    sectionDots.forEach(dot => {
      dot.classList.toggle('active', dot.dataset.section === currentSection);
    });
  }

  function next() { goTo(current + 1); }
  function prev() { goTo(current - 1); }

  // Keyboard navigation
  document.addEventListener('keydown', e => {
    if (e.key === 'ArrowRight' || e.key === ' ') { e.preventDefault(); next(); }
    if (e.key === 'ArrowLeft') { e.preventDefault(); prev(); }
    if (e.key === 'Home') { e.preventDefault(); goTo(0); }
    if (e.key === 'End') { e.preventDefault(); goTo(total - 1); }
  });

  // Button clicks
  prevBtn.addEventListener('click', prev);
  nextBtn.addEventListener('click', next);

  // Section dot clicks — jump to first slide of that section
  sectionDots.forEach(dot => {
    dot.addEventListener('click', () => {
      const section = dot.dataset.section;
      const targetSlide = document.querySelector(`.slide[data-section="${section}"]`);
      if (targetSlide) {
        const idx = Array.from(slides).indexOf(targetSlide);
        goTo(idx);
      }
    });
  });

  // Touch / swipe support
  let touchStartX = 0;
  document.addEventListener('touchstart', e => {
    touchStartX = e.changedTouches[0].screenX;
  });
  document.addEventListener('touchend', e => {
    const diff = touchStartX - e.changedTouches[0].screenX;
    if (Math.abs(diff) > 60) {
      diff > 0 ? next() : prev();
    }
  });

  // Init
  goTo(0);
});
