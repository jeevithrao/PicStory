// ============================================================
// PicStory — Frontend Application Logic
// Single-file JS: wizard flow, API calls, drag-and-drop editor
// ============================================================

const API = window.location.origin;

// ---- State ----
const state = {
  step: 0,          // 0=landing, 1=input, 2=caption, 3=music, 4=narration, 5=edit, 6=assemble, 7=output
  mode: null,       // 'upload' | 'awareness'
  projectId: null,
  language: 'hi',
  context: '',      // User-provided context for captioning
  imagePaths: [],
  captions: [],
  vibe: 'calm',
  musicSource: 'ai',
  musicPath: null,
  narrationText: null,
  narrationPath: null,
  perImageNarrations: null,  // [{path, duration, text}] for synced slideshow
  videoPath: null,
  socialCaption: '',
  socialHashtags: [],
};

const STEPS = ['Mode', 'Input', 'Caption', 'Music', 'Narration', 'Edit', 'Video', 'Output'];

const LANGUAGES = {
  hi: 'Hindi', kok: 'Konkani', kn: 'Kannada', doi: 'Dogri',
  brx: 'Bodo', ur: 'Urdu', ta: 'Tamil', ks: 'Kashmiri',
  as: 'Assamese', bn: 'Bengali', mr: 'Marathi', sd: 'Sindhi',
  mai: 'Maithili', pa: 'Punjabi', ml: 'Malayalam', mni: 'Manipuri',
  te: 'Telugu', sa: 'Sanskrit', ne: 'Nepali', sat: 'Santali',
  gu: 'Gujarati', or: 'Odia',
};

const VIBES = [
  { id: 'calm', emoji: '🌿', label: 'Calm' },
  { id: 'romantic', emoji: '💕', label: 'Romantic' },
  { id: 'rock', emoji: '🎸', label: 'Rock' },
  { id: 'happy', emoji: '😊', label: 'Happy' },
  { id: 'sad', emoji: '😢', label: 'Sad' },
  { id: 'motivational', emoji: '🔥', label: 'Motivational' },
];

// ---- Helpers ----
function $(sel) { return document.querySelector(sel); }
function $$(sel) { return document.querySelectorAll(sel); }

function showError(container, msg) {
  const el = document.createElement('div');
  el.className = 'alert alert-error';
  el.textContent = msg;
  container.prepend(el);
  setTimeout(() => el.remove(), 6000);
}

async function apiFetch(endpoint, options = {}) {
  const resp = await fetch(`${API}${endpoint}`, options);
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(err.detail || `HTTP ${resp.status}`);
  }
  return resp.json();
}

// ---- Step Navigation ----
function goToStep(n) {
  state.step = n;
  // Update sections
  $$('.step-section').forEach((sec, i) => {
    sec.classList.toggle('active', i === n);
  });
  // Update step bar
  $$('.step-dot').forEach((dot, i) => {
    dot.classList.remove('active', 'done');
    if (i === n) dot.classList.add('active');
    else if (i < n) dot.classList.add('done');
  });
  $$('.step-line').forEach((line, i) => {
    line.classList.toggle('done', i < n);
  });
  window.scrollTo({ top: 0, behavior: 'smooth' });

  // Trigger music init when navigating to step 3
  if (n === 3) {
    if (!$('#step-3-content .audio-player')) {
        initMusicStep();
    }
  }
}

// ---- Step 0: Mode Selection ----
function selectMode(mode) {
  state.mode = mode;
  renderStep1();
  goToStep(1);
}

// ---- Step 1: Input (Upload or Generate) ----
function renderStep1() {
  const container = $('#step-1-content');
  if (state.mode === 'upload') {
    container.innerHTML = `
      <div class="form-group">
        <label>Choose Language</label>
        <p style="font-size:0.82rem;color:var(--text-secondary);margin-top:0;margin-bottom:0.5rem;">
          Descriptions and narration will be generated in this language
        </p>
        <div class="lang-grid" id="lang-grid-1"></div>
      </div>
      <div class="form-group">
        <label>Context / Description (optional)</label>
        <textarea class="form-textarea" id="context-input" placeholder="e.g. Family trip to Goa, December 2025 — beach sunsets, local food, group photos..."></textarea>
        <p style="font-size:0.78rem;color:var(--text-muted);margin-top:0.25rem;">
          💡 Helps AI write more accurate and relevant descriptions for your photos
        </p>
      </div>
      <div class="drop-zone" id="drop-zone">
        <input type="file" accept=".zip" id="zip-input" />
        <div class="icon">📁</div>
        <h4>Drop your ZIP file here</h4>
        <p>or click to browse • Max 20 images</p>
      </div>
      <div class="actions-row">
        <button class="btn btn-primary" id="btn-upload" disabled>
          Upload & Continue
        </button>
        <button class="btn btn-secondary" onclick="goToStep(0)">← Back</button>
      </div>
    `;
    renderLangGrid('lang-grid-1');
    const zipInput = $('#zip-input');
    const dropZone = $('#drop-zone');
    const btnUpload = $('#btn-upload');

    zipInput.addEventListener('change', () => {
      if (zipInput.files.length > 0) {
        dropZone.querySelector('h4').textContent = zipInput.files[0].name;
        btnUpload.disabled = false;
      }
    });
    dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
    dropZone.addEventListener('drop', e => {
      e.preventDefault(); dropZone.classList.remove('drag-over');
      zipInput.files = e.dataTransfer.files;
      zipInput.dispatchEvent(new Event('change'));
    });

    btnUpload.addEventListener('click', async () => {
      btnUpload.disabled = true;
      btnUpload.innerHTML = '<span class="spinner"></span> Uploading...';
      state.context = ($('#context-input') ? $('#context-input').value.trim() : '');
      try {
        const form = new FormData();
        form.append('file', zipInput.files[0]);
        form.append('language', state.language);
        form.append('context', state.context);
        const data = await apiFetch('/upload', { method: 'POST', body: form });
        state.projectId = data.project_id;
        state.imagePaths = data.image_paths;
        await startCaptioning();
      } catch (e) {
        showError(container, e.message);
        btnUpload.disabled = false;
        btnUpload.textContent = 'Upload & Continue';
      }
    });
  } else {
    // Awareness mode — prompt is English only, language is for narration
    container.innerHTML = `
      <div class="form-group">
        <label>Narration Language</label>
        <p style="font-size:0.82rem;color:var(--text-secondary);margin-top:0;margin-bottom:0.5rem;">
          The video narration and descriptions will be generated in this language
        </p>
        <div class="lang-grid" id="lang-grid-1"></div>
      </div>
      <div class="form-group">
        <label>Enter your topic (in English)</label>
        <textarea class="form-textarea" id="prompt-input" placeholder="e.g. Indian culture and heritage, Save water awareness campaign..."></textarea>
        <p style="font-size:0.78rem;color:var(--text-muted);margin-top:0.25rem;">
          💡 The prompt must be in English. AI will generate images from this topic.
        </p>
      </div>
      <div class="actions-row">
        <button class="btn btn-primary" id="btn-generate">
          Generate Images
        </button>
        <button class="btn btn-secondary" onclick="goToStep(0)">← Back</button>
      </div>
    `;
    renderLangGrid('lang-grid-1');

    $('#btn-generate').addEventListener('click', async () => {
      const prompt = $('#prompt-input').value.trim();
      if (!prompt) return showError(container, 'Please enter a topic.');
      const btn = $('#btn-generate');
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner"></span> Generating images...';
      try {
        const data = await apiFetch('/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt, language: state.language }),
        });
        state.projectId = data.project_id;
        state.imagePaths = data.image_paths;
        await startCaptioning();
      } catch (e) {
        showError(container, e.message);
        btn.disabled = false;
        btn.textContent = 'Generate Images';
      }
    });
  }
}

function renderLangGrid(id) {
  const grid = $(`#${id}`);
  grid.innerHTML = Object.entries(LANGUAGES).map(([code, name]) =>
    `<div class="lang-chip ${code === state.language ? 'selected' : ''}" data-lang="${code}">${name}</div>`
  ).join('');
  grid.addEventListener('click', e => {
    const chip = e.target.closest('.lang-chip');
    if (!chip) return;
    state.language = chip.dataset.lang;
    grid.querySelectorAll('.lang-chip').forEach(c => c.classList.remove('selected'));
    chip.classList.add('selected');
  });
}

// ---- Step 2: Captioning ----
async function startCaptioning() {
  goToStep(2);
  const container = $('#step-2-content');
  container.innerHTML = `
    <div class="status-pill"><span class="dot"></span> AI is analyzing your images...</div>
    <div class="progress-container">
      <p class="progress-text" id="cap-status">Connecting to stream...</p>
    </div>
    <div class="caption-list" id="stream-container"></div>
  `;

  state.captions = [];
  const streamContainer = $('#stream-container');
  const statusTxt = $('#cap-status');

  const source = new EventSource(`${API}/caption-stream/${state.projectId}/${state.language}`);
  
  source.onmessage = (e) => {
    const data = JSON.parse(e.data);
    
    if (data.type === 'image') {
       const cleanName = data.filename.replace(/\W/g, '');
       streamContainer.innerHTML += `
         <div class="caption-item fade-in-up" id="cap-${cleanName}">
           <img src="${API}/${data.url}" alt="${data.filename}">
           <div class="caption-text">
             <div class="en typewriter"></div>
             <div class="translated typewriter" style="animation-delay: 2s"></div>
           </div>
         </div>
       `;
    } else if (data.type === 'progress') {
       statusTxt.textContent = `Analyzing ${data.filename}...`;
    } else if (data.type === 'info') {
       statusTxt.textContent = data.message;
    } else if (data.type === 'caption') {
       const cleanName = data.filename.replace(/\W/g, '');
       const card = $(`#cap-${cleanName}`);
       if (card) {
         const enEl = card.querySelector('.en');
         enEl.textContent = data.caption_en;
         enEl.style.animation = 'none';
         enEl.offsetHeight;
         enEl.style.animation = 'typewriter 2s steps(40, end)';
         
         const trEl = card.querySelector('.translated');
         trEl.textContent = data.caption_translated;
         trEl.style.animation = 'none';
         trEl.offsetHeight;
         trEl.style.animation = 'typewriter 2s steps(40, end)';
       }
       state.captions.push({
         image_name: data.filename,
         caption_en: data.caption_en,
         caption_translated: data.caption_translated
       });
    } else if (data.type === 'error') {
       showError(container, data.message);
       source.close();
    } else if (data.type === 'done') {
       source.close();
       statusTxt.textContent = "✅ Storyboard complete!";
       container.innerHTML += `
         <div class="actions-row fade-in-up">
           <button class="btn btn-primary" onclick="goToStep(3)">Choose Music →</button>
         </div>
       `;
    }
  };

  source.onerror = () => {
    source.close();
    showError(container, "Lost connection to server");
  };
}

// ---- Step 3: Music ----
function initMusicStep() {
  const container = $('#step-3-content');
  container.innerHTML = `
    <div class="status-pill"><span class="dot"></span> AI is analyzing the story to pick the perfect music vibe...</div>
  `;
  generateMusic("ai", null);
}

async function generateMusic(source, vibe) {
  const container = $('#step-3-content');
  try {
    const data = await apiFetch('/music', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project_id: state.projectId,
        vibe: vibe,
        source: source,
      }),
    });
    state.musicPath = data.music_path;
    state.vibe = data.ai_suggested_vibe;
    renderMusicResult(container, data, source);
  } catch (e) {
    showError(container, e.message);
    container.innerHTML += `<button class="btn btn-secondary" onclick="initMusicStep()">Retry Request</button>`;
  }
}

function renderMusicResult(container, data, currentSource) {
  const vibeLabel = `Gemini chose: <strong>${data.ai_suggested_vibe}</strong> vibe`;
  
  container.innerHTML = `
    <div class="alert alert-success fade-in-up">✅ ${vibeLabel}</div>
    <div class="audio-player fade-in-up" style="animation-delay: 0.1s">
      <audio controls autoplay src="${API}/${data.music_path}"></audio>
    </div>
    
    <div class="source-toggle fade-in-up" style="animation-delay: 0.2s">
      <button class="source-btn ${currentSource === 'ai' ? 'active' : ''}" onclick="generateMusic('ai', '${data.ai_suggested_vibe}')">🤖 AI Generated</button>
      <button class="source-btn ${currentSource === 'library' ? 'active' : ''}" onclick="generateMusic('library', '${data.ai_suggested_vibe}')">📚 Freesound Library</button>
    </div>

    ${data.suggestions && data.suggestions.length > 0 ? `
      <p class="card-subtitle fade-in-up" style="animation-delay: 0.3s">Alternative vibes:</p>
      ${data.suggestions.map((s, i) => `
        <div class="audio-player fade-in-up" style="animation-delay: ${0.4 + i*0.1}s">
           <div style="display:flex; justify-content:space-between; align-items:center;">
             <p style="font-size:0.85rem;color:var(--text-secondary);margin-bottom:0px;">${s.name}</p>
             <button class="btn btn-secondary" style="padding:0.2rem 0.5rem;font-size:0.75rem;" onclick="swapMusic('${s.path}', '${s.vibe}')">Use this</button>
           </div>
           <audio controls src="${API}/${s.path}" style="margin-top: 0.5rem; width: 100%;"></audio>
        </div>
      `).join('')}
    ` : ''}
    <div class="actions-row fade-in-up" style="animation-delay: 0.8s">
      <button class="btn btn-primary" onclick="startNarration()">Generate Narration →</button>
    </div>
  `;
}

window.swapMusic = function(path, vibe) {
  state.musicPath = path;
  state.vibe = vibe;
  const container = $('#step-3-content');
  const alert = container.querySelector('.alert-success');
  if(alert) alert.innerHTML = `✅ Swapped to <strong>${vibe}</strong> vibe`;
  const topAudio = container.querySelector('.audio-player audio');
  if (topAudio) {
      topAudio.src = `${API}/${path}`;
      topAudio.play();
  }
};

// ---- Step 4: Narration ----
async function startNarration() {
  goToStep(4);
  const container = $('#step-4-content');
  container.innerHTML = `
    <div class="status-pill"><span class="dot"></span> Gemini is writing your narration...</div>
    <div class="progress-container">
      <div class="progress-bar-bg"><div class="progress-bar-fill" style="width:40%"></div></div>
      <p class="progress-text">Generating per-image narration segments & voiceover...</p>
    </div>
  `;

  try {
    const data = await apiFetch('/narration', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project_id: state.projectId, language: state.language }),
    });
    state.narrationText = data.narration_text;
    state.narrationPath = data.narration_path;
    state.perImageNarrations = data.per_image_narrations || null;
    renderNarrationResult(container, data);
  } catch (e) {
    container.innerHTML = '';
    showError(container, `Narration failed: ${e.message}`);
    container.innerHTML += `<button class="btn btn-secondary" onclick="startNarration()">Retry</button>`;
  }
}

function renderNarrationResult(container, data) {
  container.innerHTML = `
    <div class="alert alert-success fade-in-up">✅ Narration generated!</div>
    <p class="card-subtitle fade-in-up" style="animation-delay: 0.1s">Script</p>
    <div class="social-caption-box fade-in-up" id="narration-script-box" style="animation-delay: 0.2s"></div>
    <p class="card-subtitle fade-in-up" style="animation-delay: 0.3s">Voiceover Preview</p>
    <div class="audio-player fade-in-up" style="animation-delay: 0.4s">
      <audio controls src="${API}/${data.narration_path}"></audio>
    </div>
    <div class="actions-row fade-in-up" style="animation-delay: 0.5s">
      <button class="btn btn-primary" onclick="goToStep(5); initEditor();">Edit Image Order →</button>
      <button class="btn btn-secondary" onclick="startNarration()">🔄 Regenerate</button>
    </div>
  `;

  // Custom JS typewriter effect for the narration text
  const box = $('#narration-script-box');
  if (box) {
    const words = data.narration_text.split(' ');
    let i = 0;
    setTimeout(() => {
      const inv = setInterval(() => {
        if (i >= words.length) {
          clearInterval(inv);
          return;
        }
        box.appendChild(document.createTextNode(words[i] + ' '));
        i++;
      }, 50); // type a word every 50ms
    }, 200); // wait for fade-in
  }
}

// ---- Step 5: Drag-and-Drop Editor ----
let editorImages = [];
let removedImages = [];

function initEditor() {
  editorImages = state.captions.map(c => c.image_name);
  removedImages = [];
  renderEditor();
}

function renderEditor() {
  const container = $('#step-5-content');
  const thumbsHtml = editorImages.map((name, i) => {
    const imgPath = state.imagePaths.find(p => p.includes(name)) || '';
    const src = imgPath ? `${API}/${imgPath}` : '';
    return `
      <div class="editor-thumb" draggable="true" data-idx="${i}" data-name="${name}">
        <img src="${src}" alt="${name}" />
        <button class="remove-btn" onclick="removeImage(${i})" title="Remove">✕</button>
        <span class="order-badge">${i + 1}</span>
      </div>
    `;
  }).join('');

  container.innerHTML = `
    <p class="card-subtitle">Drag to reorder • Click ✕ to remove</p>
    <div class="editor-grid" id="editor-grid">${thumbsHtml}</div>
    <p style="font-size:0.82rem;color:var(--text-muted);margin-top:0.5rem;">${editorImages.length} images in final order</p>
    <div class="actions-row">
      <button class="btn btn-primary" id="btn-save-edits">Save & Build Video →</button>
      <button class="btn btn-secondary" onclick="goToStep(4)">← Back</button>
    </div>
  `;

  setupDragAndDrop();

  $('#btn-save-edits').addEventListener('click', async () => {
    const btn = $('#btn-save-edits');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Saving...';
    try {
      await apiFetch('/edit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: state.projectId,
          ordered_images: editorImages,
          removed_images: removedImages,
        }),
      });
      await startVideoAssembly();
    } catch (e) {
      showError(container, e.message);
      btn.disabled = false;
      btn.textContent = 'Save & Build Video →';
    }
  });
}

function removeImage(idx) {
  const removed = editorImages.splice(idx, 1)[0];
  removedImages.push(removed);
  renderEditor();
}

function setupDragAndDrop() {
  const grid = $('#editor-grid');
  if (!grid) return;
  let dragIdx = null;

  grid.addEventListener('dragstart', e => {
    const thumb = e.target.closest('.editor-thumb');
    if (!thumb) return;
    dragIdx = parseInt(thumb.dataset.idx);
    thumb.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
  });

  grid.addEventListener('dragend', e => {
    $$('.editor-thumb').forEach(t => t.classList.remove('dragging', 'drag-over-thumb'));
  });

  grid.addEventListener('dragover', e => {
    e.preventDefault();
    const thumb = e.target.closest('.editor-thumb');
    if (thumb) thumb.classList.add('drag-over-thumb');
  });

  grid.addEventListener('dragleave', e => {
    const thumb = e.target.closest('.editor-thumb');
    if (thumb) thumb.classList.remove('drag-over-thumb');
  });

  grid.addEventListener('drop', e => {
    e.preventDefault();
    const thumb = e.target.closest('.editor-thumb');
    if (!thumb || dragIdx === null) return;
    const dropIdx = parseInt(thumb.dataset.idx);
    if (dragIdx === dropIdx) return;

    // Swap
    const [item] = editorImages.splice(dragIdx, 1);
    editorImages.splice(dropIdx, 0, item);
    dragIdx = null;
    renderEditor();
  });
}

// ---- Step 6: Video Assembly ----
async function startVideoAssembly() {
  goToStep(6);
  const container = $('#step-6-content');
  container.innerHTML = `
    <div class="status-pill"><span class="dot"></span> Assembling your video...</div>
    <div class="progress-container">
      <div class="progress-bar-bg"><div class="progress-bar-fill" id="vid-progress" style="width:20%"></div></div>
      <p class="progress-text" id="vid-status">MoviePy + FFmpeg are stitching everything together...</p>
    </div>
  `;

  // Simulate progress
  let progress = 20;
  const progressInterval = setInterval(() => {
    progress = Math.min(progress + 5, 90);
    const bar = $('#vid-progress');
    if (bar) bar.style.width = progress + '%';
  }, 2000);

  try {
    const payload = {
      project_id: state.projectId,
      music_path: state.musicPath || '',
    };
    // Pass per-image narrations for synced slideshow if available
    if (state.perImageNarrations) {
      payload.per_image_narrations = state.perImageNarrations;
    }
    const data = await apiFetch('/video', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    clearInterval(progressInterval);
    state.videoPath = data.video_path;
    await loadOutput();
  } catch (e) {
    clearInterval(progressInterval);
    container.innerHTML = '';
    showError(container, `Video assembly failed: ${e.message}`);
    container.innerHTML += `<button class="btn btn-secondary" onclick="startVideoAssembly()">Retry</button>`;
  }
}

// ---- Step 7: Output ----
async function loadOutput() {
  goToStep(7);
  const container = $('#step-7-content');
  container.innerHTML = `
    <div class="alert alert-success fade-in-up">🎬 Your video is ready!</div>
    <div class="video-preview fade-in-up" style="animation-delay: 0.2s">
      <video controls autoplay src="${API}/${state.videoPath}"></video>
    </div>
    <div class="actions-row fade-in-up" style="animation-delay: 0.4s">
      <a class="btn btn-primary" href="${API}/${state.videoPath}" download>⬇ Download MP4</a>
      <button class="btn btn-secondary" id="btn-social">Generate Social Captions</button>
    </div>
    <div id="social-container"></div>
  `;

  $('#btn-social').addEventListener('click', async () => {
    const btn = $('#btn-social');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Generating...';
    try {
      const data = await apiFetch('/social', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: state.projectId,
          language: state.language,
          platform: 'instagram',
        }),
      });
      renderSocialOutput(data);
    } catch (e) {
      showError(container, e.message);
      btn.disabled = false;
      btn.textContent = 'Generate Social Captions';
    }
  });
}

function renderSocialOutput(data) {
  const container = $('#social-container');
  container.innerHTML = `
    <div style="margin-top:1.5rem;">
      <p class="card-subtitle">📝 Caption</p>
      <div class="social-caption-box">${data.caption}</div>
      <p class="card-subtitle">#️⃣ Hashtags</p>
      <div class="hashtag-cloud">
        ${data.hashtags.map(h => `<span class="hashtag">${h}</span>`).join('')}
      </div>
      <div class="actions-row" style="margin-top:1rem;">
        <button class="btn btn-secondary" onclick="copyToClipboard()">📋 Copy All</button>
      </div>
    </div>
  `;
  state.socialCaption = data.caption;
  state.socialHashtags = data.hashtags;
}

function copyToClipboard() {
  const text = `${state.socialCaption}\n\n${state.socialHashtags.join(' ')}`;
  navigator.clipboard.writeText(text).then(() => {
    const btn = document.querySelector('.actions-row .btn-secondary:last-child');
    if (btn) { btn.textContent = '✅ Copied!'; setTimeout(() => btn.textContent = '📋 Copy All', 2000); }
  });
}

// ---- Initialize ----
document.addEventListener('DOMContentLoaded', () => {
  // Mode selection handlers
  $$('.mode-card').forEach(card => {
    card.addEventListener('click', () => selectMode(card.dataset.mode));
  });

  // Step 3 needs re-initialization when navigated to
  const observer = new MutationObserver(() => {
    if ($('#step-3.active') && !$('#vibe-grid')) {
      initMusicStep();
    }
  });

  // Watch for step changes
  const step3 = $('#step-3');
  if (step3) {
    observer.observe(step3, { attributes: true, attributeFilter: ['class'] });
  }

  goToStep(0);
});
