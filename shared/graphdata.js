// Shared read layer over the data-layer graph (nodes · bindings · edges).
// Both /graph/ (ego view) and /glyph/ (single-endpoint dossier) load the graph
// through here, so the node→card projection lives in ONE place and the two pages
// can't drift. Plain globals, no modules — same convention as base.js/cards3.js.

const TAGMAP = { stroke: 'stroke', component: 'comp', char: 'char' };

// loadGraph() → Promise<G>. G is the whole read model a page needs:
//   byGlyph     glyph        → node            (real + frontier)
//   byId        node id      → node            (glyphs, words, referents, entities)
//   bindById    binding id   → binding
//   refLabel    r:… id       → label
//   denotesOf   glyph        → r:… id
//   parts       glyph        → [glyphs it is built from]
//   appears     glyph        → [glyphs it appears in]
//   clusters    cf:… id      → cluster record (authored; n-ary payload)
//   confusOf    node id      → [cluster records] the node is a member of
function loadGraph() {
  return Promise.all([
    fetch('../data/nodes.json').then(r => r.json()),
    fetch('../data/edges.json').then(r => r.json()),
    fetch('../data/bindings.json').then(r => r.json()),
  ]).then(([nd, ed, bd]) => {
    const G = {
      nodes: nd.nodes, byGlyph: {}, byId: {}, bindById: {}, refLabel: {},
      denotesOf: {}, parts: {}, appears: {}, clusters: {}, confusOf: {},
    };
    bd.bindings.forEach(b => (G.bindById[b.id] = b));
    nd.nodes.forEach(n => {
      G.byId[n.id] = n;
      if (n.kind === 'glyph') G.byGlyph[n.glyph] = n;
      else if (n.kind === 'referent') G.refLabel[n.id] = n.label;
    });
    ed.edges.forEach(e => {
      if (e.kind === 'composes') {
        // composes also carries the word tier (g:人 → w:人工); a glyph ego graph
        // keys on glyphs only, so word targets are skipped here.
        if (!e.from.startsWith('g:') || !e.to.startsWith('g:')) return;
        const f = e.from.slice(2), t = e.to.slice(2);
        (G.appears[f] = G.appears[f] || []).push(t);
        (G.parts[t] = G.parts[t] || []).push(f);
      } else if (e.kind === 'denotes' && e.from.startsWith('g:')) {
        G.denotesOf[e.from.slice(2)] = e.to;
      }
    });
    // authored clusters: the n-ary payload lives once in edges.json's `clusters`
    // sibling key; index it by member so a node can ask "what am I confused with?"
    // without walking the clique. Absent key (older data) → simply no clusters.
    (ed.clusters || []).forEach(c => {
      G.clusters[c.id] = c;
      (c.members || []).forEach(m => (G.confusOf[m] = G.confusOf[m] || []).push(c));
    });
    return G;
  });
}

// ── node → cards3 card (the projection /graph/ and /glyph/ both render) ──
function gdView(b) {
  const v = { name: b.name, reading: b.readings[0] || '', gloss: b.gloss, extra: b.extra };
  if (b.appearsIn) v.appearsIn = { char: b.appearsIn.glyph, reading: b.appearsIn.reading, gloss: b.appearsIn.gloss };
  return v;
}
function gdWk(jp) {
  const p = jp && jp.program;
  if (!p || p.source !== 'wanikani' || !p.name) return null;
  const wk = { name: p.name, level: p.level, kind: p.kind };
  if (p.altglyph) wk.glyph = p.altglyph;
  if (p.icon) wk.icon = p.icon;
  return wk;
}
function gdKanji(jp) {
  const k = jp && jp.program && jp.program.kanji;
  return k ? { name: k.name, readings: k.readings, on: k.on, level: k.level } : null;
}
function cardFromNode(G, node) {
  const cn = G.bindById[`b:${node.glyph}@cn`], jp = G.bindById[`b:${node.glyph}@jp`];
  return {
    glyph: node.glyph, tag: TAGMAP[node.tier],
    image: node.media.image, hw: node.media.hw,
    // content-keyed bank keys stamped on the node by build-graph (cnSrc/jpSrc)
    cnAudioKey: node.cnAudioKey, cnExAudioKey: node.cnExAudioKey,
    jpAudioKey: node.jpAudioKey, jpExAudioKey: node.jpExAudioKey,
    cn: gdView(cn), jp: gdView(jp), wk: gdWk(jp), kanji: gdKanji(jp),
  };
}

// facts(): the one-line reading summary the ego card and the dossier hero share.
function gdFacts(G, glyph) {
  const cn = G.bindById[`b:${glyph}@cn`], jp = G.bindById[`b:${glyph}@jp`];
  const py = (cn && cn.readings[0]) || '';
  const kana = (jp && jp.readings[0]) || '';
  const p = jp && jp.program;
  return {
    py, kana,
    gloss: (cn && cn.gloss) || (jp && jp.gloss) || '',
    wk: p && p.source === 'wanikani' ? p.name : '',
    mean: p && p.kind === 'meaning',
  };
}
