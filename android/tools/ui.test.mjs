import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';

const root=fileURLToPath(new URL('../app/src/main/assets/',import.meta.url));
const artifacts=fileURLToPath(new URL('./artifacts/',import.meta.url));fs.mkdirSync(artifacts,{recursive:true});
const mime={'.html':'text/html','.js':'application/javascript','.mjs':'application/javascript','.css':'text/css','.json':'application/json','.wav':'audio/wav','.gz':'application/octet-stream'};
const server=http.createServer((req,res)=>{
  let target=path.resolve(root,'.'+decodeURIComponent(req.url.split('?')[0]));
  if(target.endsWith('.gz')&&fs.existsSync(target+'.bin'))target+='.bin';
  if(!target.startsWith(root)||!fs.existsSync(target)||!fs.statSync(target).isFile()){res.writeHead(404);res.end();return;}
  res.setHeader('Content-Type',mime[path.extname(target)]||'text/plain');
  const bytes=fs.readFileSync(target);res.setHeader('Accept-Ranges','bytes');
  const range=req.headers.range?.match(/bytes=(\d+)-(\d*)/);
  if(range){const start=+range[1],end=range[2]?Math.min(+range[2],bytes.length-1):bytes.length-1;res.writeHead(206,{'Content-Range':`bytes ${start}-${end}/${bytes.length}`,'Content-Length':end-start+1});res.end(bytes.subarray(start,end+1));}
  else{res.setHeader('Content-Length',bytes.length);res.end(bytes);}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const url=`http://127.0.0.1:${server.address().port}/web/index.html`;
const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
const page=await browser.newPage({viewport:{width:390,height:844},deviceScaleFactor:1});
const errors=[];page.on('pageerror',error=>errors.push(String(error)));
let checks=0;
function check(message,fn){fn();checks++;console.log(`PASS ${message}`);}
try{
  await page.route('**/*',route=>new URL(route.request().url()).hostname==='127.0.0.1'?route.continue():route.abort());
  await page.goto(url);await page.waitForFunction(()=>window.FollowSinger?.getState().workerReady,{},{timeout:60000});
  check('offline worker initializes all four eSpeak voices and Japanese dictionary',()=>assert.equal(errors.length,0,errors.join('\n')));
  const defaultBeginner=await page.locator('#beginner').isChecked();check('beginner is off by default',()=>assert.equal(defaultBeginner,false));
  await page.screenshot({path:path.join(artifacts,'android-home.png')});
  for(const language of ['ja','en','ru','fr','ko']){
    await page.evaluate(()=>window.FollowSinger.openSheet('library'));await page.locator(`[data-sample=${language}]`).click();
    await page.waitForFunction(lang=>window.FollowSinger.getState().language===lang&&document.querySelector('.reading')?.textContent.length>0,language);
    const reading=await page.locator('.reading').first().textContent();
    check(`${language} offline reading exists`,()=>assert.ok(reading.length>0));
    const hint=await page.locator('.hint').first().textContent();check(`${language} beginner hint exists`,()=>assert.match(hint,/[\u3400-\u9fff]/));
    if(language==='fr')check('French has real IPA symbols',()=>assert.match(reading,/[ʁʒɔɑɛəˈ]/));
    await page.locator('#beginner').check();await page.locator('#play').click();await page.waitForTimeout(180);
    assert.equal((await page.evaluate(()=>FollowSinger.getState())).playing,true);
    await page.locator('#rate').click();await page.getByRole('button',{name:'0.75×',exact:true}).click();
    await page.waitForFunction(()=>Math.abs(FollowSinger.getState().rate-.75)<.01);
    await page.locator('#play').click();await page.waitForFunction(()=>!FollowSinger.getState().playing);
    check(`${language} playback, pause and .75x work`,()=>assert.equal(errors.length,0));
    if(language==='ja'){
      const before=await page.locator('.lyric-line').first().evaluate(el=>{el.dataset.identity='stable';return el.querySelector('.reading').textContent;});
      await page.locator('#romaji').click();assert.notEqual(await page.locator('.reading').first().textContent(),before);
      assert.equal(await page.locator('.lyric-line').first().getAttribute('data-identity'),'stable');
      check('kana/romaji switch preserves existing lyric nodes',()=>assert.equal(errors.length,0));
    }
    if(language==='fr'){
      await page.locator('.lyric-line').nth(1).click();
      try{await page.waitForFunction(()=>FollowSinger.getState().currentIndex===1,{},{timeout:5000});}
      catch(error){console.log('SEEK FAILED',await page.evaluate(()=>FollowSinger.getState()));throw error;}
      await page.locator('#notice').evaluate(node=>node.hidden=true);
      console.log('French position',await page.evaluate(()=>({state:FollowSinger.getState().currentIndex,scroll:document.getElementById('lyric-viewport').scrollTop,viewport:document.getElementById('lyric-viewport').clientHeight,lines:[...document.querySelectorAll('.lyric-line')].map(n=>({top:n.offsetTop,height:n.offsetHeight,active:n.classList.contains('active')}))})));
      await page.screenshot({path:path.join(artifacts,'android-french.png')});
    }
    await page.locator('#beginner').uncheck();
  }
  // Duplicate state samples never start another scroll or replace the active DOM row.
  await page.evaluate(()=>{
    FollowSinger.setLyrics('[00:00.950]A\n[00:01.030]B\n[00:01.110]C');
    FollowSinger.updateState({position:1050,duration:3000,canSeek:true});
    window.testScrolls=0;const viewport=document.getElementById('lyric-viewport');const original=viewport.scrollTo.bind(viewport);viewport.scrollTo=(...args)=>{window.testScrolls++;original(...args);};
    for(let i=0;i<10;i++)FollowSinger.updateState({position:1050});
  });
  assert.equal(await page.evaluate(()=>window.testScrolls),0);check('duplicate samples do not repeat lyric scroll',()=>assert.equal(errors.length,0));
  await page.evaluate(()=>FollowSinger.setLyrics('[00:00.000]<img src=x onerror=alert(1)>'));
  assert.equal(await page.locator('.original img').count(),0);check('imported lyric HTML is rendered as text',()=>assert.equal(errors.length,0));
  await page.evaluate(()=>FollowSinger.openSheet('settings'));
  for(const name of ['时尚绿','护眼黄','海浪蓝','经典白','夜间黑']){
    await page.getByRole('button',{name,exact:true}).click();
    check(`${name} theme selection`,()=>assert.equal(errors.length,0));
  }
  await page.screenshot({path:path.join(artifacts,'android-night-settings.png')});
  await page.setViewportSize({width:360,height:640});await page.screenshot({path:path.join(artifacts,'android-compact.png')});
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.locator('#close-sheet').click();assert.ok(await page.locator('#play').isVisible());
  check('360x640 layout has no horizontal overflow and player remains visible',()=>assert.equal(errors.length,0));
  fs.writeFileSync(path.join(artifacts,'ui-result.json'),JSON.stringify({checks,errors},null,2));console.log(`${checks} UI checks passed`);
}finally{await browser.close();server.close();}
