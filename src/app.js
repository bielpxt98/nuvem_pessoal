import { filterFiles, formatDateBR, groupByDate, mediaFiles, parseDateSearch } from './gallery.js';

const state = {
  filter: 'all',
  selectedDate: null,
  searchDate: null,
  now: new Date('2026-06-17T12:00:00')
};

const menuItems = document.querySelectorAll('.menu-item');
const searchInput = document.querySelector('#date-search');
const summary = document.querySelector('#summary');
const dateGroups = document.querySelector('#date-groups');
const gallery = document.querySelector('#gallery');

function pluralize(count, singular, plural) {
  return count === 1 ? singular : plural;
}

function renderGroups(files) {
  const groups = groupByDate(files);
  dateGroups.innerHTML = Object.entries(groups).map(([monthKey, monthGroup]) => {
    const days = Object.entries(monthGroup.days)
      .sort(([dateA], [dateB]) => dateB.localeCompare(dateA))
      .map(([date, dayFiles]) => `
        <button class="day-row ${state.selectedDate === date ? 'selected' : ''}" data-date="${date}">
          <span>${formatDateBR(date)}</span>
          <strong>${dayFiles.length} ${pluralize(dayFiles.length, 'arquivo', 'arquivos')}</strong>
        </button>
      `)
      .join('');

    return `
      <article class="month-group" data-month="${monthKey}">
        <h2>${monthGroup.label}</h2>
        <div class="day-list">${days}</div>
      </article>
    `;
  }).join('');

  dateGroups.querySelectorAll('[data-date]').forEach((button) => {
    button.addEventListener('click', () => {
      state.selectedDate = button.dataset.date;
      state.searchDate = null;
      searchInput.value = '';
      render();
    });
  });
}

function renderGallery(files) {
  if (!files.length) {
    gallery.innerHTML = '<div class="empty">Nenhum arquivo encontrado para este filtro.</div>';
    return;
  }

  gallery.innerHTML = files
    .toSorted((a, b) => b.date.localeCompare(a.date) || a.name.localeCompare(b.name))
    .map((file) => `
      <article class="media-card">
        <img src="${file.src}" alt="${file.name}" loading="lazy" />
        <div>
          <span class="badge">${file.type === 'photo' ? 'Foto' : 'Vídeo'}</span>
          <h3>${file.name}</h3>
          <p>${formatDateBR(file.date)}</p>
        </div>
      </article>
    `)
    .join('');
}

function renderSummary(files) {
  const activeDate = state.selectedDate ?? state.searchDate;
  const dateText = activeDate ? ` em ${formatDateBR(activeDate)}` : '';
  const photoCount = files.filter((file) => file.type === 'photo').length;
  const videoCount = files.filter((file) => file.type === 'video').length;

  summary.innerHTML = `
    <div><strong>${files.length}</strong><span>${pluralize(files.length, 'arquivo encontrado', 'arquivos encontrados')}${dateText}</span></div>
    <div><strong>${photoCount}</strong><span>Fotos</span></div>
    <div><strong>${videoCount}</strong><span>Vídeos</span></div>
    ${activeDate ? '<button id="clear-date" class="clear-button">Limpar data</button>' : ''}
  `;

  document.querySelector('#clear-date')?.addEventListener('click', () => {
    state.selectedDate = null;
    state.searchDate = null;
    searchInput.value = '';
    render();
  });
}

function render() {
  const filteredFiles = filterFiles(mediaFiles, state);
  renderSummary(filteredFiles);
  renderGroups(filterFiles(mediaFiles, { filter: state.filter, now: state.now }));
  renderGallery(filteredFiles);
}

menuItems.forEach((item) => {
  item.addEventListener('click', () => {
    menuItems.forEach((menuItem) => menuItem.classList.remove('active'));
    item.classList.add('active');
    state.filter = item.dataset.filter;
    state.selectedDate = null;
    state.searchDate = null;
    searchInput.value = '';
    render();
  });
});

searchInput.addEventListener('input', () => {
  state.searchDate = parseDateSearch(searchInput.value, state.now);
  state.selectedDate = null;
  render();
});

render();
