export function makeHints(rules) {
  const vowels=new Set(rules.vowels),extra=new Set(['tɕ','tɕʰ','dʑ','ts','dz','ɲ','ɸ','ʂ','ʈʂ']);
  function tokens(value) {
    value=value.replaceAll('g','ɡ').replaceAll('ɐ','a').replaceAll('ɯ','u');
    for(const [source,replacement] of Object.entries(rules.nasals))value=value.replaceAll(source,replacement);
    value=value.normalize('NFD').replace(/[ˈˌːˑʲ̩̃͜͡\p{M}]/gu,'');
    const result=[];while(value.length){const symbol=rules.multi.find(part=>value.startsWith(part))||[...value][0];result.push(symbol);value=value.slice(symbol.length);}return result;
  }
  function distance(a,b) {
    if(a===b)return 0;if((a==='ʒ'&&b==='ʐ')||(a==='ʐ'&&b==='ʒ'))return .15;
    if(vowels.has(a[0])&&vowels.has(b[0])&&(a.length>1||b.length>1))return distance(a[0],b[0])+.4*Math.abs(a.length-b.length);
    if(rules.neighbors.some(group=>group.includes(a)&&group.includes(b)))return .35;
    if(vowels.has(a[0])&&vowels.has(b[0])){
      const pos={i:[0,1],ɪ:[.2,.85],e:[.4,1],ɛ:[.6,1],æ:[.8,1],a:[1,.5],ɑ:[1,0],ɒ:[.9,0],o:[.4,0],ɔ:[.6,0],u:[0,0],ʊ:[.2,.1],y:[0,.8],ø:[.4,.7],œ:[.6,.7],ʌ:[.7,.3]};
      const x=pos[a]||[.5,.5],y=pos[b]||[.5,.5];return .3+Math.abs(x[0]-y[0])+.7*Math.abs(x[1]-y[1]);
    }
    const affricates=['tʃ','dʒ','tɕ','dʑ','ʈʂ'];if(affricates.includes(a)&&affricates.includes(b))return .4;return 1.6;
  }
  function edit(source,target){let previous=target.map((_,i)=>(i+1)*1.4);previous.unshift(0);for(let i=0;i<source.length;i++){
    const current=[(i+1)*1.4];for(let j=0;j<target.length;j++)current.push(Math.min(previous[j+1]+1.4,current[j]+1.4,previous[j]+distance(source[i],target[j])));previous=current;}return previous.at(-1);}
  const cache=new Map();
  function nearest(syllable){const key=syllable.join('|');if(cache.has(key))return cache.get(key);
    const familiar={'k|o|n':'空','w|ɜ':'沃','t|w|a':'图哇'};let character=familiar[key];
    if(!character){let score=Infinity;for(const [sound,char] of rules.candidates){const next=edit(syllable,sound);if(next<score){score=next;character=char;}}}
    cache.set(key,character);return character;
  }
  return phonemes=>{
    const result=[];
    for(const word of phonemes.split(/[\s·,;.!?，。！？]+/)){
      const sounds=tokens(word.replaceAll('-','')).filter(s=>vowels.has(s[0])||rules.isolated[s]||extra.has(s));
      const pieces=[];let cursor=0;
      while(cursor<sounds.length){let nucleus=-1;for(let i=cursor;i<sounds.length;i++)if(vowels.has(sounds[i][0])){nucleus=i;break;}
        if(nucleus<0){pieces.push(...sounds.slice(cursor).map(s=>rules.isolated[s]||''));break;}
        const onset=sounds.slice(cursor,nucleus),keep=onset.length>=2&&['j','w'].includes(onset.at(-1))?2:1;
        pieces.push(...onset.slice(0,Math.max(0,onset.length-keep)).map(s=>rules.isolated[s]||''));
        const syllable=[...onset.slice(-keep),sounds[nucleus]];cursor=nucleus+1;
        if(cursor<sounds.length&&['n','ŋ','m'].includes(sounds[cursor])&&(cursor+1===sounds.length||!vowels.has(sounds[cursor+1][0]))){syllable.push(sounds[cursor]==='m'?'n':sounds[cursor]);cursor++;}
        pieces.push(nearest(syllable));
      }
      if(pieces.length)result.push(pieces.join(''));
    }
    return result.join(' · ');
  };
}
export function kanaToHiragana(text){return [...text].map(c=>{const n=c.codePointAt(0);return n>=0x30a1&&n<=0x30f6?String.fromCodePoint(n-0x60):c;}).join('');}
export function romanizeKana(text,rules){
  text=kanaToHiragana(text);let result='';
  for(let i=0;i<text.length;i++){
    const char=text[i],pair=text.slice(i,i+2);
    if(char==='っ'){const next=rules.kana[text.slice(i+1,i+3)]||rules.kana[text[i+1]]||'';result+=next.startsWith('ch')?'t':next[0]||'';continue;}
    if(char==='ー'){result+=result.match(/[aeiou][^aeiou]*$/)?.[0]?.[0]||'';continue;}
    if(rules.kana[pair]){result+=rules.kana[pair];i++;}else result+=rules.kana[char]||char;
  }
  return result;
}
export function romanToJapaneseIpa(value){
  const rules={shi:'ɕi',chi:'tɕʰi',tsu:'tsu',fu:'ɸu',ji:'dʑi',sha:'ɕa',shu:'ɕu',sho:'ɕo',cha:'tɕa',chu:'tɕu',cho:'tɕo',ja:'dʑa',ju:'dʑu',jo:'dʑo'};
  value=value.toLowerCase();for(const [from,to] of Object.entries(rules))value=value.replaceAll(from,to);
  return value.replace(/([ktsp])\1/g,'$1').replaceAll('y','j').replaceAll('r','ɾ');
}
