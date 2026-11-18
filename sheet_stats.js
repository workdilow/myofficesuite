(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.RuangkerjaSheetStats = api;
})(typeof window === 'undefined' ? globalThis : window, function () {
  const NUMBER_PATTERN = /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i;

  // Literal cells are interpreted using the Indonesian convention: dot groups
  // thousands and comma marks decimals. Formula results stay in GridCraft's
  // canonical numeric representation and never go through locale guessing.
  function parseIndonesianLiteral(input) {
    let value = String(input ?? '').trim().replace(/[\u00a0\u202f\s]/g, '');
    if (!value) return null;
    let negative = false;
    if (/^\(.*\)$/.test(value)) {
      negative = true;
      value = value.slice(1, -1);
    }
    const sign = value[0] === '-' || value[0] === '+' ? value[0] : '';
    if (sign) value = value.slice(1);
    if (!value || /[+-]/.test(value)) return null;

    const commaCount = (value.match(/,/g) || []).length;
    const dotCount = (value.match(/\./g) || []).length;
    let canonical;
    if (commaCount && dotCount) {
      // Accept either common mixed-separator spelling only when its grouping
      // and decimal portions are structurally valid.
      const decimal = value.lastIndexOf(',') > value.lastIndexOf('.') ? ',' : '.';
      const grouping = decimal === ',' ? '.' : ',';
      const decimalIndex = value.lastIndexOf(decimal);
      const integer = value.slice(0, decimalIndex);
      const fraction = value.slice(decimalIndex + 1);
      if (!/^\d{1,2}$/.test(fraction) || value.slice(decimalIndex + 1).includes(decimal)) return null;
      const groups = integer.split(grouping);
      if (!/^\d{1,3}$/.test(groups[0]) || groups.slice(1).some(group => !/^\d{3}$/.test(group))) return null;
      canonical = `${groups.join('')}.${fraction}`;
    } else if (commaCount || dotCount) {
      const separator = commaCount ? ',' : '.';
      const parts = value.split(separator);
      if (parts.some(part => !/^\d+$/.test(part))) return null;
      const isGrouped = parts[0].length >= 1 && parts[0].length <= 3 && parts.slice(1).every(part => part.length === 3);
      if (parts.length === 2 && parts[1].length > 0 && (parts[1].length !== 3 || !isGrouped)) {
        canonical = `${parts[0] || '0'}.${parts[1]}`;
      } else if (isGrouped) {
        canonical = parts.join('');
      } else {
        return null;
      }
    } else {
      canonical = value;
    }

    const numericText = `${negative || sign === '-' ? '-' : sign === '+' ? '+' : ''}${canonical}`;
    if (!NUMBER_PATTERN.test(numericText)) return null;
    const number = Number(numericText);
    return Number.isFinite(number) ? number : null;
  }

  function summarizeRange(target) {
    const numericCells = [];
    let emptyCount = 0;
    let textCount = 0;
    let formulaCount = 0;
    let formulaNumericCount = 0;
    for (let row = 0; row < target.rowCount; row++) {
      for (let column = 0; column < target.columnCount; column++) {
        const raw = String(target.values[row]?.[column] ?? '').trim();
        if (!raw) {
          emptyCount++;
          continue;
        }
        const formula = raw.startsWith('=');
        if (formula) formulaCount++;
        const candidate = formula ? target.calculatedValues?.[row]?.[column] : raw;
        const normalized = String(candidate ?? '').trim();
        const value = formula
          ? (NUMBER_PATTERN.test(normalized) ? Number(normalized) : null)
          : parseIndonesianLiteral(normalized);
        if (value === null) {
          if (!formula) textCount++;
          continue;
        }
        if (!Number.isFinite(value)) {
          if (!formula) textCount++;
          continue;
        }
        if (formula) formulaNumericCount++;
        const columnNumber = target.startColumn + column;
        let label = '';
        for (let current = columnNumber; current > 0; current = Math.floor((current - 1) / 26)) {
          label = String.fromCharCode(65 + ((current - 1) % 26)) + label;
        }
        numericCells.push({ address: `${label}${target.startRow + row}`, value, kind: formula ? 'formula' : 'literal', input: raw });
      }
    }

    const sorted = numericCells.map(cell => cell.value).sort((a, b) => a - b);
    let sum = 0;
    let compensation = 0;
    for (const value of sorted) {
      const adjusted = value - compensation;
      const next = sum + adjusted;
      compensation = (next - sum) - adjusted;
      sum = next;
    }
    const count = sorted.length;
    const median = count === 0 ? null : count % 2 === 1
      ? sorted[Math.floor(count / 2)]
      : sorted[count / 2 - 1] / 2 + sorted[count / 2] / 2;
    return {
      range: target.range,
      cellCount: target.rowCount * target.columnCount,
      numericCount: count,
      literalCount: count - formulaNumericCount,
      formulaNumericCount,
      emptyCount,
      textCount,
      formulaCount,
      sum: count ? sum : null,
      mean: count ? sum / count : null,
      median,
      min: count ? sorted[0] : null,
      max: count ? sorted[count - 1] : null,
      numericCells,
    };
  }

  return { summarizeRange, parseIndonesianLiteral };
});
