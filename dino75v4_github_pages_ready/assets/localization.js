/* Dino75 V4 한국어 화면 표시용. 정적 GitHub Pages에서 실행됩니다. */
(() => {
  'use strict';
  const zh = /[\u3400-\u9fff]/;
  const dictionary = window.DINO75_KO || {};
  const hidden = new Set(['SCRIPT','STYLE','TEXTAREA','NOSCRIPT','CODE','PRE']);
  const attrs = ['placeholder','title','aria-label','alt','value','data-title','data-label','data-tooltip'];
  let pending = false;

  function replacePieces(s) {
    if (!zh.test(s)) return s;
    const left = s.match(/^\s*/)?.[0] || '';
    const right = s.match(/\s*$/)?.[0] || '';
    const core = s.trim();
    if (Object.prototype.hasOwnProperty.call(dictionary, core)) return left + dictionary[core] + right;
    // 여러 중국어 라벨이 붙어 있는 경우, 길이가 긴 항목부터 부분 치환.
    let output = core;
    for (const [k, v] of Object.entries(dictionary).sort((a,b)=>b[0].length-a[0].length)) {
      if (k.length > 1 && output.includes(k)) output = output.split(k).join(v);
    }
    return left + output + right;
  }
  function scan(root) {
    if (!root || !document.documentElement) return;
    const stack = [root];
    while(stack.length){
      const n = stack.pop();
      if (n.nodeType === 3) {
        const p=n.parentElement;
        if(p && !hidden.has(p.tagName) && !p.closest('[translate="no"],[data-no-translate],[contenteditable="true"]')){
          const value=replacePieces(n.nodeValue);
          if(n.nodeValue!==value) n.nodeValue=value;
        }
      } else if(n.nodeType===1 || n.nodeType===9 || n.nodeType===11) {
        if(n.nodeType===1){
          if(hidden.has(n.tagName) || n.matches('[translate="no"],[data-no-translate]')) continue;
          for(const name of attrs){
            if(n.hasAttribute(name)){
              const a=n.getAttribute(name), b=replacePieces(a);
              if(a!==b) n.setAttribute(name,b);
            }
          }
          if(n.shadowRoot) stack.push(n.shadowRoot);
        }
        for(let c=n.lastChild;c;c=c.previousSibling) stack.push(c);
      }
    }
  }
  function schedule(){
    if(pending) return;
    pending=true;
    requestAnimationFrame(()=>{pending=false; scan(document.body);});
  }
  function start(){
    document.documentElement.lang='ko';
    document.title=replacePieces(document.title);
    scan(document.documentElement);
    new MutationObserver(schedule).observe(document.documentElement, {
      subtree:true,childList:true,characterData:true,attributes:true,
      attributeFilter:attrs
    });
    // 중국어가 번역되지 않으면 개발자도구 콘솔에서 확인할 수 있습니다.
    window.dinoKoUntranslated=()=>Array.from(document.querySelectorAll('body *'))
      .filter(e=>e.children.length===0&&zh.test(e.textContent||''))
      .map(e=>e.textContent.trim()).filter(Boolean);
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',start,{once:true});
  else start();
})();
