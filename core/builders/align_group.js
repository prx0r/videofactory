#!/usr/bin/env node
// MMS word alignment for Tantrasara groups (same engine as kashmir_audio).
// Usage: node align_group.js <wav> <words.json> <out.json> <sa-IN|en-IN>
// words.json: array of display words; folding/number-spelling applied here,
// timings map back 1:1 to display order.
const fs = require("fs");
const { execSync } = require("child_process");
const { createAligner, alignNative } = require("mms-forced-align");

const NUM = { "0": "zero", "1": "one", "2": "two", "3": "three", "4": "four", "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine", "10": "ten", "11": "eleven", "12": "twelve", "13": "thirteen", "14": "fourteen", "15": "fifteen", "16": "sixteen", "17": "seventeen", "18": "eighteen", "19": "nineteen", "20": "twenty", "30": "thirty", "40": "forty", "50": "fifty", "60": "sixty", "70": "seventy", "80": "eighty", "90": "ninety" };
function spellNum(s) {
  const n = parseInt(String(s).replace(/,/g, ""), 10);
  if (isNaN(n)) return String(s);
  if (NUM[n] !== undefined) return NUM[n];
  if (n < 100) return NUM[Math.floor(n / 10) * 10] + " " + NUM[n % 10];
  if (n < 1000) return NUM[Math.floor(n / 100)] + " hundred" + (n % 100 ? " " + spellNum(String(n % 100)) : "");
  if (n < 1000000) return spellNum(String(Math.floor(n / 1000))) + " thousand" + (n % 1000 ? " " + spellNum(String(n % 1000)) : "");
  return "number";
}
const IAST_FOLD = {ā:'a',ī:'i',ū:'u',ṛ:'r',ṝ:'r',ḷ:'l',ṃ:'m',ḥ:'h',ṅ:'n',ñ:'n',ṭ:'t',ḍ:'d',ṇ:'n',ś:'s',ṣ:'s',Ā:'A',Ī:'I',Ū:'U',Ṛ:'R',Ṃ:'M',Ḥ:'H',Ṅ:'N',Ñ:'N',Ṭ:'T',Ḍ:'D',Ṇ:'N',Ś:'S',Ṣ:'S'};
function spoken(w) {
  let f = [...w].map(c => IAST_FOLD[c] || c).join("").normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  const bare = f.replace(/[^0-9]/g, "");
  if (/^\d[\d,]*$/.test(bare)) return spellNum(bare).replace(/ /g, '-');
  if (bare && NUM[bare] !== undefined) return NUM[bare];
  return f;
}

async function main() {
  const [wav, wordsPath, outPath, lang] = process.argv.slice(2);
  const disp = JSON.parse(fs.readFileSync(wordsPath, "utf8"));
  // sa-IN takes raw Devanagari (its romanizer handles it); other langs get
  // ASCII-folded spoken forms + number spelling (house TTS_SAY doctrine).
  // timings map back 1:1 to display order either way.
  const fold = lang.startsWith("sa");
  const words = fold ? disp : disp.map(spoken);
  const f32 = "/tmp/mms_grp.f32";
  execSync(`ffmpeg -y -v error -i "${wav}" -ar 16000 -ac 1 -f f32le "${f32}"`);
  const buf = fs.readFileSync(f32);
  const waveform = new Float32Array(buf.buffer, buf.byteOffset, buf.byteLength / 4);
  const aligner = await createAligner({ quantized: false });
  const t0 = Date.now();
  const timings = await alignNative(aligner, waveform, 16000, words, lang);
  const rows = timings.map((t, i) => ({ w: disp[i], t_on: +t.start.toFixed(3), t_off: +t.end.toFixed(3), mms: +(t.score ?? 0).toFixed(3) }));
  let mono = 0;
  for (let i = 1; i < rows.length; i++) if (rows[i].t_on < rows[i - 1].t_on) mono++;
  const mean = rows.reduce((s, r) => s + r.mms, 0) / rows.length;
  console.error(`${wav.split("/").pop()}: n=${rows.length} mean=${mean.toFixed(3)} nonmono=${mono} ${(Date.now() - t0) / 1000}s`);
  fs.writeFileSync(outPath, JSON.stringify(rows));
  await aligner.dispose();
}
main().catch(e => { console.error(String(e).slice(0, 300)); process.exit(1); });
