/**
 * _report_session.js — Theo dõi phiên thao tác report
 *
 * Cách dùng:
 *   1. Include file này trong template (trước JS của report)
 *   2. Mỗi lần user thao tác mới (load trang, click Tải, thay filter...),
 *      gọi: newReportSession()
 *   3. Khi fetch API, dùng: reportFetch(url, options)
 *      thay cho fetch(url, options) — tự gắn header X-Report-Session
 *
 * Hoặc đơn giản hơn: gọi reportFetch() cho mọi API call,
 * nó tự dùng session hiện tại.
 */
(function(){
'use strict';

// Tạo UUID v4 chuẩn — không bao giờ trùng
function genId(){
  if(crypto&&crypto.randomUUID)return crypto.randomUUID();
  // Fallback cho browser cũ
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g,function(c){
    var r=Math.random()*16|0;return(c==='x'?r:r&0x3|0x8).toString(16);
  });
}

// Session hiện tại
var _sid = genId();

/**
 * Tạo session mới — gọi mỗi khi user thao tác load/reload data
 * Return session id nếu cần
 */
window.newReportSession = function(){
  _sid = genId();
  return _sid;
};

/**
 * Lấy session id hiện tại
 */
window.getReportSession = function(){
  return _sid;
};

/**
 * fetch() wrapper tự gắn X-Report-Session header
 * Dùng y hệt fetch(): reportFetch(url, options)
 */
window.reportFetch = function(url, options){
  options = options || {};
  options.headers = options.headers || {};
  options.headers['X-Report-Session'] = _sid;
  return fetch(url, options);
};

})();