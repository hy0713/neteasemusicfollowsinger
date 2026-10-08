import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {parseLrc,parseYrc,attachTranslations,activeIndex,detectLanguage,songId,matchingSong,loopBounds} from '../app/src/main/assets/web/core.mjs';
import {makeHints,kanaToHiragana,romanizeKana} from '../app/src/main/assets/web/hints.mjs';
const rules=JSON.parse(fs.readFileSync(new URL('../app/src/main/assets/web/reading-data.json',import.meta.url),'utf8'));
test('LRC handles millisecond precision, repeated tags, offsets, invalid seconds and enhanced tags',()=>{
  const result=parseLrc('[offset:-100]\n[00:01.05][00:02.120]a<00:01.2>b\n[00:99.00]invalid\n[00:03.7]c');
  assert.deepEqual(result.map(l=>[l.time,l.text]),[[950,'ab'],[2020,'ab'],[3600,'c']]);
});
test('YRC preserves real line timing without fabricated word highlighting',()=>{
  assert.deepEqual(parseYrc('[1234,800](1234,100,0)Bon(1334,200,0)jour')[0],{time:1234,text:'Bonjour',translation:''});
});
test('translation timestamp alignment consumes each translation at most once',()=>{
  const result=attachTranslations(parseLrc('[00:01]A\n[00:01.1]B'),parseLrc('[00:01.04]中文'));
  assert.equal(result[0].translation,'中文');assert.equal(result[1].translation,'');
});
test('fast 80ms lyric transitions do not select previous line for duplicate position',()=>{
  const lines=parseLrc('[00:00.950]a\n[00:01.030]b\n[00:01.110]c');
  assert.deepEqual([950,1050,1050,1130].map(p=>activeIndex(lines,p)),[0,1,1,2]);
  assert.equal(activeIndex(lines,1040,100),-1);assert.equal(activeIndex(lines,-1),-1);
});
test('all five languages are detected including unaccented French',()=>{
  assert.deepEqual(['君の歌','Hello world','Привет мир','Bonjour mon amour','안녕하세요'].map(detectLanguage),['ja','en','ru','fr','ko']);
});
test('song links accept only NetEase hosts',()=>{
  assert.equal(songId('https://music.163.com/#/song?id=333'),'333');assert.equal(songId('123'),'123');
  assert.equal(songId('https://evil.test/song?id=123'),null);assert.equal(songId('https://music.163.com.evil.test/song?id=123'),null);
});
test('automatic matching rejects same-title wrong-artist recordings',()=>{
  const songs=[{id:'1',title:'Song',artist:'Wrong',duration:30000},{id:'2',title:'Song',artist:'Artist',duration:30000}];
  assert.equal(matchingSong(songs,'Song','Artist',30000).id,'2');assert.equal(matchingSong(songs,'Different','Artist',30000),undefined);
});
test('loop bounds use offset, reject tiny remote loops, and bound last line to duration',()=>{
  const lines=parseLrc('[00:00.950]a\n[00:01.050]b');
  assert.equal(loopBounds(lines,0,0,5000,true),null);
  assert.deepEqual(loopBounds(lines,0,100,5000),{start:1050,end:1150});
  assert.deepEqual(loopBounds(lines,1,100,5000),{start:1150,end:5000});
});
test('Chinese beginner hints come from phones and keep familiar Hi convention',()=>{
  const hint=makeHints(rules);assert.equal(hint('haɪ'),'嗨');assert.ok(hint('bɔ̃ʒˈuʁ').length>0);
  assert.match(hint('həlˈoʊ'),/^[\u3400-\u9fff ·]+$/);
});
test('Japanese kana romanization handles contracted, geminated and long sounds',()=>{
  assert.equal(kanaToHiragana('キョウ'),'きょう');assert.equal(romanizeKana('キョウ',rules),'kyou');
  assert.equal(romanizeKana('ガッコウ',rules),'gakkou');assert.equal(romanizeKana('コーヒー',rules),'koohii');
});
