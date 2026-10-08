export const languages = {ja:'日语', en:'英语', ru:'俄语', fr:'法语', ko:'韩语'};
export const themes = {
  '时尚绿':['#fbfbf8','#f0f1e9','#35433e','#456c5d','#e6eddf','#78877c','#dce2d7'],
  '护眼黄':['#faf3df','#eee3c7','#514735','#92713d','#eee0b9','#84745b','#d9cbae'],
  '海浪蓝':['#f3f8fc','#e4eef7','#28445b','#337ba8','#dcecf8','#64839c','#c8d9e7'],
  '经典白':['#ffffff','#f2f3f5','#30343b','#56647a','#e9edf3','#727985','#dce0e6'],
  '夜间黑':['#191c22','#22262e','#e2e6ed','#8aa8d8','#2d3c52','#a0aaba','#39414e']
};
export function parseLrc(content) {
  const offset = Number(content.match(/\[offset:\s*([+-]?\d+)\]/i)?.[1] || 0), lines = [];
  for (const raw of content.split(/\r?\n/)) {
    const tags = [...raw.matchAll(/\[(\d{1,3}):(\d{2})(?:[.:](\d{1,3}))?\]/g)];
    if (!tags.length) continue;
    const last = tags.at(-1);
    const text = raw.slice(last.index + last[0].length).replace(/<\d{1,3}:\d{2}(?:[.:]\d{1,3})?>/g,'').trim();
    if (!text) continue;
    for (const tag of tags) {
      if (+tag[2] >= 60) continue;
      lines.push({time:Math.max(0,(+tag[1]*60 + +tag[2])*1000 + +((tag[3]||'').padEnd(3,'0')) + offset),text,translation:''});
    }
  }
  return lines.sort((a,b)=>a.time-b.time);
}
export function parseYrc(content) {
  return content.split(/\r?\n/).flatMap(raw=>{
    const m=raw.trim().match(/^\[(\d+),\d+\](.*)$/);
    if (!m) return [];
    const text=m[2].replace(/\(\d+,\d+(?:,\d+)?\)/g,'').trim();
    return text ? [{time:+m[1],text,translation:''}] : [];
  }).sort((a,b)=>a.time-b.time);
}
export function attachTranslations(lines, translations) {
  const remaining=new Set(translations.map((_,i)=>i));
  return lines.map(line=>{
    let selected=-1, distance=601;
    for (const i of remaining) {
      const delta=Math.abs(line.time-translations[i].time);
      if (delta<distance) {selected=i; distance=delta;}
    }
    if (selected<0) return {...line,translation:''};
    remaining.delete(selected);
    return {...line,translation:translations[selected].text};
  });
}
export function activeIndex(lines, position, offset=0) {
  if (position<0) return -1;
  let low=0,high=lines.length;
  while(low<high) { const mid=(low+high)>>1; if(lines[mid].time<=position-offset) low=mid+1; else high=mid; }
  return low-1;
}
export function detectLanguage(text) {
  if (/[\uac00-\ud7af]/.test(text)) return 'ko';
  if (/[\u0400-\u04ff]/.test(text)) return 'ru';
  if (/[\u3040-\u30ff\u3400-\u9fff]/.test(text)) return 'ja';
  if (/[àâæçéèêëîïôœùûüÿ]/i.test(text)) return 'fr';
  const words=new Set(text.toLowerCase().match(/[a-z]+/g)||[]);
  if (['bonjour','bonsoir','chanson','amour','coeur','toujours','pourquoi','jamais','avec','veux','chante'].some(w=>words.has(w)) ||
      ['je','tu','nous','vous','toi','moi','une','les','des','est','dans','pas','mon','mes','pour','que','qui'].filter(w=>words.has(w)).length>=2) return 'fr';
  return 'en';
}
export function songId(value) {
  value=value.trim();
  if (/^\d{1,20}$/.test(value)) return value;
  try {
    const url=new URL(value);
    if (!['music.163.com','y.music.163.com'].includes(url.hostname)) return null;
    return value.match(/(?:^|[?&#])id=(\d{1,20})(?:\D|$)/)?.[1]||null;
  } catch { return null; }
}
export function matchingSong(songs, title, artist, duration) {
  const normal=s=>s.toLowerCase().replace(/[\p{P}\p{Z}\p{S}_]/gu,'');
  return songs.find(s=>normal(s.title)===normal(title) && (!artist || normal(s.artist).includes(normal(artist.split('/')[0]))) &&
    (!duration || !s.duration || Math.abs(s.duration-duration)<15000));
}
export function loopBounds(lines,index,offset,duration,remote=false) {
  if(index<0 || index>=lines.length || duration<=0) return null;
  const start=Math.max(0,lines[index].time+offset), end=Math.min(duration,(lines[index+1]?.time??duration-offset)+offset);
  return end-start>=(remote?800:100) ? {start,end} : null;
}
export function timeLabel(ms) { ms=Math.max(0,ms); return `${Math.floor(ms/60000)}:${String(Math.floor(ms/1000)%60).padStart(2,'0')}`; }
