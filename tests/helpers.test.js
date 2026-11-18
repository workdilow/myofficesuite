const assert = require('node:assert/strict');
const { test } = require('node:test');
const { summarizeRange, parseIndonesianLiteral } = require('../sheet_stats');
const { diffParagraphs } = require('../writer_review');

test('statistics include Indonesian literals and calculated formulas with source addresses', () => {
  assert.equal(parseIndonesianLiteral('1.234,50'), 1234.5);
  const stats = summarizeRange({
    startRow: 2, startColumn: 2, rowCount: 2, columnCount: 2,
    values: [['1.234', '=A1+1'], ['2,5', 'teks']],
    calculatedValues: [['', 8], ['', '']],
  });
  assert.deepEqual(stats.numericCells.map(cell => [cell.address, cell.value]), [
    ['B2', 1234], ['C2', 8], ['B3', 2.5],
  ]);
  assert.equal(stats.sum, 1244.5);
  assert.equal(stats.median, 8);
});

test('Writer separates distant changes in long documents', () => {
  const before = Array.from({ length: 700 }, (_, i) => `Paragraph ${i}`);
  const after = [...before];
  after[30] = 'First edit';
  after[620] = 'Last edit';
  const diff = diffParagraphs(before.join('\n'), after.join('\n'));
  assert.equal(diff.changes.length, 2);
  assert.deepEqual(diff.changes.map(change => change.start), [30, 620]);
});
