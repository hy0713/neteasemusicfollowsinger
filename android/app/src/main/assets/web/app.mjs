import {languages,themes,parseLrc,parseYrc,attachTranslations,activeIndex,detectLanguage,songId,matchingSong,loopBounds,timeLabel} from './core.mjs';

const $=id=>document.getElementById(id);
let saved={}; try {saved=JSON.parse(localStorage.getItem('preferences')||'{}')}catch{}
const prefs={theme:themes[saved.theme]?saved.theme:'经典白',language: saved.language==='auto'||languages[saved.language]?saved.language:'auto',
  romaji:!!saved.romaji,beginner:!!saved.beginner,reading:saved.reading!==false,translation:saved.translation!==false,
  size:Number.isFinite(saved.size)?Math.max(20,Math.min(36,saved.size)):27,offset:0};
let lines=[], readings=[], currentLanguage='en', currentIndex=-1, readingGeneration=0, requestSerial=0, pendingRequest=null;
let following=true, dragging=false, mode='local', sheetType='', state={position:0,duration:0,playing:false,canPlay:false,canSeek:false,canRate:false,loop:false,rate:1};
let remoteTrack=null, noticeTimer=0, lastProblem='', localTitle='选择一首歌，开始跟唱';
const worker=new Worker('./reading-worker.js');
let workerReady=false, workerProblem='';

function notice(message, milliseconds=4500) { $('notice').textContent=message; $('notice').hidden=false; clearTimeout(noticeTimer); noticeTimer=setTimeout(()=>$('notice').hidden=true,milliseconds); }
function persist() { try {localStorage.setItem('preferences',JSON.stringify(prefs))}catch{} }
function command(action,extra={}) {
  if(window.Android) Android.postMessage(JSON.stringify({action,...extra}));
  else previewCommand(action,extra);
}
function theme(name) {
  prefs.theme=name; const values=themes[name];
  ['bg','surface','text','accent','selected','muted','border'].forEach((key,i)=>document.documentElement.style.setProperty(`--${key}`,values[i]));
  document.documentElement.style.colorScheme=name==='夜间黑'?'dark':'light';
  command('theme',{dark:name==='夜间黑',background:values[0]});persist();
}
function preserveAnchor(change) {
  const viewport=$('lyric-viewport');
  const anchor=[...$('lyrics').children].find(node=>node.offsetTop+node.offsetHeight>=viewport.scrollTop);
  const top=anchor?.offsetTop;
  change();
  if(anchor && top!==undefined) viewport.scrollTop+=anchor.offsetTop-top;
}
function displayPreferences() {
  $('beginner').checked=prefs.beginner; $('language').value=prefs.language;
  preserveAnchor(()=>{
    $('lyrics').classList.toggle('no-reading',!prefs.reading);
    $('lyrics').classList.toggle('no-translation',!prefs.translation);
    $('lyrics').classList.toggle('no-beginner',!prefs.beginner);
    document.documentElement.style.setProperty('--font-size',`${prefs.size}px`);
  });
  $('japanese-switch').hidden=currentLanguage!=='ja'; $('reading-kind').hidden=currentLanguage==='ja';
  $('reading-kind').textContent=['fr','en'].includes(currentLanguage)?'国际音标 IPA':'本地转写';
  $('kana').classList.toggle('selected',!prefs.romaji);$('romaji').classList.toggle('selected',prefs.romaji);
  $('language-caption').textContent=lines.length?`${languages[currentLanguage]} · ${prefs.beginner?'新手谐音 + 原读音':'本地读音'}${prefs.offset?` · 延迟 ${prefs.offset>0?'+':''}${(prefs.offset/1000).toFixed(1)}s`:''}`:'五种语言 · 跟唱练习';
  persist();
}
function setBeginner(value) {prefs.beginner=value;displayPreferences(); if($('setting-beginner'))$('setting-beginner').checked=value;}
function clearLoop() {command('loop',{start:-1,end:-1});state.loop=false;$('loop').classList.remove('selected');}
function setLyrics(original,translated='',yrc='') {
  const parsed=parseLrc(original); const next=parsed.length?parsed:parseYrc(yrc);
  if(!next.length){notice('没有可用的逐行歌词，请导入带时间标签的 LRC');return false;}
  clearLoop(); lines=attachTranslations(next,parseLrc(translated)); prefs.offset=0;
  readings=[];currentIndex=-1;following=true;$('resume-follow').hidden=true;
  currentLanguage=prefs.language==='auto'?detectLanguage(lines.map(l=>l.text).join(' ')):prefs.language;
  renderLyrics(); displayPreferences();requestReadings();updateState(state);return true;
}
function clearLyrics() {
  clearLoop();lines=[];readings=[];currentIndex=-1;readingGeneration++;$('lyrics').replaceChildren();$('empty').hidden=false;$('line-count').textContent='';
  $('resume-follow').hidden=true; following=true; displayPreferences();
}
function renderLyrics() {
  const fragment=document.createDocumentFragment();
  lines.forEach((line,i)=>{
    const node=document.createElement('article');node.className='lyric-line';node.dataset.index=i;node.tabIndex=0;node.setAttribute('role','button');node.setAttribute('aria-label',`第 ${i+1} 句：${line.text}`);
    for(const name of ['reading','hint','original','translation']) {const div=document.createElement('div');div.className=name;div.textContent=name==='original'?line.text:name==='translation'?line.translation:'';node.append(div);}
    const seek=()=>{if(!state.canSeek){notice('当前没有可定位的音频时间轴');return;}following=true;$('resume-follow').hidden=true;command('seek',{position:Math.max(0,line.time+prefs.offset)});};
    node.addEventListener('click',seek);node.addEventListener('keydown',e=>{if(e.key==='Enter')seek();});fragment.append(node);
  });
  $('lyrics').replaceChildren(fragment);$('empty').hidden=!!lines.length;$('line-count').textContent=lines.length?`— / ${lines.length}`:'';
  $('lyric-viewport').scrollTop=0;
}
function requestReadings() {
  const generation=++readingGeneration;
  readings=[];
  if(!workerReady){ if(workerProblem)notice(workerProblem); return; }
  worker.postMessage({type:'read',generation,language:currentLanguage,texts:lines.map(l=>l.text)});
}
function showReadings(index) {
  const node=$('lyrics').children[index], result=readings[index]; if(!node || !result)return;
  preserveAnchor(()=>{
    node.querySelector('.reading').textContent=currentLanguage==='ja'?(prefs.romaji?result.roman:result.kana):result.reading;
    node.querySelector('.hint').textContent=result.hint;
  });
}
worker.onmessage=event=>{
  const message=event.data;
  if(message.type==='ready'){workerReady=true;if(lines.length)requestReadings();return;}
  if(message.type==='error'){workerProblem='离线读音加载失败，请重新打开应用';notice(workerProblem);return;}
  if(message.generation!==readingGeneration)return;
  if(message.type==='reading'){readings[message.index]=message;showReadings(message.index);}
  if(message.type==='line-error'){notice(`部分读音转换失败：${message.message}`);}
};
worker.onerror=()=>{workerProblem='离线词典未能加载，请重新打开应用';notice(workerProblem);};
function scrollToActive() {
  const node=$('lyrics').children[currentIndex];if(!node)return;
  const viewport=$('lyric-viewport');
  // One scroll per actual line change. No competing smooth-scroll animations.
  viewport.scrollTo({top:Math.max(0,node.offsetTop-viewport.clientHeight*.42+node.clientHeight/2),behavior:'instant'});
}
function updateActive(force=false) {
  const next=activeIndex(lines,state.position,prefs.offset);
  if(next!==currentIndex){
    $('lyrics').children[currentIndex]?.classList.remove('active');currentIndex=next;
    $('lyrics').children[currentIndex]?.classList.add('active');
    $('line-count').textContent=lines.length?`${Math.max(0,next+1)} / ${lines.length}`:'';
    if(following)scrollToActive();
  } else if(force && following)scrollToActive();
}
function updateState(message) {
  state={...state,...message};mode=state.mode||mode;
  $('source-chip').textContent=mode==='netease'?'网易云同步 ▾':'本地练习 ▾';
  $('play').disabled=!state.canPlay;$('play').textContent=state.playing?'Ⅱ':'▶';$('play').setAttribute('aria-label',state.playing?'暂停':'播放');
  $('rate').disabled=!state.canRate;$('rate').querySelector('b').textContent=`${Number(state.rate||1).toFixed(2).replace(/0$/,'')}×`;
  $('progress').disabled=!state.canSeek;$('loop').disabled=!state.canSeek||!lines.length;
  $('loop').classList.toggle('selected',!!state.loop);
  $('previous').disabled=!state.canSeek||!lines.length;$('next').disabled=!state.canSeek||!lines.length;
  $('duration').textContent=timeLabel(state.duration);
  if(!dragging){$('elapsed').textContent=state.position<0?'—:—':timeLabel(state.position);$('progress').value=state.duration>0?String(Math.round(state.position/state.duration*1000)):'0';}
  $('timeline-note').textContent=mode==='netease'&&!state.canSeek?'网易云未提供定位能力':state.loop?'正在单句循环':prefs.offset?`歌词延迟 ${(prefs.offset/1000).toFixed(1)}s`:'点击歌词可跳转';
  if(state.title)$('song-title').textContent=state.title;
  $('song-artist').textContent=mode==='netease'?(state.artist||'网易云音乐'):(lines.length?`${languages[currentLanguage]} · ${lines.length} 句练习歌词`:'本地音频 · 导入歌词开始练习');
  $('connection').querySelector('span').textContent=mode==='netease'?(state.ready?'网易云已连接 · 本地读音':state.access?'等待网易云播放':'需要通知使用权'):(state.ready?'本地播放器 · 离线读音':'本地练习 · 离线读音');
  if(state.problem && state.problem!==lastProblem){lastProblem=state.problem;notice(state.problem);}
  updateActive();
}
function request(action,extra={}) {const id=++requestSerial;pendingRequest={action,id,...extra};command(action,{request:id,...extra});return id;}
function loadSong(song) {
  request('lyrics',{id:song.id});
  if(mode==='local'){$('song-title').textContent=localTitle;}
  notice('正在获取逐行歌词…');
}
function songResults(songs) {
  let container=$('search-results');
  if(!container){openSheet('library');container=$('search-results');}
  container.replaceChildren();
  if(!songs.length){container.textContent='没有找到歌曲，可以导入本地 LRC。';return;}
  songs.forEach(song=>{
    const button=document.createElement('button');button.className='search-result';
    const title=document.createElement('strong');title.textContent=song.title;
    const info=document.createElement('small');info.textContent=`${song.artist} · ${timeLabel(song.duration)}`;button.append(title,info);
    button.onclick=()=>loadSong(song);container.append(button);
  });
}
window.receiveNative=message=>{
  switch(message.type){
    case 'state':updateState(message);break;
    case 'status':notice(message.message);break;
    case 'audio':
      remoteTrack=null;pendingRequest=null;requestSerial++;mode='local';localTitle=message.name;clearLyrics();
      state={position:0,duration:0,playing:false,canPlay:false,canSeek:false,canRate:false,loop:false,rate:1,mode:'local',title:message.name};updateState(state);closeSheet();notice('音频已打开，请导入对应的 LRC 歌词');break;
    case 'sample':
      remoteTrack=null;pendingRequest=null;requestSerial++;mode='local';prefs.language=message.language;localTitle=`${languages[message.language]} · 五语练习`;
      state={position:0,duration:0,playing:false,canPlay:false,canSeek:false,canRate:false,loop:false,rate:1,mode:'local',title:localTitle};
      $('cover-label').textContent={ja:'あ',en:'Aa',ru:'Я',fr:'é',ko:'한'}[message.language];
      setLyrics(message.original,message.translation);closeSheet();notice('示例使用合成提示音，适合体验歌词与读音');break;
    case 'import':
      pendingRequest=null;requestSerial++;
      if(message.kind==='translation'){
        if(!lines.length){notice('请先导入原文歌词');break;}
        const translated=attachTranslations(lines,parseLrc(message.text));
        lines=translated; preserveAnchor(()=>[...$('lyrics').children].forEach((node,i)=>node.querySelector('.translation').textContent=lines[i].translation));
        closeSheet();notice('中文译文已导入');
      }else if(setLyrics(message.text)){closeSheet();notice('歌词已导入');}
      break;
    case 'track':
      remoteTrack={...message};clearLyrics();pendingRequest=null;requestSerial++;
      request('search',{query:`${message.title} ${message.artist}`,automatic:true});break;
    case 'search':
      if(message.request!==pendingRequest?.id)break;
      if(pendingRequest.automatic && remoteTrack){
        const match=matchingSong(message.songs,remoteTrack.title,remoteTrack.artist,remoteTrack.duration);
        if(match)loadSong(match);else{songResults(message.songs);notice('未找到明确匹配，请选择对应的歌词版本');}
      }else songResults(message.songs);
      break;
    case 'lyrics':
      if(message.request!==pendingRequest?.id)break;
      if(setLyrics(message.original,message.translation,message.yrc)){closeSheet();notice('歌词已加载，读音在本地转换');}
      pendingRequest=null;break;
    case 'error':
      if(message.request!==pendingRequest?.id)break;
      pendingRequest=null;notice(message.message,7000);if($('search-results'))$('search-results').textContent=message.message;break;
  }
};
function changeMode(value){
  if(value===mode)return;
  clearLyrics();pendingRequest=null;requestSerial++;remoteTrack=null;mode=value;
  state={position:0,duration:0,playing:false,canPlay:false,canSeek:false,canRate:false,loop:false,rate:1,mode};updateState(state);
  command('mode',{value}); if(value==='netease')notice('请在网易云播放歌曲，并开启通知使用权');
  document.querySelectorAll('[data-mode]').forEach(b=>b.classList.toggle('selected',b.dataset.mode===mode));
}
function searchSubmit(event){
  event.preventDefault();const query=$('search-query').value.trim();if(!query)return;
  $('search-query').blur();const id=songId(query);
  if(id)loadSong({id});else{$('search-results').textContent='正在搜索…';request('search',{query});}
}
function openSheet(type){
  sheetType=type;$('sheet-backdrop').hidden=false;$('sheet-body').replaceChildren();
  $('sheet-title').textContent={library:'曲库与音源',settings:'显示与皮肤',rate:'播放速度',licenses:'开源许可证'}[type];
  document.querySelectorAll('.bottom-nav button').forEach(b=>b.classList.remove('active'));
  $(type==='settings'?'settings-tab':type==='library'?'library-tab':'practice-tab').classList.add('active');
  if(type==='library'){
    $('sheet-body').append($('library-template').content.cloneNode(true));
    document.querySelectorAll('[data-mode]').forEach(b=>{b.classList.toggle('selected',b.dataset.mode===mode);b.onclick=()=>changeMode(b.dataset.mode);});
    document.querySelectorAll('[data-pick]').forEach(b=>b.onclick=()=>command('pick',{kind:b.dataset.pick}));
    document.querySelectorAll('[data-sample]').forEach(b=>b.onclick=()=>command('sample',{language:b.dataset.sample}));
    $('search-form').onsubmit=searchSubmit;$('grant-access').onclick=()=>{changeMode('netease');command('permission');};
  }else if(type==='settings'){
    $('sheet-body').append($('settings-template').content.cloneNode(true));
    for(const name of Object.keys(themes)){
      const button=document.createElement('button');button.className='theme-choice';button.classList.toggle('selected',name===prefs.theme);
      const dot=document.createElement('span');dot.className='theme-swatch';dot.style.background=themes[name][0];dot.style.boxShadow=`inset -7px -7px ${themes[name][3]}`;
      button.append(dot,document.createTextNode(name));button.onclick=()=>{theme(name);document.querySelectorAll('.theme-choice').forEach(b=>b.classList.toggle('selected',b===button));};$('theme-list').append(button);
    }
    $('show-reading').checked=prefs.reading;$('show-translation').checked=prefs.translation;$('setting-beginner').checked=prefs.beginner;
    $('show-reading').onchange=e=>{prefs.reading=e.target.checked;displayPreferences();};
    $('show-translation').onchange=e=>{prefs.translation=e.target.checked;displayPreferences();};
    $('setting-beginner').onchange=e=>setBeginner(e.target.checked);
    $('font-size').value=prefs.size;$('size-value').textContent=`${prefs.size}px`;
    $('font-size').oninput=e=>{prefs.size=+e.target.value;$('size-value').textContent=`${prefs.size}px`;displayPreferences();};
    const offset=value=>{prefs.offset=Math.max(-10000,Math.min(10000,value));clearLoop();$('offset-value').textContent=`${prefs.offset>0?'+':''}${(prefs.offset/1000).toFixed(1)} 秒`;displayPreferences();updateActive(true);};
    $('offset-minus').onclick=()=>offset(prefs.offset-100);$('offset-plus').onclick=()=>offset(prefs.offset+100);$('offset-reset').onclick=()=>offset(0);
    $('offset-value').textContent=`${(prefs.offset/1000).toFixed(1)} 秒`;$('licenses').onclick=()=>openSheet('licenses');
  }else if(type==='rate'){
    const grid=document.createElement('div');grid.className='rate-grid';
    for(const rate of [.5,.75,1,1.25,1.5]){
      const button=document.createElement('button');button.className='rate-choice';button.classList.toggle('selected',Math.abs(rate-state.rate)<.01);button.textContent=`${rate}×`;
      button.onclick=()=>{command('rate',{value:rate});closeSheet();if(mode==='netease')notice('已请求倍速，以网易云实际回传为准');};grid.append(button);
    }$('sheet-body').append(grid);
  }else if(type==='licenses'){
    const p=document.createElement('p');p.className='muted';p.textContent='跟唱伴学：GPL-3.0-only。读音引擎 ephone 1.0.2 / eSpeak NG：GPL-3.0-or-later；kuromoji.js 0.1.2：Apache-2.0，IPADIC 使用 NAIST 许可。所有词库随 APK 离线提供。源码与对应引擎源码位于项目 android/ 与 vendor/。';$('sheet-body').append(p);
    for(const [label,path] of [['应用 GPL-3.0','../LICENSE'],['ephone / eSpeak NG','../licenses/ephone-GPL-3.txt'],['kuromoji Apache-2.0','../licenses/LICENSE-2.0.txt'],['IPADIC 声明','../licenses/kuromoji-NOTICE.md']]){
      const details=document.createElement('details'),summary=document.createElement('summary'),pre=document.createElement('pre');summary.textContent=label;details.append(summary,pre);$('sheet-body').append(details);
      fetch(path).then(r=>{if(!r.ok)throw Error();return r.text();}).then(t=>pre.textContent=t).catch(()=>pre.textContent='许可证见项目 android/app/src/main/assets/licenses/');
    }
  }
}
window.closeSheet=function(){if($('sheet-backdrop').hidden)return false;$('sheet-backdrop').hidden=true;sheetType='';document.querySelectorAll('.bottom-nav button').forEach(b=>b.classList.toggle('active',b.id==='practice-tab'));return true;};
function closeSheet(){return window.closeSheet();}
$('close-sheet').onclick=closeSheet;$('sheet-backdrop').onclick=e=>{if(e.target===$('sheet-backdrop'))closeSheet();};
$('source-chip').onclick=$('open-library').onclick=$('library-tab').onclick=()=>openSheet('library');
$('settings-tab').onclick=()=>openSheet('settings');$('practice-tab').onclick=closeSheet;
$('try-sample').onclick=()=>command('sample',{language:'fr'});
$('play').onclick=()=>command('toggle');$('rate').onclick=()=>openSheet('rate');
$('beginner').onchange=e=>setBeginner(e.target.checked);
$('language').onchange=e=>{prefs.language=e.target.value;currentLanguage=prefs.language==='auto'?detectLanguage(lines.map(l=>l.text).join(' ')):prefs.language;displayPreferences();requestReadings();};
for(const [id,value] of [['kana',false],['romaji',true]])$(id).onclick=()=>{prefs.romaji=value;displayPreferences();readings.forEach((_,i)=>showReadings(i));};
$('previous').onclick=()=>command('seek',{position:Math.max(0,lines[Math.max(0,currentIndex-1)]?.time+prefs.offset||0)});
$('next').onclick=()=>command('seek',{position:Math.max(0,lines[Math.min(lines.length-1,currentIndex+1)]?.time+prefs.offset||0)});
$('loop').onclick=()=>{
  if(state.loop){clearLoop();return;}
  const bounds=loopBounds(lines,currentIndex,prefs.offset,state.duration,mode==='netease');
  if(!bounds){notice(currentIndex<0?'请先播放到或点击想练习的一句':'这句太短或没有有效结束时间，无法循环');return;}
  command('loop',bounds);command('seek',{position:bounds.start});
};
$('progress').addEventListener('pointerdown',()=>dragging=true);
$('progress').oninput=()=>{dragging=true;$('elapsed').textContent=timeLabel(state.duration*+$('progress').value/1000);};
$('progress').onchange=()=>{command('seek',{position:Math.round(state.duration*+$('progress').value/1000)});dragging=false;following=true;$('resume-follow').hidden=true;};
$('progress').addEventListener('pointercancel',()=>dragging=false);
$('lyric-viewport').addEventListener('pointerdown',()=>{if(lines.length){following=false;$('resume-follow').hidden=false;}});
$('lyric-viewport').addEventListener('wheel',()=>{if(lines.length){following=false;$('resume-follow').hidden=false;}},{passive:true});
$('resume-follow').onclick=()=>{following=true;$('resume-follow').hidden=true;scrollToActive();};
document.addEventListener('keydown',e=>{
  if(e.key==='Escape'){closeSheet();return;}
  if(e.code==='Space'&&!['INPUT','SELECT','TEXTAREA','BUTTON'].includes(document.activeElement?.tagName)){e.preventDefault();if(state.canPlay)command('toggle');}
});

// A browser preview uses the same UI and bundled audio; installed APK uses native playback.
let previewAudio=null, previewLoop=null;
async function previewCommand(action,data){
  if(action==='sample'){
    const [original,translation]=await Promise.all([fetch(`../samples/${data.language}.lrc`).then(r=>r.text()),fetch(`../samples/${data.language}.zh.lrc`).then(r=>r.text())]);
    previewAudio?.pause();previewAudio=new Audio('../samples/practice.wav');previewAudio.preload='auto';previewLoop=null;
    window.receiveNative({type:'sample',language:data.language,original,translation});
    previewAudio.addEventListener('loadedmetadata',()=>previewTick());
  }else if(action==='toggle'&&previewAudio){if(previewAudio.paused)await previewAudio.play();else previewAudio.pause();}
  else if(action==='seek'&&previewAudio)previewAudio.currentTime=Math.min(previewAudio.duration||0,data.position/1000);
  else if(action==='rate'&&previewAudio)previewAudio.playbackRate=data.value;
  else if(action==='loop')previewLoop=data.start>=0?data:null;
  else if(action==='mode'){previewAudio?.pause();}
  else if(['search','lyrics','pick','permission'].includes(action))notice('此功能使用 Android 原生接口，请在 APK 中使用');
}
function previewTick(){if(!previewAudio || mode!=='local')return;if(previewLoop&&!previewAudio.paused&&previewAudio.currentTime*1000>=previewLoop.end)previewAudio.currentTime=previewLoop.start/1000;
  updateState({mode:'local',position:Math.round(previewAudio.currentTime*1000),duration:Math.round((previewAudio.duration||0)*1000),playing:!previewAudio.paused,ready:previewAudio.readyState>=1,canPlay:previewAudio.readyState>=1,canSeek:previewAudio.readyState>=1,canRate:previewAudio.readyState>=1,rate:previewAudio.playbackRate,loop:!!previewLoop,title:localTitle});}
if(!window.Android)setInterval(previewTick,80);
command('ready');theme(prefs.theme);displayPreferences();updateState(state);
// Stable automation hooks also help reproduce lyric boundary regressions in the browser.
window.FollowSinger={getState:()=>({...state,currentIndex,language:currentLanguage,workerReady,prefs:{...prefs},lines:[...lines]}),setLyrics,updateState,openSheet};
