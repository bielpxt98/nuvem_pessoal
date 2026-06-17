import test from 'node:test';
import assert from 'node:assert/strict';
import { filterFiles, groupByDate, mediaFiles, parseDateSearch } from '../src/gallery.js';

test('groups files by month and day in descending order', () => {
  const groups = groupByDate(mediaFiles);
  assert.equal(groups['2026-06'].label, 'JUNHO 2026');
  assert.equal(groups['2026-06'].days['2026-06-17'].length, 3);
  assert.equal(groups['2026-06'].days['2026-06-16'].length, 2);
});

test('parses supported Brazilian date search formats', () => {
  const referenceDate = new Date('2026-06-17T12:00:00');
  assert.equal(parseDateSearch('10/06/2026', referenceDate), '2026-06-10');
  assert.equal(parseDateSearch('10-06-2026', referenceDate), '2026-06-10');
  assert.equal(parseDateSearch('10/06', referenceDate), '2026-06-10');
  assert.equal(parseDateSearch('31/02/2026', referenceDate), null);
});

test('filters by selected date, period and media type', () => {
  const now = new Date('2026-06-17T12:00:00');
  assert.equal(filterFiles(mediaFiles, { date: '2026-06-16', now }).length, 2);
  assert.equal(filterFiles(mediaFiles, { filter: 'today', now }).length, 3);
  assert.equal(filterFiles(mediaFiles, { filter: 'yesterday', now }).length, 2);
  assert.equal(filterFiles(mediaFiles, { filter: 'month', now }).length, 6);
  assert.equal(filterFiles(mediaFiles, { filter: 'videos', now }).every((file) => file.type === 'video'), true);
});
