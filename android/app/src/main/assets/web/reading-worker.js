// Expensive dictionary loading and conversion stay off the lyric/player UI thread.
importScripts('./vendor/kuromoji/kuromoji.js');
let engine,tokenizer,rules,hints,helpers,generation=0;
const cache=new Map();
const ready=(async()=>{
  const [module,data,helper]=await Promise.all([import('./vendor/ephone/ephone.js'),fetch('./reading-data.json').then(r=>r.json()),import('./hints.mjs')]);
  rules=data;helpers=helper;hints=helper.makeHints(rules);
  // Full offline pack includes Korean, Russian and French. English-only engines cannot do this.
  engine=await module.default(module.all);
  tokenizer=await new Promise((resolve,reject)=>self.kuromoji.builder({dicPath:'./vendor/kuromoji/dict/'}).build((err,result)=>err?reject(err):resolve(result)));
  for(const voice of ['en-US','fr','ru','ko'])engine.setVoice(voice);
  self.postMessage({type:'ready'});
})().catch(error=>{self.postMessage({type:'error',message:String(error)});throw error;});
async function reading(text,language){
  const key=`${language}\0${text}`;if(cache.has(key))return cache.get(key);
  let result;
  if(language==='ja'){
    const parts=tokenizer.tokenize(text);
    const kana=parts.map(p=>helpers.kanaToHiragana(p.reading||p.surface_form)).join(' ');
    const roman=parts.map(p=>helpers.romanizeKana(p.pronunciation||p.reading||p.surface_form,rules)).join(' ');
    result={kana,roman,reading:kana,hint:hints(helpers.romanToJapaneseIpa(roman))};
  }else{
    engine.setVoice(language==='en'?'en-US':language);
    const ipa=engine.textToIpa(text);
    let reading=`/${ipa}/`;
    if(language==='ru')reading=[...text].map(c=>{const value=rules.russian[c.toLowerCase()];return value?(c===c.toUpperCase()?value[0].toUpperCase()+value.slice(1):value):c;}).join('');
    if(language==='ko')reading=[...text].map(c=>{const code=c.codePointAt(0)-0xac00;if(code<0||code>=11172)return c;return rules.koInitial[Math.floor(code/588)]+rules.koVowel[Math.floor(code%588/28)]+rules.koFinal[code%28];}).join('');
    result={reading,hint:hints(ipa)};
  }
  if(cache.size>=2048)cache.delete(cache.keys().next().value);cache.set(key,result);return result;
}
self.onmessage=async event=>{
  const job=event.data;if(job.type!=='read')return;generation=job.generation;
  try{await ready;for(let index=0;index<job.texts.length;index++){
    if(generation!==job.generation)return;
    try{const result=await reading(job.texts[index],job.language);if(generation===job.generation)self.postMessage({type:'reading',generation,index,...result});}
    catch(error){self.postMessage({type:'line-error',generation:job.generation,index,message:String(error)});}
    // Let newer jobs supersede stale jobs while processing a long song.
    if(index%4===3)await new Promise(resolve=>setTimeout(resolve,0));
  }}catch{}
};
