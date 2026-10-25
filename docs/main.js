/* Progressive enhancement: navigation, publication filters and diagram viewer. */
(() => {
  'use strict';
  document.documentElement.classList.add('js');
  const menuButton = document.querySelector('.menu-toggle');
  const menu = document.querySelector('#site-nav');
  if (menuButton && menu) {
    menuButton.hidden = false;
    const closeMenu = () => {
      menu.classList.remove('is-open');
      menuButton.setAttribute('aria-expanded', 'false');
    };
    menuButton.addEventListener('click', () => {
      const open = menuButton.getAttribute('aria-expanded') !== 'true';
      menuButton.setAttribute('aria-expanded', String(open));
      menu.classList.toggle('is-open', open);
    });
    menu.querySelectorAll('a').forEach(link => link.addEventListener('click', closeMenu));
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && menu.classList.contains('is-open')) {
        closeMenu();
        menuButton.focus();
      }
    });
    window.matchMedia('(min-width: 801px)').addEventListener('change', closeMenu);
  }
  const controls = document.querySelector('.publication-controls');
  if (controls) {
    controls.hidden = false;
    const papers = [...document.querySelectorAll('.publication')];
    const buttons = [...controls.querySelectorAll('[data-filter]')];
    const count = document.querySelector('#publication-count');
    buttons.forEach(button => button.addEventListener('click', () => {
      const topic = button.dataset.filter;
      let visible = 0;
      papers.forEach(paper => {
        const show = topic === 'all' || paper.dataset.topics.split(' ').includes(topic);
        paper.hidden = !show;
        if (show) visible++;
      });
      buttons.forEach(item => item.setAttribute('aria-pressed', String(item === button)));
      count.textContent = `${visible} selected publication${visible === 1 ? '' : 's'}`;
    }));
  }
  const dialog = document.querySelector('.framework-dialog');
  if (dialog && typeof dialog.showModal === 'function') {
    document.querySelectorAll('[data-framework-open]').forEach(link => {
      link.addEventListener('click', event => {
        event.preventDefault();
        dialog.showModal();
        document.body.classList.add('dialog-open');
      });
    });
    dialog.querySelector('[data-framework-close]').addEventListener('click', () => dialog.close());
    dialog.addEventListener('click', event => {
      if (event.target !== dialog) return;
      const bounds = dialog.getBoundingClientRect();
      if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) dialog.close();
    });
    dialog.addEventListener('close', () => document.body.classList.remove('dialog-open'));
  }
})();
