(function(root, factory) {
  const citations = factory();
  if (typeof module === 'object' && module.exports) module.exports = citations;
  else root.RuangkerjaPdfCitations = citations;
})(typeof globalThis === 'object' ? globalThis : this, function() {
  const CONTEXT_LIMIT = 24 * 1024;
  const encoder = new TextEncoder();

  function contextFor(pageTexts) {
    const pages = [];
    for (let index = 0; index < pageTexts.length; index++) {
      const text = pageTexts[index].trim();
      if (!text) continue;
      const page = { halaman: index + 1, teks: text };
      if (encoder.encode(JSON.stringify([...pages, page], null, 2)).length <= CONTEXT_LIMIT) {
        pages.push(page);
        continue;
      }
      if (pages.length) break;
      const chars = Array.from(text);
      let low = 0;
      let high = Math.min(chars.length, CONTEXT_LIMIT);
      while (low < high) {
        const middle = Math.ceil((low + high) / 2);
        page.teks = chars.slice(0, middle).join('');
        if (encoder.encode(JSON.stringify([page], null, 2)).length <= CONTEXT_LIMIT) low = middle;
        else high = middle - 1;
      }
      page.teks = chars.slice(0, low).join('');
      pages.push(page);
      break;
    }
    return pages.length ? JSON.stringify(pages, null, 2) : '';
  }

  function verify(answer, sentContext) {
    const normalize = value => value.replace(/\s+/gu, ' ').trim();
    const pages = new Map(JSON.parse(sentContext).map(page => [page.halaman, normalize(page.teks)]));
    const lines = answer.split(/\r?\n/u).filter(line => line.trim());
    let supportedLines = 0;
    let quoteCount = 0;
    for (const line of lines) {
      const matches = [...line.matchAll(/\[Hal\.\s*([1-9]\d*):\s*(?:“([^”]+)”|"([^"]+)")\s*\]/giu)];
      const references = [...line.matchAll(/\[Hal\./giu)].length;
      const verified = matches.filter(([, page, curly, straight]) => {
        const quote = normalize(curly ?? straight);
        return quote.length >= 8 && pages.get(Number(page))?.includes(quote);
      }).length;
      quoteCount += verified;
      if (verified > 0 && verified === references) supportedLines++;
    }
    return { supportedLines, totalLines: lines.length, quoteCount };
  }

  return { contextFor, verify };
});
