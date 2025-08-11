// Tabs + ACL search & add with mutual exclusion
document.addEventListener('DOMContentLoaded', function(){
  // Tabs
  document.querySelectorAll('.acl-tab').forEach(tab => {
    tab.addEventListener('click', function(){
      document.querySelectorAll('.acl-tab').forEach(t => t.classList.remove('active'));
      this.classList.add('active');
      document.querySelectorAll('.acl-tab-content').forEach(c => c.classList.add('hidden'));
      document.getElementById('acl-' + this.dataset.tab).classList.remove('hidden');
    });
  });

  // helpers
  const allowedInput = document.getElementById('allowed-users');
  const blockedInput = document.getElementById('blocked-users');
  const allowedListEl = document.getElementById('allow-list');
  const blockedListEl = document.getElementById('block-list');

  function getArr(v){ return v ? v.split(',').map(s=>s.trim()).filter(Boolean) : []; }
  function setArr(el, arr){ el.value = arr.join(','); }
  function renderList(ul, arr){ ul.innerHTML = ''; arr.forEach(u => {
      const li = document.createElement('li');
      li.dataset.username = u;
      li.innerHTML = u + ' <button type="button" class="remove-btn">X</button>';
      ul.appendChild(li);
  }); }

  function addUserTo(listName, username){
    let allowed = getArr(allowedInput.value);
    let blocked = getArr(blockedInput.value);
    if(listName === 'allow'){
      if(blocked.includes(username)) {
        alert('이미 차단 그룹에 있는 사용자입니다. 먼저 차단을 해제하세요.');
        return;
      }
      if(!allowed.includes(username)) allowed.push(username);
    } else {
      if(allowed.includes(username)){
        // remove from allowed
        allowed = allowed.filter(x=>x!==username);
      }
      if(!blocked.includes(username)) blocked.push(username);
    }
    setArr(allowedInput, allowed);
    setArr(blockedInput, blocked);
    renderList(allowedListEl, allowed);
    renderList(blockedListEl, blocked);
  }

  // remove handlers
  document.querySelectorAll('.acl-list').forEach(ul => {
    ul.addEventListener('click', function(e){
      if(e.target.classList.contains('remove-btn')){
        const li = e.target.closest('li');
        const uname = li.dataset.username;
        let allowed = getArr(allowedInput.value);
        let blocked = getArr(blockedInput.value);
        allowed = allowed.filter(x=>x!==uname);
        blocked = blocked.filter(x=>x!==uname);
        setArr(allowedInput, allowed);
        setArr(blockedInput, blocked);
        renderList(allowedListEl, allowed);
        renderList(blockedListEl, blocked);
      }
    });
  });

  // search handlers (allow and block)
  async function doSearch(q){
    const res = await fetch('/api/users?q=' + encodeURIComponent(q));
    return await res.json();
  }

  document.getElementById('allow-search').addEventListener('input', async function(){
    const q = this.value.trim();
    const results = document.getElementById('allow-results');
    results.innerHTML = '';
    if(!q) return;
    const data = await doSearch(q);
    data.forEach(u => {
      const div = document.createElement('div');
      div.className = 'search-item';
      div.textContent = u.username;
      div.addEventListener('click', ()=> {
        addUserTo('allow', u.username);
        results.innerHTML = '';
        document.getElementById('allow-search').value = '';
      });
      results.appendChild(div);
    });
  });

  document.getElementById('block-search').addEventListener('input', async function(){
    const q = this.value.trim();
    const results = document.getElementById('block-results');
    results.innerHTML = '';
    if(!q) return;
    const data = await doSearch(q);
    data.forEach(u => {
      const div = document.createElement('div');
      div.className = 'search-item';
      div.textContent = u.username;
      div.addEventListener('click', ()=> {
        addUserTo('block', u.username);
        results.innerHTML = '';
        document.getElementById('block-search').value = '';
      });
      results.appendChild(div);
    });
  });

  // initial render from hidden inputs
  renderList(allowedListEl, getArr(allowedInput.value));
  renderList(blockedListEl, getArr(blockedInput.value));
});
