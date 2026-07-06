// VK Mini App Client JS
let bridge = window.vkBridge || null;
let userId = "vk_demo_user";
let currentUser = null;
let activeTab = "dashboard";
let currentScanResult = null;
let base64Image = null;
let vkUserData = null;

// Format date for greeting
const options = { weekday: 'long', month: 'long', day: 'numeric' };
document.getElementById('date-text').innerText = new Date().toLocaleDateString('ru-RU', options);

// Initialize VK Bridge and Get User Info
if (bridge) {
  bridge.send("VKWebAppInit");
  bridge.send("VKWebAppGetUserInfo")
    .then((data) => {
      vkUserData = data;
      if (data.id) {
        userId = `vk_${data.id}`;
      }
      loadApp();
    })
    .catch((err) => {
      console.error("VK GetUserInfo error:", err);
      loadApp();
    });
} else {
  loadApp();
}

// Load App
function loadApp() {
  fetchUserData();
}

// Fetch user data from server sync
function fetchUserData() {
  fetch(`/api/sync?userId=${userId}`)
    .then(res => res.json())
    .then(data => {
      if (data && data.success && data.user) {
        currentUser = data.user;
        // Optionally update avatar/name from VK if they were missing
        if (vkUserData) {
          if (!currentUser.name || currentUser.name === "Пользователь") {
            currentUser.name = `${vkUserData.first_name} ${vkUserData.last_name}`;
          }
          if (!currentUser.avatarUrl) {
            currentUser.avatarUrl = vkUserData.photo_200;
          }
        }
      } else {
        // Create defaults
        currentUser = {
          email: userId,
          name: vkUserData ? `${vkUserData.first_name} ${vkUserData.last_name}` : "Пользователь",
          gender: "male",
          age: 25,
          height: 175,
          weight: 70,
          activity: 1.2,
          targets: calculateTargets("male", 25, 175, 70, 1.2),
          isPremium: false,
          avatarUrl: vkUserData ? vkUserData.photo_200 : null,
          scans: [],
          dailyLog: []
        };
        syncUser();
      }
      
      // Update UI
      document.getElementById('loading-screen').style.display = 'none';
      document.getElementById('app').style.display = 'block';
      document.getElementById('bottom-nav').style.display = 'flex';
      
      if (vkUserData) {
        document.getElementById('greeting-text').innerText = `Привет, ${vkUserData.first_name}! 👋`;
      } else {
        document.getElementById('greeting-text').innerText = `Привет! 👋`;
      }
      
      updateDashboard();
      renderProfile();
    })
    .catch(err => {
      console.error("Fetch user error:", err);
      showToast("Ошибка загрузки данных. Используется демо-режим.");
      document.getElementById('loading-screen').style.display = 'none';
      document.getElementById('app').style.display = 'block';
      document.getElementById('bottom-nav').style.display = 'flex';
    });
}

// Calculate Mifflin-St Jeor daily norms
function calculateTargets(gender, age, height, weight, activity) {
  let bmr = 0;
  if (gender === "male") {
    bmr = 10 * weight + 6.25 * height - 5 * age + 5;
  } else {
    bmr = 10 * weight + 6.25 * height - 5 * age - 161;
  }
  const calories = Math.round(bmr * activity);
  return {
    bmr: Math.round(bmr),
    calories: calories,
    protein: Math.round((calories * 0.3) / 4),
    carbs: Math.round((calories * 0.45) / 4),
    fats: Math.round((calories * 0.25) / 9),
    fiber: Math.min(40, Math.max(20, Math.round((calories * 14) / 1000)))
  };
}

// Sync user data back to backend
function syncUser() {
  if (!currentUser) return;
  fetch('/api/sync', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ userId: userId, user: currentUser })
  })
  .then(res => res.json())
  .then(data => {
    if (data && data.success) {
      console.log("User synced successfully.");
    }
  })
  .catch(err => console.error("Sync error:", err));
}

// Switch tabs
function switchTab(tabName) {
  activeTab = tabName;
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  
  document.getElementById(`tab-${tabName}`).classList.add('active');
  document.getElementById(`nav-${tabName}`).classList.add('active');
  
  if (tabName === 'dashboard') updateDashboard();
  if (tabName === 'profile') renderProfile();
}

// Update Dashboard UI
function updateDashboard() {
  if (!currentUser) return;
  const targets = currentUser.targets;
  let consumed = { calories: 0, protein: 0, carbs: 0, fats: 0, fiber: 0 };
  
  const dailyLog = currentUser.dailyLog || [];
  dailyLog.forEach(meal => {
    (meal.ingredients || []).forEach(ing => {
      const mult = (ing.weight || 0) / 100;
      consumed.calories += (ing.calories || 0) * mult;
      consumed.protein += (ing.protein || 0) * mult;
      consumed.carbs += (ing.carbs || 0) * mult;
      consumed.fats += (ing.fats || 0) * mult;
      consumed.fiber += (ing.fiber || 0) * mult;
    });
  });
  
  // Format variables
  consumed.calories = Math.round(consumed.calories);
  consumed.protein = Math.round(consumed.protein);
  consumed.carbs = Math.round(consumed.carbs);
  consumed.fats = Math.round(consumed.fats);
  consumed.fiber = Math.round(consumed.fiber);
  
  // Update numbers
  document.getElementById('cal-consumed').innerText = consumed.calories;
  document.getElementById('cal-remain').innerText = `из ${targets.calories}`;
  
  document.getElementById('m-protein').innerText = `${consumed.protein}г`;
  document.getElementById('m-carbs').innerText = `${consumed.carbs}г`;
  document.getElementById('m-fats').innerText = `${consumed.fats}г`;
  document.getElementById('m-fiber').innerText = `${consumed.fiber}г`;
  
  // Progress Ring
  const pct = Math.min(100, (consumed.calories / targets.calories) * 100) || 0;
  const offset = 427 - (427 * pct) / 100;
  document.getElementById('cal-ring').style.strokeDashoffset = offset;
  
  // Progress List
  document.getElementById('pg-cal').innerText = `${consumed.calories} / ${targets.calories} ккал`;
  document.getElementById('pgb-cal').style.width = `${pct}%`;
  
  const protPct = Math.min(100, (consumed.protein / targets.protein) * 100) || 0;
  document.getElementById('pg-prot').innerText = `${consumed.protein} / ${targets.protein}г`;
  document.getElementById('pgb-prot').style.width = `${protPct}%`;
  
  const carbsPct = Math.min(100, (consumed.carbs / targets.carbs) * 100) || 0;
  document.getElementById('pg-carbs').innerText = `${consumed.carbs} / ${targets.carbs}г`;
  document.getElementById('pgb-carbs').style.width = `${carbsPct}%`;
  
  const fatsPct = Math.min(100, (consumed.fats / targets.fats) * 100) || 0;
  document.getElementById('pg-fats').innerText = `${consumed.fats} / ${targets.fats}г`;
  document.getElementById('pgb-fats').style.width = `${fatsPct}%`;
  
  // Render meal list
  const listEl = document.getElementById('meal-list');
  if (dailyLog.length === 0) {
    listEl.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">🍽️</div>
        <div>Дневник пуст. Отсканируйте первое блюдо!</div>
      </div>`;
  } else {
    listEl.innerHTML = "";
    dailyLog.forEach((meal, idx) => {
      let mealCal = 0;
      (meal.ingredients || []).forEach(ing => {
        mealCal += (ing.calories || 0) * ((ing.weight || 0) / 100);
      });
      
      const item = document.createElement('div');
      item.className = 'meal-item';
      
      // Default image if path is wrong or missing
      const imgSrc = meal.image ? meal.image : 'images/uploads/default.jpg';
      
      item.innerHTML = `
        <img class="meal-thumb" src="${imgSrc}" alt="${meal.name}" onerror="this.src='https://images.unsplash.com/photo-1498837167922-ddd27525d352?w=100&auto=format&fit=crop&q=60'">
        <div class="meal-details">
          <div class="meal-name">${meal.name}</div>
          <div class="meal-meta">${meal.time || '--:--'}</div>
        </div>
        <div class="meal-cal">${Math.round(mealCal)} ккал</div>
        <button class="meal-del" onclick="deleteMeal(${idx})">🗑️</button>
      `;
      listEl.appendChild(item);
    });
  }
}

// Clear log
function clearLog() {
  if (!currentUser) return;
  if (confirm("Вы уверены, что хотите очистить дневник за сегодня?")) {
    currentUser.dailyLog = [];
    syncUser();
    updateDashboard();
    showToast("Дневник питания очищен.");
  }
}

// Delete single meal
function deleteMeal(idx) {
  if (!currentUser) return;
  currentUser.dailyLog.splice(idx, 1);
  syncUser();
  updateDashboard();
  showToast("Прием пищи удален.");
}

// Trigger file input scan
function triggerScan() {
  document.getElementById('photo-input').click();
}

// Handle selected photo file
function handlePhoto(event) {
  const file = event.target.files[0];
  if (!file) return;
  
  const reader = new FileReader();
  reader.onload = function(e) {
    const base64 = e.target.result.split(',')[1];
    base64Image = e.target.result; // Data URL for display
    
    // Hide upload zone, show loading spinner
    document.getElementById('scan-zone').style.display = 'none';
    document.getElementById('scan-loading').style.display = 'block';
    
    // Call Gemini API
    callGeminiAPI(base64);
  };
  reader.readAsDataURL(file);
}

// Call local proxy endpoint to use Gemini
function callGeminiAPI(base64Data) {
  const promptText = `Анализируй это изображение еды. Твоя главная задача — максимально точно оценить вес (в граммах) каждого ингредиента на тарелке и его пищевую ценность на 100г.
Оценивай по масштабам тарелки и приборов.
Выдай JSON объект следующей структуры:
{
  "name": "Название блюда на русском",
  "estimation_reasoning": "Объяснение того, какие масштабы и ориентиры на фото использовал для оценки веса каждого продукта",
  "ingredients": [
    { 
      "name": "Название ингредиента на русском", 
      "weight": примерный_вес_в_граммах,
      "calories": калории_на_100г,
      "protein": белки_на_100г,
      "carbs": углеводы_на_100г,
      "fats": жиры_на_100г,
      "fiber": клетчатка_на_100г
    }
  ]
}
Пиши только чистый JSON без разметки markdown (без \`\`\`json).`;

  const payload = {
    contents: [{
      parts: [
        { text: promptText },
        { inlineData: { mimeType: 'image/jpeg', data: base64Data } }
      ]
    }],
    generationConfig: {
      responseMimeType: 'application/json'
    }
  };

  fetch('/api/gemini', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
  .then(res => {
    if (!res.ok) throw new Error("API returned status " + res.status);
    return res.json();
  })
  .then(data => {
    // Check structure
    let text = data.candidates[0].content.parts[0].text.trim();
    if (text.startsWith("```json")) {
      text = text.substring(7);
    }
    if (text.endsWith("```")) {
      text = text.substring(0, text.length - 3);
    }
    text = text.trim();
    
    const firstBrace = text.indexOf("{");
    const lastBrace = text.lastIndexOf("}");
    if (firstBrace !== -1 && lastBrace !== -1) {
      text = text.substring(firstBrace, lastBrace + 1);
    }
    
    const parsed = JSON.parse(text);
    displayScanResult(parsed);
  })
  .catch(err => {
    console.error("Gemini API error:", err);
    showToast("Не удалось распознать блюдо. Попробуйте другое фото.");
    rescan();
  });
}

// Display AI analysis results
function displayScanResult(result) {
  currentScanResult = result;
  
  document.getElementById('scan-loading').style.display = 'none';
  document.getElementById('scan-result').style.display = 'block';
  
  // Set image
  document.getElementById('result-img').src = base64Image;
  document.getElementById('result-name').innerText = result.name;
  
  // Totals calculations
  let totalCal = 0, totalP = 0, totalC = 0, totalF = 0, totalFib = 0;
  
  const ingListEl = document.getElementById('ingredients-list');
  ingListEl.innerHTML = "";
  
  result.ingredients.forEach(ing => {
    const mult = ing.weight / 100;
    const itemCal = ing.calories * mult;
    totalCal += itemCal;
    totalP += ing.protein * mult;
    totalC += ing.carbs * mult;
    totalF += ing.fats * mult;
    totalFib += ing.fiber * mult;
    
    const ingRow = document.createElement('div');
    ingRow.className = 'ing-item';
    ingRow.innerHTML = `<span>• ${ing.name}</span><span>${ing.weight}г (~${Math.round(itemCal)} ккал)</span>`;
    ingListEl.appendChild(ingRow);
  });
  
  totalCal = Math.round(totalCal);
  totalP = Math.round(totalP);
  totalC = Math.round(totalC);
  totalF = Math.round(totalF);
  totalFib = Math.round(totalFib);
  
  document.getElementById('r-cal').innerText = totalCal;
  document.getElementById('r-prot').innerText = `${totalP}г`;
  document.getElementById('r-carbs').innerText = `${totalC}г`;
  document.getElementById('r-fats').innerText = `${totalF}г`;
  
  // Coach advice
  let advice = "";
  if (totalCal > 800) {
    advice += "🍽️ Очень сытный прием пищи! Убедитесь, что он вписывается в суточный лимит. ";
  }
  if (totalP < 12) {
    advice += "🍳 Мало белка. Попробуйте добавить яйцо, куриное филе или греческий йогурт. ";
  } else if (totalP > 35) {
    advice += "💪 Отличная порция белка для построения мышц! ";
  }
  if (totalFib < 3) {
    advice += "🥦 Добавьте клетчатки (овощи, зелень, брокколи) в следующий раз. ";
  }
  if (!advice) {
    advice = "🌟 Идеальный сбалансированный прием пищи! Отличный выбор для здорового питания.";
  }
  document.getElementById('coach-text').innerText = advice;
  
  // Reasoning
  document.getElementById('reasoning-text').innerText = result.estimation_reasoning || "Оценено на основе масштаба блюда";
}

// Reset scan tab
function rescan() {
  document.getElementById('scan-result').style.display = 'none';
  document.getElementById('scan-loading').style.display = 'none';
  document.getElementById('scan-zone').style.display = 'flex';
  document.getElementById('photo-input').value = "";
  currentScanResult = null;
  base64Image = null;
}

// Add scanned meal to daily log
function addToLog() {
  if (!currentUser || !currentScanResult) return;
  
  const now = new Date();
  const timeStr = now.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
  
  const newMeal = {
    name: currentScanResult.name,
    time: timeStr,
    image: base64Image, // Save the uploaded photo in base64
    ingredients: currentScanResult.ingredients
  };
  
  currentUser.dailyLog.push(newMeal);
  
  // Save scan count
  currentUser.scans.push(Date.now());
  
  syncUser();
  showToast("Блюдо добавлено в дневник!");
  
  // Switch to dashboard tab
  rescan();
  switchTab('dashboard');
}

// Render Profile
function renderProfile() {
  if (!currentUser) return;
  
  // Avatar
  const name = currentUser.name || "Пользователь";
  const avatarEl = document.getElementById('profile-avatar');
  if (currentUser.avatarUrl) {
    avatarEl.innerHTML = `<img src="${currentUser.avatarUrl}" style="width:100%;height:100%;border-radius:50%;object-fit:cover;display:block;">`;
    avatarEl.style.background = "none";
  } else {
    avatarEl.innerText = name.charAt(0).toUpperCase();
    avatarEl.style.background = "";
  }
  document.getElementById('profile-name').innerText = name;
  document.getElementById('profile-sub').innerText = `VK ID: ${userId}`;
  
  // BMI
  const h_m = currentUser.height / 100;
  const bmi = (currentUser.weight / (h_m * h_m)).toFixed(1);
  document.getElementById('bmi-value').innerText = bmi;
  
  let status = "";
  if (bmi < 18.5) status = "Дефицит веса 🟡";
  else if (bmi < 25) status = "Норма веса 🟢";
  else if (bmi < 30) status = "Избыточный вес 🟡";
  else status = "Ожирение 🔴";
  document.getElementById('bmi-status').innerText = status;
  
  // Parameters
  document.getElementById('p-weight').innerText = `${currentUser.weight} кг`;
  document.getElementById('p-height').innerText = `${currentUser.height} см`;
  document.getElementById('p-age').innerText = `${currentUser.age} лет`;
  
  let actText = "";
  if (currentUser.activity === 1.2) actText = "Малоподвижный (1.2)";
  else if (currentUser.activity === 1.375) actText = "Умеренный (1.375)";
  else if (currentUser.activity === 1.55) actText = "Средний (1.55)";
  else actText = "Высокий (1.725)";
  document.getElementById('p-activity').innerText = actText;
  
  document.getElementById('p-gender').innerText = currentUser.gender === 'male' ? 'Мужской' : 'Женский';
  
  // Targets
  const targets = currentUser.targets;
  document.getElementById('t-cal').innerText = targets.calories;
  document.getElementById('t-prot').innerText = targets.protein;
  document.getElementById('t-carbs').innerText = targets.carbs;
  document.getElementById('t-fats').innerText = targets.fats;
  
  const titleEl = document.getElementById('targets-title');
  if (titleEl) {
    titleEl.innerText = currentUser.customTargets ? "🔥 Ваши нормы (индивидуальные)" : "🔥 Ваши нормы (ИИ-расчет)";
  }
  
  // Premium
  if (currentUser.isPremium) {
    document.getElementById('premium-badge').innerText = "PREMIUM 🚀";
    document.getElementById('premium-badge').style.background = "rgba(74, 222, 128, 0.15)";
    document.getElementById('premium-badge').style.color = "#4ade80";
    document.getElementById('premium-section').style.display = 'none';
    document.getElementById('premium-active').style.display = 'flex';
  } else {
    document.getElementById('premium-badge').innerText = "FREE";
    document.getElementById('premium-badge').style.background = "rgba(167, 139, 250, 0.15)";
    document.getElementById('premium-badge').style.color = "#a78bfa";
    document.getElementById('premium-section').style.display = 'flex';
    document.getElementById('premium-active').style.display = 'none';
  }
}

// Edit Parameter Modal
function editParam(param) {
  const modal = document.getElementById('edit-modal');
  const title = document.getElementById('modal-title');
  const body = document.getElementById('modal-body');
  
  modal.style.display = 'flex';
  
  if (param === 'weight') {
    title.innerText = "Укажите ваш вес";
    body.innerHTML = `
      <input type="number" id="edit-val" class="modal-input" value="${currentUser.weight}" min="30" max="250">
      <button class="modal-save" onclick="saveParam('weight')">Сохранить</button>
    `;
  } else if (param === 'height') {
    title.innerText = "Укажите ваш рост";
    body.innerHTML = `
      <input type="number" id="edit-val" class="modal-input" value="${currentUser.height}" min="100" max="230">
      <button class="modal-save" onclick="saveParam('height')">Сохранить</button>
    `;
  } else if (param === 'age') {
    title.innerText = "Укажите ваш возраст";
    body.innerHTML = `
      <input type="number" id="edit-val" class="modal-input" value="${currentUser.age}" min="10" max="100">
      <button class="modal-save" onclick="saveParam('age')">Сохранить</button>
    `;
  } else if (param === 'gender') {
    title.innerText = "Выберите пол";
    body.innerHTML = `
      <button class="modal-option ${currentUser.gender==='male'?'selected':''}" onclick="setGender('male')">👨 Мужской</button>
      <button class="modal-option ${currentUser.gender==='female'?'selected':''}" onclick="setGender('female')">👩 Женский</button>
    `;
  } else if (param === 'activity') {
    title.innerText = "Физическая активность";
    const act = currentUser.activity;
    body.innerHTML = `
      <button class="modal-option ${act===1.2?'selected':''}" onclick="setActivity(1.2)">🛋️ Малоподвижный (офис)</button>
      <button class="modal-option ${act===1.375?'selected':''}" onclick="setActivity(1.375)">🚶 Умеренный (1-3 тренировки/нед)</button>
      <button class="modal-option ${act===1.55?'selected':''}" onclick="setActivity(1.55)">🚴 Средний (3-5 тренировок/нед)</button>
      <button class="modal-option ${act===1.725?'selected':''}" onclick="setActivity(1.725)">🏋️ Высокий (спортсмены)</button>
    `;
  }
}

// Save scalar parameter
function saveParam(param) {
  const val = parseFloat(document.getElementById('edit-val').value);
  if (!val || val <= 0) return;
  
  currentUser[param] = val;
  if (!currentUser.customTargets) {
    currentUser.targets = calculateTargets(
      currentUser.gender,
      currentUser.age,
      currentUser.height,
      currentUser.weight,
      currentUser.activity
    );
  }
  
  syncUser();
  renderProfile();
  closeModal(null, true);
  showToast("Параметры успешно сохранены!");
}

function setGender(g) {
  currentUser.gender = g;
  if (!currentUser.customTargets) {
    currentUser.targets = calculateTargets(
      currentUser.gender,
      currentUser.age,
      currentUser.height,
      currentUser.weight,
      currentUser.activity
    );
  }
  syncUser();
  renderProfile();
  closeModal(null, true);
  showToast("Пол обновлен.");
}

function setActivity(a) {
  currentUser.activity = a;
  if (!currentUser.customTargets) {
    currentUser.targets = calculateTargets(
      currentUser.gender,
      currentUser.age,
      currentUser.height,
      currentUser.weight,
      currentUser.activity
    );
  }
  syncUser();
  renderProfile();
  closeModal(null, true);
  showToast("Активность обновлена.");
}

// Close modal sheet
function closeModal(e, force = false) {
  if (force || e.target.classList.contains('modal-overlay')) {
    document.getElementById('edit-modal').style.display = 'none';
  }
}

// Upgrade to Premium
function upgradeToPremium() {
  if (!currentUser) return;
  
  if (confirm("Вы хотите подключить тариф Безлимит за 490 ₽/мес?\n(Оплата будет симулирована для теста)")) {
    currentUser.isPremium = true;
    syncUser();
    renderProfile();
    showToast("Поздравляем! Безлимит активирован! 🚀");
  }
}

// Toast helper
function showToast(text) {
  const toast = document.getElementById('toast');
  toast.innerText = text;
  toast.classList.add('show');
  setTimeout(() => {
    toast.classList.remove('show');
  }, 2500);
}

// Custom targets editing handlers
function editTargets() {
  const modal = document.getElementById('edit-modal');
  const title = document.getElementById('modal-title');
  const body = document.getElementById('modal-body');
  
  modal.style.display = 'flex';
  title.innerText = "Настройка норм КБЖУ";
  
  const currentCal = currentUser.targets.calories;
  const currentProt = currentUser.targets.protein;
  const currentCarbs = currentUser.targets.carbs;
  const currentFats = currentUser.targets.fats;
  
  body.innerHTML = `
    <div style="display: flex; flex-direction: column; gap: 12px; width: 100%; margin-bottom: 16px; text-align: left;">
      <div>
        <label style="font-size: 12px; display: block; margin-bottom: 4px; color:#888;">Калории (ккал)</label>
        <input type="number" id="edit-t-cal" class="modal-input" value="${currentCal}" min="500" max="10000" style="margin-bottom:0; width:100%; box-sizing:border-box;">
      </div>
      <div>
        <label style="font-size: 12px; display: block; margin-bottom: 4px; color:#888;">Белки (г)</label>
        <input type="number" id="edit-t-prot" class="modal-input" value="${currentProt}" min="0" max="1000" style="margin-bottom:0; width:100%; box-sizing:border-box;">
      </div>
      <div>
        <label style="font-size: 12px; display: block; margin-bottom: 4px; color:#888;">Углеводы (г)</label>
        <input type="number" id="edit-t-carbs" class="modal-input" value="${currentCarbs}" min="0" max="2000" style="margin-bottom:0; width:100%; box-sizing:border-box;">
      </div>
      <div>
        <label style="font-size: 12px; display: block; margin-bottom: 4px; color:#888;">Жиры (г)</label>
        <input type="number" id="edit-t-fats" class="modal-input" value="${currentFats}" min="0" max="500" style="margin-bottom:0; width:100%; box-sizing:border-box;">
      </div>
    </div>
    <div style="display: flex; gap: 10px; width: 100%; box-sizing:border-box;">
      <button class="modal-save" onclick="saveCustomTargets()" style="flex: 1; margin: 0; padding: 12px;">Сохранить</button>
      <button class="modal-save" onclick="resetTargetsToFormula()" style="flex: 1; margin: 0; padding: 12px; background: #333; color: #fff; border: 1px solid rgba(255,255,255,0.08);">Сбросить</button>
    </div>
  `;
}

function saveCustomTargets() {
  const cal = parseInt(document.getElementById('edit-t-cal').value);
  const prot = parseInt(document.getElementById('edit-t-prot').value);
  const carbs = parseInt(document.getElementById('edit-t-carbs').value);
  const fats = parseInt(document.getElementById('edit-t-fats').value);
  
  if (isNaN(cal) || isNaN(prot) || isNaN(carbs) || isNaN(fats)) {
    alert("Заполните все поля числовыми значениями.");
    return;
  }
  
  currentUser.targets = {
    calories: cal,
    protein: prot,
    carbs: carbs,
    fats: fats,
    bmr: currentUser.targets.bmr || Math.round((currentUser.weight * 10) + (currentUser.height * 6.25) - (currentUser.age * 5))
  };
  currentUser.customTargets = true;
  
  syncUser();
  renderProfile();
  closeModal(null, true);
  showToast("Индивидуальные нормы сохранены!");
}

function resetTargetsToFormula() {
  currentUser.customTargets = false;
  currentUser.targets = calculateTargets(
    currentUser.gender,
    currentUser.age,
    currentUser.height,
    currentUser.weight,
    currentUser.activity
  );
  syncUser();
  renderProfile();
  closeModal(null, true);
  showToast("Нормы сброшены к расчетным.");
}

// Avatar upload handlers
function triggerAvatarUpload() {
  document.getElementById('avatar-file-input').click();
}

function handleAvatarUpload(event) {
  const file = event.target.files[0];
  if (!file) return;
  
  compressAndSaveAvatar(file, (compressedBase64) => {
    if (!currentUser) return;
    currentUser.avatarUrl = compressedBase64;
    syncUser();
    renderProfile();
    showToast("Аватар успешно обновлен!");
  });
}

function compressAndSaveAvatar(file, callback) {
  const reader = new FileReader();
  reader.onload = function(e) {
    const img = new Image();
    img.onload = function() {
      const canvas = document.createElement('canvas');
      const MAX_WIDTH = 150;
      const MAX_HEIGHT = 150;
      let width = img.width;
      let height = img.height;
      
      if (width > height) {
        if (width > MAX_WIDTH) {
          height *= MAX_WIDTH / width;
          width = MAX_WIDTH;
        }
      } else {
        if (height > MAX_HEIGHT) {
          width *= MAX_HEIGHT / height;
          height = MAX_HEIGHT;
        }
      }
      
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(img, 0, 0, width, height);
      
      const compressedDataUrl = canvas.toDataURL('image/jpeg', 0.7);
      callback(compressedDataUrl);
    };
    img.src = e.target.result;
  };
  reader.readAsDataURL(file);
}
