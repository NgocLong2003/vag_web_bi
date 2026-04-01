<!-- _report_permissions.js — Shared permission logic
     
     TRƯỚC KHI INCLUDE, trang cần define:
       - USER_NVKD, USER_BP  (từ server template: '{{ user_ma_nvkd }}')
       - hierarchy, nvMap     (sau khi load hierarchy API)
     
     Lưu ý: computeAllowedNV() cần gọi THỦ CÔNG sau khi hierarchy + nvMap đã build xong.
             Không tự gọi khi include.
     
     SAU KHI INCLUDE, trang có:
       userNvkdList, userBpList     — parsed arrays
       allowedNV                    — Set of allowed ma_nvkd
       computeAllowedNV()           — gọi sau khi build nvMap
       getAllowedBP(khMap)           — trả về sorted array of BP codes
-->
<script>
var userNvkdList=(typeof USER_NVKD==='string'&&USER_NVKD)?USER_NVKD.split(',').map(function(s){return s.trim()}).filter(Boolean):[];
var userBpList=(typeof USER_BP==='string'&&USER_BP)?USER_BP.split(',').map(function(s){return s.trim()}).filter(Boolean):[];
var allowedNV=new Set();

function computeAllowedNV(){
    if(!userNvkdList.length){allowedNV=new Set(hierarchy.map(function(h){return h.ma_nvkd}));return}
    allowedNV=new Set();
    function addDesc(id){allowedNV.add(id);(nvMap[id]?nvMap[id].children:[]).forEach(function(c){addDesc(c.ma_nvkd)})}
    userNvkdList.forEach(function(id){if(nvMap[id])addDesc(id)});
}

function getAllowedBP(khMapRef){
    var km=khMapRef||khMap;
    if(!userBpList.length){var s=new Set();Object.values(km).forEach(function(v){if(v.ma_bp)s.add(v.ma_bp)});return[...s].sort()}
    return userBpList.sort();
}
</script>