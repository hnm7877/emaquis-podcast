// Short: "Ton maquis perd de l'argent chaque soir". All times are SOURCE seconds (files/words.md).
// Beats:
//  0.0  hook   : "Où passe ton argent ?" + casiers counting up on "casiers sortis de ton dépôt"
//  5.7  caisse : "Dans la caisse ?" big question, accent on caisse
//  8.5  face   : full camera "Tu hésites ? C'est normal… ton argent s'en va"
// 11.75 leaks  : three leaks appear then get struck (cahier, bouteilles, table)
// 17.4  cause  : "malchance" struck -> "manque d'outils"
// 20.2  fix    : E-Maquis logo hero, then 3 checks (ventes, stock, téléphone)
// 27.7  close  : full camera signature "On gère avec E-Maquis"
const EM = 'assets/logos/emaquis.png';
window.SPEC = {
  title: "Ton maquis perd de l'argent chaque soir",
  media: {},
  cam: { crop: [0, 0, 1080, 1920], eyes: [555, 640], splitZoom: 1 },
  cut: [],
  layout: { keys: [[0, 1160], [8.5, 0], [11.7, 1160], [27.6, 0]] },
  zoom: { keys: [[0, 1], [2.86, 1.06, 400], [8.5, 1], [10.01, 1.08, 400], [11.7, 1], [27.6, 1], [29.8, 1.08, 400]] },
  actors: [],
  scenes: [
    // 1. hook: readable on frame 0, the crates count up on "casiers"
    { type: 'board', from: 0, to: 5.6, pre: .5, items: [
      { k: 'text', text: 'Où passe', size: 110, x: 540, y: 330, at: 0, pre: .5 },
      { k: 'text', text: 'ton argent ?', emph: 'argent', emphAt: 0, size: 110, x: 540, y: 460, at: 0, pre: .5 },
      { k: 'counter', value: 20, suffix: ' casiers', size: 150, x: 540, y: 760, at: 3.40, countFrom: 3.49, countTo: 4.9 },
    ] },
    // 2. "combien d'argent est vraiment rentré dans la caisse ?"
    { type: 'board', from: 5.66, to: 8.45, items: [
      { k: 'text', text: 'Et dans', size: 120, x: 540, y: 450, at: 5.66 },
      { k: 'text', text: 'la caisse ?', emph: 'caisse', emphAt: 7.79, size: 140, x: 540, y: 620, at: 7.6 },
    ] },
    // 4. the three leaks, each struck as the next one arrives
    { type: 'board', from: 11.75, to: 17.35, items: [
      { k: 'text', text: 'Cahier perdu', size: 92, x: 540, y: 330, at: 12.93, strikeAt: 13.6 },
      { k: 'text', text: 'Bouteilles offertes', size: 84, x: 540, y: 520, at: 14.02, strikeAt: 15.2 },
      { k: 'text', text: 'Table oubliée', size: 92, x: 540, y: 710, at: 15.96, strikeAt: 16.75 },
    ] },
    // 5. not bad luck: a missing tool
    { type: 'board', from: 17.42, to: 20.15, items: [
      { k: 'text', text: 'Malchance', size: 130, x: 540, y: 400, at: 17.42, strikeAt: 18.3 },
      { k: 'text', text: "Manque d'outils.", emph: "d'outils.", emphAt: 19.53, size: 110, x: 540, y: 650, at: 19.3 },
    ] },
    // 6. the fix: E-Maquis lands, then what it does
    { type: 'board', from: 20.23, to: 27.5, items: [
      { k: 'logo', logo: EM, s: 380, x: 540, y: 330, at: 20.47 },
      { k: 'check', s: 70, x: 200, y: 580, at: 21.92 },
      { k: 'text', text: 'Chaque vente', size: 74, x: 600, y: 580, at: 21.38 },
      { k: 'check', s: 70, x: 200, y: 720, at: 23.79 },
      { k: 'text', text: 'Stock à jour', size: 74, x: 600, y: 720, at: 22.96 },
      { k: 'check', s: 70, x: 200, y: 860, at: 26.06 },
      { k: 'text', text: 'Sur ton téléphone', size: 74, x: 600, y: 860, at: 25.56 },
    ] },
  ],
  music: { bed: 'enquete', offset: 0 },
  sfx: { swish: 0, accents: 0, extra: [[13.6, 'thud', -8], [15.2, 'thud', -8], [16.75, 'thud', -8], [18.3, 'thud', -6], [20.47, 'pop', -6]] },
  captions: {
    replace: [['Emaki,', 'E-Maquis,'], ['Emaki.', 'E-Maquis.'], ['Emaki', 'E-Maquis']],
    emph: ['argent', 'caisse', 'outils', 'E-Maquis', 'feeling,'],
    hide: [],
  },
};
