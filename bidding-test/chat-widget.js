// ═══════════════ 文鳐智投 AI 对话助手 v4 ═══════════════
// 多轮对话 · DeepSeek大模型驱动 · 反馈合并 · 可拖动
(function() {
const API = "/bidding/api/chat";
const LOGO = "/bidding/img/logo.png";
let isOpen = false, isLoading = false, isFeedbackMode = false;
let chatHistory = [];

// ═══ 构建DOM ═══
const css = document.createElement('link');
css.rel = 'stylesheet'; css.href = '/bidding/chat-widget.css?v=6';
document.head.appendChild(css);

const wrapper = document.createElement('div');
wrapper.className = 'chat-widget-all';
wrapper.id = 'chatWidgetAll';
wrapper.innerHTML = `
  <div class="chat-trigger" id="chatTrigger" onclick="window.openChat()">
    <img src="${LOGO}" alt="文鳐智投" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 40 40%22><rect fill=%22%233b82f6%22 width=%2240%22 height=%2240%22 rx=%2220%22/><text x=%2220%22 y=%2227%22 text-anchor=%22middle%22 fill=%22white%22 font-size=%2220%22>文</text></svg>'">
    <span class="trigger-text">🤖 文鳐智投 · AI投标助手</span>
    <span class="trigger-badge">问问我</span>
  </div>

  <div class="chat-panel-v2" id="chatPanel">
    <!-- 可拖动头部 -->
    <div class="chat-header-v2" id="chatDragHandle">
      <img src="${LOGO}" alt="文鳐智投" onerror="this.style.display='none'">
      <div class="header-info">
        <div class="header-name">文鳐智投</div>
        <div class="header-status"><span class="dot"></span> 在线 · AI大模型驱动</div>
      </div>
      <button class="chat-fb-btn" id="chatFbBtn" onclick="window.toggleFeedbackMode()" title="反馈问题">📝</button>
      <button class="close-btn" onclick="window.closeChat()">✕</button>
    </div>

    <!-- 反馈模式：全屏反馈表单 -->
    <div class="chat-fb-panel" id="chatFbPanel" style="display:none">
      <div class="chat-fb-body">
        <div class="chat-fb-label">📝 告诉我们您发现了什么问题</div>
        <textarea id="chatFbText" placeholder="例如：&#10;• 某条招标信息标题/日期有误&#10;• 页面显示异常或功能不可用&#10;• 评分不合理，不相关的项目排到了前面&#10;• 有其他建议或需求"></textarea>
        <div class="chat-fb-hint">💡 提交后 AI 将在凌晨自检时自动分析并修复</div>
      </div>
      <div class="chat-fb-actions">
        <button class="chat-fb-cancel" onclick="window.toggleFeedbackMode()">← 返回对话</button>
        <button class="chat-fb-submit" id="chatFbSubmit" onclick="window.submitChatFeedback()">提交反馈</button>
      </div>
    </div>

    <!-- 正常对话模式 -->
    <div class="chat-normal-area" id="chatNormalArea">
      <div class="chat-presets-v2" id="chatPresetsV2"></div>
      <div class="chat-messages-v2" id="chatMessagesV2">
        <div class="chat-msg-v2 bot">
          👋 你好！我是<b>文鳐智投</b>，中南电力·数智科技的AI投标助手。<br><br>
          我基于 <b>DeepSeek 大模型</b> + 实时数据库，可以：<br>
          🔹 查询招标/中标数据<br>
          🔹 分析投标趋势<br>
          🔹 智能评分排序<br>
          🔹 支持<b>多轮追问</b><br><br>
          💡 发现数据有误？点击右上角 <b>📝</b> 直接反馈！<br>
          试试问我吧，或者点击下方的快捷问题 👇
        </div>
      </div>
      <div class="chat-input-v2">
        <input id="chatInputV2" placeholder="输入问题，按回车发送..." onkeydown="if(event.key==='Enter')window.sendChatV2()">
        <button onclick="window.sendChatV2()" id="chatSendBtnV2">▶</button>
      </div>
    </div>
  </div>
`;
document.body.appendChild(wrapper);

// ═══ 加载预设问题（含反馈入口） ═══
fetch(API).then(r => r.json()).then(d => {
  if (d.presets) {
    const el = document.getElementById('chatPresetsV2');
    // 反馈入口作为第一个预设
    const fbPreset = document.createElement('span');
    fbPreset.className = 'chat-preset-v2 chat-preset-fb';
    fbPreset.textContent = '📝 反馈问题';
    fbPreset.onclick = () => window.toggleFeedbackMode();
    el.appendChild(fbPreset);
    // 其他预设
    d.presets.forEach(q => {
      const btn = document.createElement('span');
      btn.className = 'chat-preset-v2';
      btn.textContent = q;
      btn.title = q;
      btn.onclick = () => { document.getElementById('chatInputV2').value = q; window.sendChatV2(); };
      el.appendChild(btn);
    });
  }
}).catch(() => {
  // 即使 API 失败也显示反馈入口
  const el = document.getElementById('chatPresetsV2');
  const fbPreset = document.createElement('span');
  fbPreset.className = 'chat-preset-v2 chat-preset-fb';
  fbPreset.textContent = '📝 反馈问题';
  fbPreset.onclick = () => window.toggleFeedbackMode();
  el.appendChild(fbPreset);
});

// ═══ 拖动功能 — 桌面+手机双支持 ═══
(function initDrag() {
  let dragging = false, startX, startY, origLeft, origTop;
  let wrapperRect, hasMoved = false;
  const wrapperEl = document.getElementById('chatWidgetAll');

  function getPos(e) {
    if (e.touches && e.touches.length) return {x: e.touches[0].clientX, y: e.touches[0].clientY};
    return {x: e.clientX, y: e.clientY};
  }

  function onStart(e) {
    if (e.target.closest('button, input, textarea, a')) return;
    dragging = true; hasMoved = false;
    wrapperEl.style.userSelect = 'none';
    wrapperEl.style.webkitUserSelect = 'none';
    wrapperRect = wrapperEl.getBoundingClientRect();
    const pos = getPos(e);
    startX = pos.x; startY = pos.y;
    origLeft = wrapperRect.left; origTop = wrapperRect.top;
    // Switch to fixed px positioning
    wrapperEl.style.position = 'fixed';
    wrapperEl.style.bottom = 'auto'; wrapperEl.style.right = 'auto';
    wrapperEl.style.left = origLeft + 'px'; wrapperEl.style.top = origTop + 'px';
  }

  function onMove(e) {
    if (!dragging) return;
    const pos = getPos(e);
    const dx = pos.x - startX, dy = pos.y - startY;
    if (Math.abs(dx) < 3 && Math.abs(dy) < 3) return;
    hasMoved = true;
    e.preventDefault();  // 阻止背景页面跟随滚动
    wrapperEl.style.left = (origLeft + dx) + 'px';
    wrapperEl.style.top = (origTop + dy) + 'px';
  }

  function onEnd(e) {
    if (!dragging) return;
    dragging = false;
    wrapperEl.style.userSelect = '';
    wrapperEl.style.webkitUserSelect = '';
    if (hasMoved) {
      setTimeout(() => { hasMoved = false; }, 0);
      e.preventDefault();
    }
  }

  // Mouse events (desktop) — 头部 + 收起态图标可拖
  const dragHandle = document.getElementById('chatDragHandle');
  const dragTrigger = document.getElementById('chatTrigger');
  if (dragHandle) dragHandle.addEventListener('mousedown', onStart);
  if (dragTrigger) dragTrigger.addEventListener('mousedown', onStart);
  document.addEventListener('mousemove', onMove);
  document.addEventListener('mouseup', onEnd);
  // Touch events (mobile) — 头部 + 收起态图标可拖
  if (dragHandle) dragHandle.addEventListener('touchstart', onStart, {passive:false});
  if (dragTrigger) dragTrigger.addEventListener('touchstart', onStart, {passive:false});
  document.addEventListener('touchmove', onMove, {passive:false});
  document.addEventListener('touchend', onEnd);

  // 拦截 click：如果刚拖动过，阻止打开面板
  wrapperEl.addEventListener('click', function(e) {
    if (hasMoved) {
      e.stopPropagation(); e.preventDefault();
      hasMoved = false;
    }
  }, true);
})();

// ═══ 全局函数 ═══
window.openChat = function() {
  isOpen = true;
  document.getElementById('chatTrigger').style.display = 'none';
  document.getElementById('chatPanel').classList.add('open');
  // 重置wrapper定位 — 手机端用CSS媒体查询，桌面端固定值
  const w = document.getElementById('chatWidgetAll');
  w.style.position = 'fixed';
  if (window.innerWidth <= 768) {
    w.style.bottom = ''; w.style.right = ''; w.style.left = ''; w.style.top = '';
  } else {
    w.style.bottom = '20px'; w.style.right = '20px'; w.style.left = 'auto'; w.style.top = 'auto';
  }
  setTimeout(() => {
    const input = document.getElementById('chatInputV2');
    if (input && !isFeedbackMode) input.focus();
  }, 300);
};

window.closeChat = function() {
  isOpen = false;
  document.getElementById('chatPanel').classList.remove('open');
  document.getElementById('chatTrigger').style.display = 'flex';
};

window.toggleFeedbackMode = function() {
  isFeedbackMode = !isFeedbackMode;
  const fbPanel = document.getElementById('chatFbPanel');
  const normalArea = document.getElementById('chatNormalArea');
  const fbBtn = document.getElementById('chatFbBtn');
  if (isFeedbackMode) {
    fbPanel.style.display = 'flex';
    normalArea.style.display = 'none';
    fbBtn.style.background = '#ef4444';
    fbBtn.style.color = '#fff';
    setTimeout(() => document.getElementById('chatFbText').focus(), 200);
  } else {
    fbPanel.style.display = 'none';
    normalArea.style.display = '';
    fbBtn.style.background = 'rgba(255,255,255,.2)';
    fbBtn.style.color = '#fff';
    setTimeout(() => document.getElementById('chatInputV2').focus(), 200);
  }
};

window.submitChatFeedback = function() {
  const textarea = document.getElementById('chatFbText');
  const btn = document.getElementById('chatFbSubmit');
  const reason = textarea.value.trim();
  if (!reason) { addMsgV2('⚠️ 请填写反馈内容', 'bot'); return; }

  btn.disabled = true;
  btn.textContent = '提交中...';

  fetch('/bidding/api/feedback', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({type: 'general', reason: reason, section: 'bidding'})
  }).then(r => {
    if (!r.ok) return r.json().then(e => { throw new Error(e.error || '提交失败'); });
    return r.json();
  }).then(() => {
    textarea.value = '';
    addMsgV2('✅ 反馈已提交！AI 将在凌晨自检时分析处理，感谢您的反馈 🙏', 'bot');
    setTimeout(() => window.toggleFeedbackMode(), 1200);
  }).catch(e => {
    addMsgV2('❌ 提交失败: ' + e.message, 'bot');
  }).finally(() => {
    btn.disabled = false;
    btn.textContent = '提交反馈';
  });
};

window.sendChatV2 = function() {
  if (isFeedbackMode) return;
  const input = document.getElementById('chatInputV2');
  const q = input.value.trim();
  if (!q || isLoading) return;

  isLoading = true;
  document.getElementById('chatSendBtnV2').disabled = true;

  addMsgV2(q, 'user');
  chatHistory.push({role: 'user', content: q});
  input.value = '';
  const typingId = addTypingV2();

  fetch(API, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({question: q, messages: chatHistory.slice(0, -1)})
  }).then(r => r.json()).then(d => {
    removeTypingV2(typingId);
    const answer = d.answer || '⚠️ 未获取到回答';
    addMsgV2(answer, 'bot', true);
    chatHistory.push({role: 'assistant', content: answer});
    if (chatHistory.length > 20) chatHistory = chatHistory.slice(-20);
    isLoading = false;
    document.getElementById('chatSendBtnV2').disabled = false;
  }).catch(e => {
    removeTypingV2(typingId);
    addMsgV2('⚠️ 网络错误，请稍后重试', 'bot');
    isLoading = false;
    document.getElementById('chatSendBtnV2').disabled = false;
  });
};

function addMsgV2(text, role, isHtml) {
  const div = document.createElement('div');
  div.className = 'chat-msg-v2 ' + role;
  if (isHtml) {
    text = text
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" class="chat-link" rel="noopener">$1</a>')
      .replace(/\*\*(.*?)\*\*/g, '<b>$1</b>')
      .replace(/\n/g, '<br>')
      .replace(/^- (.*)/gm, '• $1')
      .replace(/(\d+)\.\s/g, '<b>$1.</b> ');
    div.innerHTML = text;
  } else {
    div.textContent = text;
  }
  document.getElementById('chatMessagesV2').appendChild(div);
  div.scrollIntoView({behavior: 'smooth'});
}

function addTypingV2() {
  const id = 'typing_' + Date.now();
  const div = document.createElement('div');
  div.className = 'chat-msg-v2 bot';
  div.id = id;
  div.innerHTML = '<div class="typing"><span></span><span></span><span></span></div>';
  document.getElementById('chatMessagesV2').appendChild(div);
  div.scrollIntoView({behavior: 'smooth'});
  return id;
}

function removeTypingV2(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

// ═══ 3秒后自动弹出（仅首次，手机端不弹） ═══
setTimeout(() => {
  if (window.innerWidth > 768 && !sessionStorage.getItem('chat_auto_opened')) {
    sessionStorage.setItem('chat_auto_opened', '1');
    window.openChat();
  }
}, 3000);
})();
