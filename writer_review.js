(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.RuangkerjaTextReview = api;
})(typeof window === 'undefined' ? globalThis : window, function () {
  const MAX_PARAGRAPHS = 250;

  function paragraphs(text) {
    return String(text).split(/\r?\n/);
  }

  function diffParagraphs(source, suggestion) {
    const before = paragraphs(source);
    const after = paragraphs(suggestion);
    const changes = [];
    diffRange(before, after, 0, before.length, 0, after.length, changes);
    return { wholeDocument: false, changes: changes.map((change, id) => ({ ...change, id })) };
  }

  function diffRange(before, after, beforeStart, beforeEnd, afterStart, afterEnd, changes) {
    while (beforeStart < beforeEnd && afterStart < afterEnd && before[beforeStart] === after[afterStart]) {
      beforeStart++;
      afterStart++;
    }
    while (beforeStart < beforeEnd && afterStart < afterEnd && before[beforeEnd - 1] === after[afterEnd - 1]) {
      beforeEnd--;
      afterEnd--;
    }
    if (beforeStart === beforeEnd && afterStart === afterEnd) return;

    const beforeCount = beforeEnd - beforeStart;
    const afterCount = afterEnd - afterStart;
    if (beforeCount <= MAX_PARAGRAPHS && afterCount <= MAX_PARAGRAPHS) {
      diffSmallRange(before, after, beforeStart, beforeEnd, afterStart, afterEnd, changes);
      return;
    }

    const anchors = uniqueAnchors(before, after, beforeStart, beforeEnd, afterStart, afterEnd);
    if (!anchors.length) {
      changes.push({
        kind: 'replace',
        start: beforeStart,
        deleteCount: beforeCount,
        original: before.slice(beforeStart, beforeEnd),
        suggested: after.slice(afterStart, afterEnd),
      });
      return;
    }

    let previousBefore = beforeStart;
    let previousAfter = afterStart;
    for (const anchor of anchors) {
      diffRange(before, after, previousBefore, anchor.before, previousAfter, anchor.after, changes);
      previousBefore = anchor.before + 1;
      previousAfter = anchor.after + 1;
    }
    diffRange(before, after, previousBefore, beforeEnd, previousAfter, afterEnd, changes);
  }

  function uniqueAnchors(before, after, beforeStart, beforeEnd, afterStart, afterEnd) {
    const beforeCounts = new Map();
    const afterCounts = new Map();
    const beforePositions = new Map();
    const afterPositions = new Map();
    for (let index = beforeStart; index < beforeEnd; index++) {
      const value = before[index];
      beforeCounts.set(value, (beforeCounts.get(value) || 0) + 1);
      beforePositions.set(value, index);
    }
    for (let index = afterStart; index < afterEnd; index++) {
      const value = after[index];
      afterCounts.set(value, (afterCounts.get(value) || 0) + 1);
      afterPositions.set(value, index);
    }
    const pairs = [];
    for (const [value, beforeIndex] of beforePositions) {
      if (beforeCounts.get(value) === 1 && afterCounts.get(value) === 1) {
        pairs.push({ before: beforeIndex, after: afterPositions.get(value) });
      }
    }
    pairs.sort((a, b) => a.before - b.before);
    if (pairs.length < 2) return pairs;

    const tails = [];
    const tailPairIndexes = [];
    const previous = new Int32Array(pairs.length).fill(-1);
    for (let index = 0; index < pairs.length; index++) {
      const target = pairs[index].after;
      let low = 0;
      let high = tails.length;
      while (low < high) {
        const middle = (low + high) >>> 1;
        if (tails[middle] < target) low = middle + 1;
        else high = middle;
      }
      if (low > 0) previous[index] = tailPairIndexes[low - 1];
      tails[low] = target;
      tailPairIndexes[low] = index;
    }
    const ordered = [];
    let index = tailPairIndexes[tails.length - 1];
    while (index >= 0) {
      ordered.push(pairs[index]);
      index = previous[index];
    }
    return ordered.reverse();
  }

  function diffSmallRange(before, after, beforeStart, beforeEnd, afterStart, afterEnd, changes) {
    const beforeCount = beforeEnd - beforeStart;
    const afterCount = afterEnd - afterStart;
    const width = afterCount + 1;
    const table = new Uint16Array((beforeCount + 1) * width);
    for (let i = beforeCount - 1; i >= 0; i--) {
      for (let j = afterCount - 1; j >= 0; j--) {
        const index = i * width + j;
        table[index] = before[beforeStart + i] === after[afterStart + j]
          ? 1 + table[(i + 1) * width + j + 1]
          : Math.max(table[(i + 1) * width + j], table[i * width + j + 1]);
      }
    }

    const anchors = [];
    let i = 0;
    let j = 0;
    while (i < beforeCount && j < afterCount) {
      if (before[beforeStart + i] === after[afterStart + j]) {
        anchors.push({ before: beforeStart + i, after: afterStart + j });
        i++;
        j++;
      } else if (table[(i + 1) * width + j] >= table[i * width + j + 1]) {
        i++;
      } else {
        j++;
      }
    }
    anchors.push({ before: beforeEnd, after: afterEnd });

    let previousBefore = beforeStart - 1;
    let previousAfter = afterStart - 1;
    for (const anchor of anchors) {
      const localBeforeStart = previousBefore + 1;
      const localAfterStart = previousAfter + 1;
      const localBeforeCount = anchor.before - localBeforeStart;
      const localAfterCount = anchor.after - localAfterStart;
      const paired = Math.min(localBeforeCount, localAfterCount);
      for (let offset = 0; offset < paired; offset++) {
        if (before[localBeforeStart + offset] !== after[localAfterStart + offset]) {
          changes.push({
            kind: 'replace',
            start: localBeforeStart + offset,
            deleteCount: 1,
            original: [before[localBeforeStart + offset]],
            suggested: [after[localAfterStart + offset]],
          });
        }
      }
      for (let offset = paired; offset < localBeforeCount; offset++) {
        changes.push({
          kind: 'delete',
          start: localBeforeStart + offset,
          deleteCount: 1,
          original: [before[localBeforeStart + offset]],
          suggested: [],
        });
      }
      if (localAfterCount > paired) {
        changes.push({
          kind: 'insert',
          start: localBeforeStart + paired,
          deleteCount: 0,
          original: [],
          suggested: after.slice(localAfterStart + paired, anchor.after),
        });
      }
      previousBefore = anchor.before;
      previousAfter = anchor.after;
    }
  }

  function applySelected(source, changes, replacements) {
    const original = paragraphs(source);
    const selected = changes
      .filter(change => Object.hasOwn(replacements, change.id))
      .slice()
      .sort((a, b) => a.start - b.start);
    if (!selected.length) return String(source);

    const result = [];
    let cursor = 0;
    for (const change of selected) {
      if (change.start < cursor) throw new Error('paragraph changes overlap');
      result.push(...original.slice(cursor, change.start));
      result.push(...replacements[change.id]);
      cursor = change.start + change.deleteCount;
    }
    result.push(...original.slice(cursor));
    return result.join('\n');
  }

  return { diffParagraphs, applySelected, MAX_PARAGRAPHS };
});
