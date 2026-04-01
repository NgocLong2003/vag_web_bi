<!-- _report_utils.js — Shared JS utilities
     Include SAU _report_base.css, TRƯỚC JS riêng của trang
     
     Cung cấp:
       FMT, fmtV(v), fmtD(s), fmtDF(s), iso(d)
       numH(v, cls, inv), shimH()
       esc(s), setS(status, text), toast(msg, type)
       isMobile(), isLandscapePhone()
       startResize(e, handle), startResizeTouch(e, handle)
       openSheet(type, contentFn), closeSheet()  — sheet framework
       activateHybridScroll()                     — mobile address bar trick
       exportExcelBlob(apiUrl, payload, fallbackFilename) — download helper
       
     Yêu cầu HTML:
       #sDot, #sTxt           — status chip
       #toasts                — toast container
       #sheet-overlay, #bottom-sheet, .sheet-handle, #sheet-title, #sheet-body
-->
<script>
/* ═══════════════════════════════════════
   FORMATTERS
   ═══════════════════════════════════════ */
const FMT=new Intl.NumberFormat('vi-VN',{maximumFractionDigits:0});
const fmtV=v=>FMT.format(Math.round(v));
const fmtD=function(s){if(!s)return'';s=s.substring(0,10);var p=s.split('-');return p[2]+'/'+p[1]+'/'+p[0]};
const fmtDF=fmtD; // alias
const iso=function(d){return d?String(d).substring(0,10):''};

/**
 * numH — render số thành HTML span với class pos/neg/zero
 * @param {number} v   - giá trị
 * @param {string} cls - class bổ sung (e.g. 'sub', 'grand')
 * @param {boolean} inv - inverse: dương=đỏ, âm=xanh (cho cột dư nợ)
 */
function numH(v,cls,inv){
    if(v==null)return'<span class="dash">—</span>';
    var n=Math.round(v),s;
    if(inv){s=n>0?'neg':n<0?'pos':'zero'}
    else{s=n<0?'neg':n===0?'zero':'pos'}
    return'<span class="n '+s+' '+(cls||'')+'">'+ fmtV(v)+'</span>';
}
const shimH=function(){return'<span class="sh"></span>'};

/* ═══════════════════════════════════════
   ESCAPE & STATUS
   ═══════════════════════════════════════ */
function esc(s){return s?String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'):''}
function setS(st,t){document.getElementById('sDot').className='s-dot '+st;document.getElementById('sTxt').textContent=t}
function toast(m,t){
    t=t||'ok';
    var e=document.createElement('div');
    e.className='toast '+t;
    e.innerHTML='<div class="ti">'+(t==='ok'?'✓':'✕')+'</div><span>'+m+'</span>';
    document.getElementById('toasts').appendChild(e);
    setTimeout(function(){e.remove()},3500);
}

/* ═══════════════════════════════════════
   DEVICE DETECTION
   ═══════════════════════════════════════ */
function isMobile(){
    return window.innerWidth<=768||
        (window.matchMedia&&window.matchMedia('(orientation:landscape) and (max-height:500px) and (hover:none)').matches);
}
function isLandscapePhone(){
    return window.matchMedia&&window.matchMedia('(orientation:landscape) and (max-height:500px) and (hover:none)').matches;
}

/* ═══════════════════════════════════════
   COLUMN RESIZE (mouse + touch)
   ═══════════════════════════════════════ */
function startResize(e,handle){
    e.preventDefault();e.stopPropagation();
    var th=handle.parentElement,sx=e.clientX,sw=th.offsetWidth;
    handle.classList.add('active');
    function onM(ev){var nw=Math.max(80,sw+(ev.clientX-sx))+'px';th.style.width=nw;th.style.minWidth=nw;th.style.maxWidth=nw}
    function onU(){handle.classList.remove('active');document.removeEventListener('mousemove',onM);document.removeEventListener('mouseup',onU)}
    document.addEventListener('mousemove',onM);document.addEventListener('mouseup',onU);
}
function startResizeTouch(e,handle){
    e.stopPropagation();
    var th=handle.parentElement,sx=e.touches[0].clientX,sw=th.offsetWidth;
    handle.classList.add('active');
    function onM(ev){ev.preventDefault();var nw=Math.max(80,sw+(ev.touches[0].clientX-sx))+'px';th.style.width=nw;th.style.minWidth=nw;th.style.maxWidth=nw}
    function onU(){handle.classList.remove('active');document.removeEventListener('touchmove',onM);document.removeEventListener('touchend',onU)}
    document.addEventListener('touchmove',onM,{passive:false});document.addEventListener('touchend',onU);
}

/* ═══════════════════════════════════════
   BOTTOM SHEET (framework)
   Trang gọi openSheet(title, bodyHTML) hoặc
   tự build body rồi gọi _openSheet(title, html)
   ═══════════════════════════════════════ */
function _openSheet(title,bodyHTML){
    document.getElementById('sheet-title').textContent=title;
    document.getElementById('sheet-body').innerHTML=bodyHTML;
    document.getElementById('sheet-overlay').classList.add('open');
    document.getElementById('bottom-sheet').classList.add('open');
    var mt=document.querySelector('.mob-toolbar');if(mt)mt.style.display='none';
}
function closeSheet(){
    document.getElementById('sheet-overlay').classList.remove('open');
    document.getElementById('bottom-sheet').classList.remove('open');
    var mt=document.querySelector('.mob-toolbar');if(mt)mt.style.display='';
}
/* Swipe-down to dismiss */
(function(){
    var sheet=null,startY=0,currentY=0,isDragging=false;
    document.addEventListener('DOMContentLoaded',function(){
        sheet=document.getElementById('bottom-sheet');
        if(!sheet)return;
        var handle=sheet.querySelector('.sheet-handle');
        var titleEl=sheet.querySelector('.sheet-title');
        [handle,titleEl].forEach(function(el){
            if(!el)return;
            el.addEventListener('touchstart',function(e){
                startY=e.touches[0].clientY;currentY=startY;isDragging=true;
                sheet.style.transition='none';
            },{passive:true});
        });
        document.addEventListener('touchmove',function(e){
            if(!isDragging)return;currentY=e.touches[0].clientY;
            sheet.style.transform='translateY('+Math.max(0,currentY-startY)+'px)';
        },{passive:true});
        document.addEventListener('touchend',function(){
            if(!isDragging)return;isDragging=false;sheet.style.transition='';
            if(currentY-startY>80)closeSheet();else sheet.style.transform='';
        });
    });
})();

/* ═══════════════════════════════════════
   HYBRID SCROLL (mobile address bar hide)
   ═══════════════════════════════════════ */
var _hybridActive=false,_spacerEl=null;
function activateHybridScroll(){
    var app=document.querySelector('.app');if(!app)return;
    var isTouch=window.matchMedia('(hover:none)').matches;
    var isNarrow=window.innerWidth<=768;
    var isLand=window.matchMedia('(orientation:landscape) and (max-height:500px) and (hover:none)').matches;
    if(isTouch&&(isNarrow||isLand)){
        if(_hybridActive)return;_hybridActive=true;
        document.documentElement.style.overflow='auto';document.body.style.overflow='auto';
        document.documentElement.style.height='auto';document.body.style.height='auto';
        app.classList.add('hybrid-scroll');
        if(!_spacerEl){_spacerEl=document.createElement('div');_spacerEl.className='hybrid-spacer';document.body.appendChild(_spacerEl)}
        var tw=document.querySelector('.table-wrap');
        if(tw&&!tw._hybridBound){tw._hybridBound=true;tw.addEventListener('touchstart',function(){if(window.scrollY<1)window.scrollTo(0,1)},{passive:true,once:false})}
    }else{
        if(!_hybridActive)return;_hybridActive=false;
        document.documentElement.style.overflow='hidden';document.body.style.overflow='hidden';
        document.documentElement.style.height='100%';document.body.style.height='100%';
        app.classList.remove('hybrid-scroll');
        if(_spacerEl){_spacerEl.remove();_spacerEl=null}window.scrollTo(0,0);
    }
}
var _resizeTimer=null;
window.addEventListener('resize',function(){clearTimeout(_resizeTimer);_resizeTimer=setTimeout(activateHybridScroll,300)});
window.addEventListener('orientationchange',function(){setTimeout(activateHybridScroll,300)});

/* ═══════════════════════════════════════
   EXPORT EXCEL HELPER
   POST JSON → download blob
   ═══════════════════════════════════════ */
async function exportExcelBlob(apiUrl,payload,fallbackFilename){
    var resp=await fetch(apiUrl,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    if(!resp.ok)throw new Error('Server error '+resp.status);
    var blob=await resp.blob(),url=URL.createObjectURL(blob),a=document.createElement('a');
    a.href=url;
    var cd=resp.headers.get('Content-Disposition'),fn=fallbackFilename||'export.xlsx';
    if(cd){var m=cd.match(/filename=(.+)/);if(m)fn=m[1].replace(/"/g,'')}
    a.download=fn;document.body.appendChild(a);a.click();a.remove();URL.revokeObjectURL(url);
}
</script>