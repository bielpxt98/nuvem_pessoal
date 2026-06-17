export const mediaFiles = [
  { id: 1, name: 'Praia ao amanhecer', type: 'photo', date: '2026-06-17', src: 'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=800&q=80' },
  { id: 2, name: 'Família no parque', type: 'photo', date: '2026-06-17', src: 'https://images.unsplash.com/photo-1511895426328-dc8714191300?auto=format&fit=crop&w=800&q=80' },
  { id: 3, name: 'Vídeo da viagem', type: 'video', date: '2026-06-17', src: 'https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=800&q=80' },
  { id: 4, name: 'Café da tarde', type: 'photo', date: '2026-06-16', src: 'https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?auto=format&fit=crop&w=800&q=80' },
  { id: 5, name: 'Aniversário', type: 'video', date: '2026-06-16', src: 'https://images.unsplash.com/photo-1464349095431-e9a21285b5f3?auto=format&fit=crop&w=800&q=80' },
  { id: 6, name: 'Jardim florido', type: 'photo', date: '2026-06-15', src: 'https://images.unsplash.com/photo-1490750967868-88aa4486c946?auto=format&fit=crop&w=800&q=80' },
  { id: 7, name: 'Passeio de maio', type: 'photo', date: '2026-05-10', src: 'https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?auto=format&fit=crop&w=800&q=80' },
  { id: 8, name: 'Vídeo de maio', type: 'video', date: '2026-05-10', src: 'https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?auto=format&fit=crop&w=800&q=80' },
  { id: 9, name: 'Arquivo antigo', type: 'photo', date: '2025-12-24', src: 'https://images.unsplash.com/photo-1512389142860-9c449e58a543?auto=format&fit=crop&w=800&q=80' }
];

const monthNames = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'];

export function toLocalDate(isoDate) {
  const [year, month, day] = isoDate.split('-').map(Number);
  return new Date(year, month - 1, day);
}

export function formatDateBR(isoDate) {
  const date = toLocalDate(isoDate);
  return date.toLocaleDateString('pt-BR');
}

export function formatMonthYear(isoDate) {
  const date = toLocalDate(isoDate);
  return `${monthNames[date.getMonth()].toUpperCase()} ${date.getFullYear()}`;
}

export function groupByDate(files) {
  return files
    .toSorted((a, b) => b.date.localeCompare(a.date))
    .reduce((groups, file) => {
      const monthKey = file.date.slice(0, 7);
      groups[monthKey] ??= { label: formatMonthYear(file.date), days: {} };
      groups[monthKey].days[file.date] ??= [];
      groups[monthKey].days[file.date].push(file);
      return groups;
    }, {});
}

export function parseDateSearch(query, referenceDate = new Date()) {
  const normalized = query.trim().replaceAll('-', '/');
  const match = normalized.match(/^(\d{1,2})\/(\d{1,2})(?:\/(\d{4}))?$/);
  if (!match) return null;

  const [, dayRaw, monthRaw, yearRaw] = match;
  const day = Number(dayRaw);
  const month = Number(monthRaw);
  const year = Number(yearRaw ?? referenceDate.getFullYear());
  const date = new Date(year, month - 1, day);

  if (date.getFullYear() !== year || date.getMonth() !== month - 1 || date.getDate() !== day) {
    return null;
  }

  return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
}

export function filterFiles(files, { filter = 'all', date, searchDate, now = new Date() } = {}) {
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);

  return files.filter((file) => {
    const fileDate = toLocalDate(file.date);
    if (date && file.date !== date) return false;
    if (searchDate && file.date !== searchDate) return false;
    if (filter === 'today' && fileDate.getTime() !== today.getTime()) return false;
    if (filter === 'yesterday' && fileDate.getTime() !== yesterday.getTime()) return false;
    if (filter === 'month' && (fileDate.getMonth() !== today.getMonth() || fileDate.getFullYear() !== today.getFullYear())) return false;
    if (filter === 'photos' && file.type !== 'photo') return false;
    if (filter === 'videos' && file.type !== 'video') return false;
    return true;
  });
}
