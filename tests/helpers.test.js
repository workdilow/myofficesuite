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

const { read: readAiStream } = require('../ai_stream');

function byteStream(parts) {
  return new ReadableStream({
    start(controller) {
      parts.forEach(part => controller.enqueue(part));
      controller.close();
    },
  });
}

test('AI stream assembles UTF-8 across arbitrary transport chunks', async () => {
  const bytes = new TextEncoder().encode('{"delta":"Halo ✦"}\n{"delta":" dunia"}\n{"done":true}\n');
  const deltas = [];
  const result = await readAiStream(byteStream(Array.from(bytes, byte => Uint8Array.of(byte))), delta => deltas.push(delta));
  assert.deepEqual(deltas, ['Halo ✦', ' dunia']);
  assert.equal(result, 'Halo ✦ dunia');
});

test('AI stream refuses to finalize a preview after an interrupted response', async () => {
  const bytes = new TextEncoder().encode('{"delta":"Hasil parsial"}\n');
  await assert.rejects(readAiStream(byteStream([bytes]), () => {}), /terputus/);
});

const { contextFor, verify } = require('../pdf_citations');

test('PDF quote checks use the cited page and require a verified reference on each line', () => {
  const context = contextFor(['Kalimat ini\nada pada halaman satu.', '', 'Kutipan lain ada di halaman tiga.']);
  const answer = '- Satu [Hal. 1: “Kalimat ini ada pada halaman satu.”]\n'
    + '- Salah halaman [Hal. 3: “Kalimat ini ada pada halaman satu.”]\n'
    + '- Tanpa sumber\n'
    + '- Referensi campuran [Hal. 3: "Kutipan lain"] [Hal. 2: "tidak ada"]';
  assert.deepEqual(verify(answer, context), { supportedLines: 1, totalLines: 4, quoteCount: 2 });
});

test('PDF verification cannot cite page text excluded from the approved preview', () => {
  const context = contextFor(['漢'.repeat(25000) + 'Di luar batas konteks.', 'Halaman ini juga di luar konteks.']);
  assert.ok(new TextEncoder().encode(context).length <= 24 * 1024);
  assert.deepEqual(verify('- Klaim [Hal. 1: “Di luar batas konteks.”]', context), {
    supportedLines: 0, totalLines: 1, quoteCount: 0,
  });
});
