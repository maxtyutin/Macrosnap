# -*- coding: utf-8 -*-
import os
import time
import urllib.request
import urllib.parse
import json
import base64
import uuid
import datetime

# Global memory cache for temporary meal states before saving
temp_meals = {}

DB_FILE = "users_data.json"

# Default Gemini API Key (obfuscated as in frontend)
PART_A = "AIzaSyBrjH5Jtqm98P"
PART_B = "dV3431eLY6caxHXFG_Nd0"
DEFAULT_GEMINI_KEY = PART_A + PART_B

def load_env():
    """Loads environment variables from .env file if it exists."""
    if os.path.exists(".env"):
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    parts = line.strip().split("=", 1)
                    k = parts[0].strip()
                    v = parts[1].strip().strip('"').strip("'")
                    os.environ[k] = v

# Initialize env
load_env()

def get_bot_token():
    return os.environ.get("TELEGRAM_BOT_TOKEN", "")

def get_mini_app_url():
    return os.environ.get("TELEGRAM_MINI_APP_URL", "")

def get_gemini_key():
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key.strip():
        return DEFAULT_GEMINI_KEY
    return key

def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[BOT-DB] Error reading DB: {e}")
        return {}

def save_db(db):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[BOT-DB] Error writing DB: {e}")

def make_request(url, data=None, headers=None, method='POST'):
    if headers is None:
        headers = {}
    
    # Simple handler for POST data
    req_data = data
    if isinstance(data, dict):
        req_data = urllib.parse.urlencode(data).encode('utf-8')
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
    
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"[BOT-API] Request failed to {url}: {e}")
        return None

def telegram_api(token, method, data=None):
    url = f"https://api.telegram.org/bot{token}/{method}"
    headers = {}
    req_data = None
    
    if data:
        req_data = json.dumps(data).encode('utf-8')
        headers['Content-Type'] = 'application/json'
        
    return make_request(url, data=req_data, headers=headers, method='POST')

def download_telegram_file(token, file_path):
    """Downloads a file from Telegram and saves it to images/uploads/"""
    os.makedirs("images/uploads", exist_ok=True)
    file_url = f"https://api.telegram.org/file/bot{token}/{file_path}"
    local_filename = f"images/uploads/tg_{uuid.uuid4().hex}.jpg"
    
    try:
        req = urllib.request.Request(file_url)
        with urllib.request.urlopen(req) as response:
            with open(local_filename, "wb") as f:
                f.write(response.read())
        return local_filename
    except Exception as e:
        print(f"[BOT-DOWNLOAD] Error downloading file: {e}")
        return None

def call_gemini_vision(img_path):
    """Sends image to Gemini Vision API for food classification and calories estimation"""
    try:
        with open(img_path, "rb") as f:
            img_data = f.read()
        
        base64_data = base64.b64encode(img_data).decode('utf-8')
        gemini_key = get_gemini_key()
        
        prompt_text = """Анализируй это изображение еды. Твоя главная задача — максимально точно оценить вес (в граммах) каждого ингредиента на тарелке и его пищевую ценность на 100г.
Для этого проведи визуальную оценку по следующим критериям:
1. Найди ориентиры масштаба (вилка, ложка, стакан, текстура стола, размер тарелки).
2. Оцени диаметр тарелки (стандартная обеденная тарелка ~24-26 см, десертная ~18-20 см).
3. Оцени объем и толщину каждого продукта (например, толщину куска пиццы, высоту горки риса).
4. Учти плотность (зелень объемная, но легкая: 10-20г; сыр и мясо тяжелые: 100-200г).

Выдай JSON объект следующей структуры:
{
  "name": "Название блюда на русском",
  "estimation_reasoning": "Короткое объяснение на русском, какие масштабы и ориентиры на фото ИИ использовал для оценки веса (например: ориентир на размер грибов и бортик пиццы, тарелка около 25см, плотность теста...)",
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
Пиши только чистый JSON без разметки markdown (без ```json)."""

        models_to_try = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-3.5-flash"]
        res_data = None
        
        for model_name in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={gemini_key}"
            print(f"[BOT-GEMINI] Trying Gemini model: {model_name}")
            
            payload = {
                "contents": [{
                    "parts": [
                        { "text": prompt_text },
                        {
                            "inlineData": {
                                "mimeType": "image/jpeg",
                                "data": base64_data
                            }
                        }
                    ]
                }],
                "generationConfig": {
                    "responseMimeType": "application/json"
                }
            }
            
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            
            try:
                with urllib.request.urlopen(req, timeout=30) as response:
                    res_data = json.loads(response.read().decode('utf-8'))
                    print(f"[BOT-GEMINI] Successfully received response from model: {model_name}")
                    break
            except Exception as model_err:
                print(f"[BOT-GEMINI] Model {model_name} failed: {model_err}")
                continue
                
        if not res_data:
            print("[BOT-GEMINI] All Gemini models failed.")
            return None
            
        text_response = res_data['candidates'][0]['content']['parts'][0]['text']
        
        # Clean markdown JSON block wrappers if any
        clean_text = text_response.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        clean_text = clean_text.strip()
        
        # Handle brackets wrapping
        first_brace = clean_text.find("{")
        last_brace = clean_text.rfind("}")
        if first_brace != -1 and last_brace != -1:
            clean_text = clean_text[first_brace:last_brace+1]
            
        return json.loads(clean_text)
    except Exception as e:
        print(f"[BOT-GEMINI] Error parsing response or calling Gemini: {e}")
        return None

def generate_coach_recommendation(calories, protein, carbs, fats, fiber):
    text = ""
    if calories > 800:
        text += "🍽️ *Ого, сытный прием пищи!* Это отличный источник энергии, но убедитесь, что он укладывается в вашу суточную норму. "
    
    if protein < 12:
        text += "🍳 *Добавьте белка!* Его маловато в этой тарелке. Белок необходим для сытости и мышц. Добавьте порцию куриного филе, рыбы или греческого йогурта в следующий раз. "
    elif protein > 35:
        text += "💪 *Отличная белковая бомба!* Это строительный материал для мышц. Запивайте прием пищи водой для лучшего усвоения белка. "
        
    if fiber < 3:
        text += "🥦 *Добавьте больше клетчатки!* Она критически важна для правильного пищеварения и продления сытости. Добавьте огурец, шпинат, брокколи, зелень или горсть свежих ягод к этому блюду. "
    elif fiber > 8:
        text += "🥗 *Замечательный уровень клетчатки!* Ваше пищеварение и кишечник скажут вам спасибо. Отличная работа над плотностью нутриентов! "
        
    if fats > 30:
        text += "🥑 *Многовато жиров.* Полезные растительные жиры важны для гормонального здоровья, но следите за общим балансом калорий. Постарайтесь сделать следующий прием пищи более постным. "
        
    if not text:
        text = "🌟 *Прекрасный сбалансированный прием пищи!* Белки, жиры, углеводы и клетчатка находятся в хорошем отношении. Отличный выбор для здорового рациона!"
        
    return text

def calculate_user_calorie_goal(gender, age, height, weight, activity_multiplier):
    """BMR and Calorie Target Calculation based on Mifflin-St Jeor formula"""
    if gender == "male":
        bmr = (10 * weight) + (6.25 * height) - (5 * age) + 5
    else:
        bmr = (10 * weight) + (6.25 * height) - (5 * age) - 161
        
    tdee = round(bmr * activity_multiplier)
    
    protein_val = round((tdee * 0.30) / 4) # 30% of total calories
    carbs_val = round((tdee * 0.45) / 4)   # 45% of total calories
    fats_val = round((tdee * 0.25) / 9)    # 25% of total calories
    fiber_val = min(40, max(20, round((tdee * 14) / 1000))) # 14g per 1000 kcal
    
    return {
        "bmr": round(bmr),
        "calories": tdee,
        "protein": protein_val,
        "carbs": carbs_val,
        "fats": fats_val,
        "fiber": fiber_val
    }

def get_webapp_button(text, url):
    if not url:
        url = "https://localhost"
    if "t.me/" in url:
        return {"text": text, "url": url}
    else:
        return {"text": text, "web_app": {"url": url}}

def check_user_scans(user):
    """Checks if the user has scans left (limit 5 for free users)"""
    if user.get("isPremium", False):
        return True, 0, 0
    
    thirty_days_ago = time.time() - 30 * 24 * 60 * 60
    scans = user.get("scans", [])
    
    # Filter scans in last 30 days
    recent_scans = [t for t in scans if t > thirty_days_ago]
    user["scans"] = recent_scans
    
    if len(recent_scans) >= 5:
        return False, len(recent_scans), 5
    return True, len(recent_scans), 5

def get_default_keyboard():
    """Returns the persistent bottom reply menu keyboard"""
    mini_app_url = get_mini_app_url()
    keyboard = [
        [
            {"text": "📊 Дашборд"},
            {"text": "📸 Сканировать"}
        ],
        [
            {"text": "👤 Профиль"}
        ]
    ]
    if mini_app_url:
        keyboard.insert(0, [{"text": "🚀 Открыть Mini App", "web_app": {"url": mini_app_url}}])
        
    return {
        "keyboard": keyboard,
        "resize_keyboard": True,
        "one_time_keyboard": False
    }

def process_update(token, update):
    if "message" in update:
        message = update["message"]
        chat_id = message["chat"]["id"]
        user_info = message.get("from", {})
        first_name = user_info.get("first_name", "Пользователь")
        user_id = f"tg_{user_info.get('id', '')}"
        
        # Load DB
        db = load_db()
        user = db.get(user_id)
        
        # Check if user needs initialization
        if not user:
            user = {
                "email": user_id,
                "name": first_name,
                "gender": "male",
                "age": 25,
                "height": 175,
                "weight": 70,
                "activity": 1.2,
                "state": "",
                "targets": calculate_user_calorie_goal("male", 25, 175, 70, 1.2),
                "isPremium": False,
                "scans": [],
                "dailyLog": []
            }
            db[user_id] = user
            save_db(db)
            
        # Ensure state and other keys exist (migrations)
        if "state" not in user:
            user["state"] = ""
        if "dailyLog" not in user:
            user["dailyLog"] = []
            
        # 1. State machine handling (conversational parameters setup)
        if user["state"] and "text" in message:
            text = message["text"].strip()
            state = user["state"]
            
            # Cancel state
            if text.lower() in ["отмена", "/cancel", "назад"]:
                user["state"] = ""
                db[user_id] = user
                save_db(db)
                telegram_api(token, "sendMessage", {
                    "chat_id": chat_id,
                    "text": "❌ Корректировка отменена.",
                    "reply_markup": get_default_keyboard()
                })
                return
                
            if state == "wait_weight":
                try:
                    val = float(text)
                    if val < 30 or val > 200:
                        raise ValueError()
                    user["weight"] = val
                    user["targets"] = calculate_user_calorie_goal(
                        user.get("gender", "male"),
                        user.get("age", 25),
                        user.get("height", 175),
                        val,
                        user.get("activity", 1.2)
                    )
                    user["state"] = ""
                    db[user_id] = user
                    save_db(db)
                    telegram_api(token, "sendMessage", {
                        "chat_id": chat_id,
                        "text": f"✅ Ваш вес обновлен до *{val} кг*!\n🔥 Суточная норма калорий пересчитана: *{user['targets']['calories']} ккал*.",
                        "parse_mode": "Markdown",
                        "reply_markup": get_default_keyboard()
                    })
                except ValueError:
                    telegram_api(token, "sendMessage", {
                        "chat_id": chat_id,
                        "text": "⚠️ Пожалуйста, введите корректный вес числом от 30 до 200 (например: 72.5) или отправьте слово 'отмена'."
                    })
                return
                
            elif state == "wait_height":
                try:
                    val = int(text)
                    if val < 100 or val > 230:
                        raise ValueError()
                    user["height"] = val
                    user["targets"] = calculate_user_calorie_goal(
                        user.get("gender", "male"),
                        user.get("age", 25),
                        val,
                        user.get("weight", 70),
                        user.get("activity", 1.2)
                    )
                    user["state"] = ""
                    db[user_id] = user
                    save_db(db)
                    telegram_api(token, "sendMessage", {
                        "chat_id": chat_id,
                        "text": f"✅ Ваш рост обновлен до *{val} см*!\n🔥 Суточная норма калорий пересчитана: *{user['targets']['calories']} ккал*.",
                        "parse_mode": "Markdown",
                        "reply_markup": get_default_keyboard()
                    })
                except ValueError:
                    telegram_api(token, "sendMessage", {
                        "chat_id": chat_id,
                        "text": "⚠️ Пожалуйста, введите корректный рост целым числом от 100 до 230 (например: 178) или отправьте слово 'отмена'."
                    })
                return
                
            elif state == "wait_age":
                try:
                    val = int(text)
                    if val < 10 or val > 100:
                        raise ValueError()
                    user["age"] = val
                    user["targets"] = calculate_user_calorie_goal(
                        user.get("gender", "male"),
                        val,
                        user.get("height", 175),
                        user.get("weight", 70),
                        user.get("activity", 1.2)
                    )
                    user["state"] = ""
                    db[user_id] = user
                    save_db(db)
                    telegram_api(token, "sendMessage", {
                        "chat_id": chat_id,
                        "text": f"✅ Ваш возраст обновлен до *{val} лет*!\n🔥 Суточная норма калорий пересчитана: *{user['targets']['calories']} ккал*.",
                        "parse_mode": "Markdown",
                        "reply_markup": get_default_keyboard()
                    })
                except ValueError:
                    telegram_api(token, "sendMessage", {
                        "chat_id": chat_id,
                        "text": "⚠️ Пожалуйста, введите корректный возраст целым числом от 10 до 100 (например: 28) или отправьте слово 'отмена'."
                    })
                return
        
        # 2. Text command / button inputs
        if "text" in message:
            text = message["text"].strip()
            
            if text == "/start":
                welcome_msg = (
                    f"Привет, {first_name}! 🍎\n\n"
                    "Я *MacroSnap AI* — твой умный трекер питания и ИИ-коуч.\n\n"
                    "📸 *Как сканировать?*\n"
                    "Просто пришли мне *фото своей тарелки с едой*. Наш ИИ распознает ингредиенты, вес, калории и БЖУ, а также даст ценные советы!\n\n"
                    "📊 Используйте меню ниже для просмотра Дашборда и настройки Профиля прямо в чате!"
                )
                telegram_api(token, "sendMessage", {
                    "chat_id": chat_id,
                    "text": welcome_msg,
                    "parse_mode": "Markdown",
                    "reply_markup": get_default_keyboard()
                })
                
            elif text == "📊 Дашборд":
                daily_log = user.get("dailyLog", [])
                
                # Calculate current daily totals
                total_cal = 0
                total_p = 0
                total_c = 0
                total_f = 0
                total_fb = 0
                
                for meal in daily_log:
                    for ing in meal.get("ingredients", []):
                        factor = ing.get("weight", 100) / 100.0
                        total_cal += ing.get("calories", 0) * factor
                        total_p += ing.get("protein", 0) * factor
                        total_c += ing.get("carbs", 0) * factor
                        total_f += ing.get("fats", 0) * factor
                        total_fb += ing.get("fiber", 0) * factor
                        
                total_cal = round(total_cal)
                total_p = round(total_p, 1)
                total_c = round(total_c, 1)
                total_f = round(total_f, 1)
                total_fb = round(total_fb, 1)
                
                targets = user.get("targets", calculate_user_calorie_goal("male", 25, 175, 70, 1.2))
                
                rem_cal = targets["calories"] - total_cal
                rem_text = f"осталось *{rem_cal} ккал*" if rem_cal >= 0 else f"превышено на *{abs(rem_cal)} ккал*"
                
                # Format meal list
                meal_lines = []
                for idx, meal in enumerate(daily_log):
                    meal_cal = 0
                    for ing in meal.get("ingredients", []):
                        meal_cal += ing.get("calories", 0) * (ing.get("weight", 100) / 100.0)
                    meal_lines.append(f"{idx+1}. *{meal['name']}* ({meal.get('time', '--:--')}) — {round(meal_cal)} ккал")
                
                meal_log_str = "\n".join(meal_lines) if meal_lines else "_Дневник за сегодня пуст_"
                
                dash_msg = (
                    f"📊 *Дневник питания за сегодня:*\n\n"
                    f"🔥 Калории: *{total_cal}* из *{targets['calories']} ккал* ({rem_text})\n"
                    f"🥩 Белки: *{total_p}* из *{targets['protein']}г*\n"
                    f"🌾 Углеводы: *{total_c}* из *{targets['carbs']}г*\n"
                    f"💧 Жиры: *{total_f}* из *{targets['fats']}г*\n"
                    f"🥦 Клетчатка: *{total_fb}* из *{targets['fiber']}г*\n\n"
                    f"🍽️ *Список приемов пищи:*\n{meal_log_str}"
                )
                
                keyboard = {
                    "inline_keyboard": [
                        [
                            {"text": "🗑️ Очистить дневник", "callback_data": "clear_log"}
                        ]
                    ]
                }
                
                telegram_api(token, "sendMessage", {
                    "chat_id": chat_id,
                    "text": dash_msg,
                    "parse_mode": "Markdown",
                    "reply_markup": keyboard
                })
                
            elif text == "📸 Сканировать":
                scan_msg = (
                    "📸 *Готовы отсканировать ваше блюдо?*\n\n"
                    "Просто сфотографируйте еду и *отправьте фото прямо в этот чат*!\n\n"
                    "ИИ Gemini моментально выполнит:\n"
                    "1. Определение ингредиентов по визуальным признакам.\n"
                    "2. Расчет ориентировочного веса с учетом масштабов столовых приборов/тарелки.\n"
                    "3. Расчет калорий и баланса БЖУ.\n"
                    "4. Подготовит рекомендации от ИИ-коуча."
                )
                telegram_api(token, "sendMessage", {
                    "chat_id": chat_id,
                    "text": scan_msg,
                    "parse_mode": "Markdown"
                })
                
            elif text == "👤 Профиль":
                targets = user.get("targets", calculate_user_calorie_goal("male", 25, 175, 70, 1.2))
                weight = user.get("weight", 70)
                height = user.get("height", 175)
                age = user.get("age", 25)
                gender = "Мужской" if user.get("gender") == "male" else "Женский"
                
                # Calculate BMI
                h_m = height / 100.0
                bmi = round(weight / (h_m * h_m), 1)
                
                if bmi < 18.5:
                    bmi_status = "Дефицит массы 🟡"
                elif bmi < 25:
                    bmi_status = "Норма 🟢"
                elif bmi < 30:
                    bmi_status = "Избыточный вес 🟡"
                else:
                    bmi_status = "Ожирение 🔴"
                
                # Premium status
                is_premium = user.get("isPremium", False)
                premium_str = "Безлимитный (Premium) 🚀" if is_premium else "Бесплатный (5 сканов/мес) 🆓"
                
                scans_count = len(user.get("scans", []))
                scans_str = "Использовано без ограничений" if is_premium else f"{scans_count} / 5 сканов"
                
                prof_msg = (
                    f"👤 *Ваш профиль и параметры:*\n\n"
                    f"• Имя: *{user.get('name', 'Пользователь')}*\n"
                    f"• Пол: *{gender}* | Возраст: *{age} лет*\n"
                    f"• Рост: *{height} см* | Вес: *{weight} кг*\n"
                    f"• ИМТ (Индекс массы тела): *{bmi}* ({bmi_status})\n\n"
                    f"🔥 *Ваши ИИ-нормы (Миффлин-Сан Жеор):*\n"
                    f"• Калории: *{targets['calories']} ккал*\n"
                    f"• Белки: *{targets['protein']}г* | Углеводы: *{targets['carbs']}г*\n"
                    f"• Жиры: *{targets['fats']}г* | Клетчатка: *{targets['fiber']}г*\n\n"
                    f"👑 *Статус подписки:* {premium_str}\n"
                    f"📊 *ИИ-сканирования:* {scans_str}"
                )
                
                keyboard = {
                    "inline_keyboard": [
                        [
                            {"text": "⚖️ Изменить Вес", "callback_data": "edit_weight"},
                            {"text": "📏 Изменить Рост", "callback_data": "edit_height"}
                        ],
                        [
                            {"text": "🎂 Изменить Возраст", "callback_data": "edit_age"},
                            {"text": "🏃 Активность", "callback_data": "edit_activity"}
                        ],
                        [
                            {"text": "🚀 Подключить Безлимит за 490 ₽", "callback_data": "edit_premium"}
                        ]
                    ]
                }
                
                # Check if premium button is redundant
                if is_premium:
                    keyboard["inline_keyboard"].pop() # Remove premium payment row
                    
                telegram_api(token, "sendMessage", {
                    "chat_id": chat_id,
                    "text": prof_msg,
                    "parse_mode": "Markdown",
                    "reply_markup": keyboard
                })
        
        # 3. Photo processing
        elif "photo" in message:
            allowed, count, limit_max = check_user_scans(user)
            if not allowed:
                limit_msg = (
                    "🚫 *Лимит бесплатных сканирований превышен!*\n\n"
                    f"Вы израсходовали лимит в {limit_max} сканирований за этот месяц.\n"
                    "Оформите *Безлимит* прямо в профиле бота, чтобы пользоваться ИИ без ограничений!"
                )
                keyboard = {
                    "inline_keyboard": [
                        [
                            {"text": "🚀 Перейти на Безлимит", "callback_data": "edit_premium"}
                        ]
                    ]
                }
                telegram_api(token, "sendMessage", {
                    "chat_id": chat_id,
                    "text": limit_msg,
                    "parse_mode": "Markdown",
                    "reply_markup": keyboard
                })
                return

            # Keep loading message
            loading_res = telegram_api(token, "sendMessage", {
                "chat_id": chat_id,
                "text": "🔍 *Считываю фото и запускаю нейросеть Gemini...* Пожалуйста, подождите.",
                "parse_mode": "Markdown"
            })
            
            loading_msg_id = loading_res.get("result", {}).get("message_id") if loading_res else None
            
            photo = message["photo"][-1]
            file_id = photo["file_id"]
            
            # 1. Get file path
            file_info = telegram_api(token, "getFile", {"file_id": file_id})
            if not file_info or not file_info.get("ok"):
                if loading_msg_id:
                    telegram_api(token, "deleteMessage", {"chat_id": chat_id, "message_id": loading_msg_id})
                telegram_api(token, "sendMessage", {
                    "chat_id": chat_id,
                    "text": "❌ Не удалось получить файл с серверов Telegram."
                })
                return
                
            file_path = file_info["result"]["file_path"]
            
            # 2. Download file locally
            img_path = download_telegram_file(token, file_path)
            if not img_path:
                if loading_msg_id:
                    telegram_api(token, "deleteMessage", {"chat_id": chat_id, "message_id": loading_msg_id})
                telegram_api(token, "sendMessage", {
                    "chat_id": chat_id,
                    "text": "❌ Ошибка при загрузке фото."
                })
                return
            
            # 3. Analyze photo via Gemini Vision
            ai_data = call_gemini_vision(img_path)
            
            # Delete loading message
            if loading_msg_id:
                telegram_api(token, "deleteMessage", {"chat_id": chat_id, "message_id": loading_msg_id})
                
            if not ai_data:
                telegram_api(token, "sendMessage", {
                    "chat_id": chat_id,
                    "text": "❌ *ИИ-модель вернула ошибку.* Сфотографируйте еду ближе и при хорошем освещении."
                })
                return
            
            # 4. Calculate nutrients
            ingredients = ai_data.get("ingredients", [])
            
            total_cal = 0
            total_p = 0
            total_c = 0
            total_f = 0
            total_fb = 0
            
            ingredients_lines = []
            for ing in ingredients:
                weight = ing.get("weight", 100)
                cal = ing.get("calories", 0)
                p = ing.get("protein", 0)
                c = ing.get("carbs", 0)
                f = ing.get("fats", 0)
                fb = ing.get("fiber", 0)
                
                factor = weight / 100.0
                total_cal += cal * factor
                total_p += p * factor
                total_c += c * factor
                total_f += f * factor
                total_fb += fb * factor
                
                ingredients_lines.append(f"• *{ing.get('name', 'Ингредиент')}*: {weight}г (~{round(cal * factor)} ккал)")
                
            total_cal = round(total_cal)
            total_p = round(total_p, 1)
            total_c = round(total_c, 1)
            total_f = round(total_f, 1)
            total_fb = round(total_fb, 1)
            
            # Save scan record
            user["scans"].append(time.time())
            db[user_id] = user
            save_db(db)
            
            # Cache the parsed meal in memory
            meal_id = uuid.uuid4().hex[:12]
            now_str = datetime.datetime.now().strftime("%H:%M")
            temp_meals[meal_id] = {
                "name": ai_data.get("name", "Распознанное блюдо ИИ"),
                "image": img_path,
                "ingredients": [{
                    "name": ing.get("name", "Продукт"),
                    "weight": ing.get("weight", 100),
                    "calories": ing.get("calories", 100),
                    "protein": ing.get("protein", 2),
                    "carbs": ing.get("carbs", 10),
                    "fats": ing.get("fats", 2),
                    "fiber": ing.get("fiber", 0)
                } for ing in ingredients],
                "time": now_str
            }
            
            coach_text = generate_coach_recommendation(total_cal, total_p, total_c, total_f, total_fb)
            
            caption = (
                f"🍽️ *Распознано ИИ:* {ai_data.get('name', 'Блюдо')}\n\n"
                f"🔥 Калории: *{total_cal} ккал*\n"
                f"💪 Белки: *{total_p}г* | 🌾 Углеводы: *{total_c}г*\n"
                f"💧 Жиры: *{total_f}г* | 🥦 Клетчатка: *{total_fb}г*\n\n"
                f"🥗 *Состав порции:*\n" + "\n".join(ingredients_lines) + "\n\n"
                f"🧠 *ИИ-оценка веса:*\n_{ai_data.get('estimation_reasoning', 'Оценка по масштабам тарелки')}_\n\n"
                f"💡 *Совет ИИ-коуча:*\n{coach_text}"
            )
            
            keyboard = {
                "inline_keyboard": [
                    [
                        {"text": "📥 Добавить в дневник", "callback_data": f"add_meal_{meal_id}"}
                    ]
                ]
            }
            
            # Send photo back to user with caption and keyboard
            telegram_api(token, "sendPhoto", {
                "chat_id": chat_id,
                "photo": file_id,
                "caption": caption,
                "parse_mode": "Markdown",
                "reply_markup": keyboard
            })
            
    elif "callback_query" in update:
        callback = update["callback_query"]
        callback_id = callback["id"]
        chat_id = callback["message"]["chat"]["id"]
        message_id = callback["message"]["message_id"]
        user_info = callback["from"]
        user_id = f"tg_{user_info['id']}"
        data = callback["data"]
        
        # Load DB
        db = load_db()
        user = db.get(user_id)
        
        if not user:
            telegram_api(token, "answerCallbackQuery", {
                "callback_query_id": callback_id,
                "text": "Пользователь не найден."
            })
            return
            
        if data.startswith("add_meal_"):
            meal_id = data.replace("add_meal_", "")
            
            if meal_id not in temp_meals:
                telegram_api(token, "answerCallbackQuery", {
                    "callback_query_id": callback_id,
                    "text": "❌ Время хранения сессии истекло. Отправьте фото заново.",
                    "show_alert": True
                })
                return
            
            meal_data = temp_meals[meal_id]
            if "dailyLog" not in user:
                user["dailyLog"] = []
                
            user["dailyLog"].append(meal_data)
            db[user_id] = user
            save_db(db)
            
            # Clean from temp cache
            del temp_meals[meal_id]
            
            # Update Inline Keyboard
            keyboard = {
                "inline_keyboard": [
                    [
                        {"text": "✅ Добавлено в дневник", "callback_data": "meal_already_added"}
                    ]
                ]
            }
            
            telegram_api(token, "editMessageReplyMarkup", {
                "chat_id": chat_id,
                "message_id": message_id,
                "reply_markup": keyboard
            })
            
            telegram_api(token, "answerCallbackQuery", {
                "callback_query_id": callback_id,
                "text": "Прием пищи успешно добавлен в дневник! 🎉"
            })
            
        elif data == "meal_already_added":
            telegram_api(token, "answerCallbackQuery", {
                "callback_query_id": callback_id,
                "text": "Этот прием пищи уже в дневнике."
            })
            
        elif data == "clear_log":
            user["dailyLog"] = []
            db[user_id] = user
            save_db(db)
            
            # Edit original message to say it was cleared
            telegram_api(token, "editMessageText", {
                "chat_id": chat_id,
                "message_id": message_id,
                "text": "📊 *Дневник питания успешно очищен!*\n\nВсе сегодняшние приемы пищи сброшены. Готовы к новым записям!",
                "parse_mode": "Markdown"
            })
            
            telegram_api(token, "answerCallbackQuery", {
                "callback_query_id": callback_id,
                "text": "Дневник очищен!"
            })
            
        elif data == "edit_weight":
            user["state"] = "wait_weight"
            db[user_id] = user
            save_db(db)
            
            telegram_api(token, "sendMessage", {
                "chat_id": chat_id,
                "text": "⚖️ *Корректировка веса*\n\nВведите ваш текущий вес в килограммах (например: *74* или *68.5*).\n\nДля отмены введите слово 'отмена'.",
                "parse_mode": "Markdown",
                "reply_markup": {"remove_keyboard": True}
            })
            
            telegram_api(token, "answerCallbackQuery", { "callback_query_id": callback_id })
            
        elif data == "edit_height":
            user["state"] = "wait_height"
            db[user_id] = user
            save_db(db)
            
            telegram_api(token, "sendMessage", {
                "chat_id": chat_id,
                "text": "📏 *Корректировка роста*\n\nВведите ваш рост в сантиметрах целым числом (например: *175*).\n\nДля отмены введите слово 'отмена'.",
                "parse_mode": "Markdown",
                "reply_markup": {"remove_keyboard": True}
            })
            
            telegram_api(token, "answerCallbackQuery", { "callback_query_id": callback_id })
            
        elif data == "edit_age":
            user["state"] = "wait_age"
            db[user_id] = user
            save_db(db)
            
            telegram_api(token, "sendMessage", {
                "chat_id": chat_id,
                "text": "🎂 *Корректировка возраста*\n\nВведите ваш возраст целым числом (например: *26*).\n\nДля отмены введите слово 'отмена'.",
                "parse_mode": "Markdown",
                "reply_markup": {"remove_keyboard": True}
            })
            
            telegram_api(token, "answerCallbackQuery", { "callback_query_id": callback_id })
            
        elif data == "edit_activity":
            # Send inline keyboard for activity levels
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🏃 Малоподвижный (офис)", "callback_data": "set_act_1.2"}],
                    [{"text": "🏃‍♂️ Умеренный (1-3 тр/нед)", "callback_data": "set_act_1.375"}],
                    [{"text": "🚴 Средняя активность (3-5 тр/нед)", "callback_data": "set_act_1.55"}],
                    [{"text": "🏋️ Высокая активность (спортсмен)", "callback_data": "set_act_1.725"}]
                ]
            }
            
            telegram_api(token, "sendMessage", {
                "chat_id": chat_id,
                "text": "🏃 *Выберите уровень физической активности:*",
                "reply_markup": keyboard
            })
            
            telegram_api(token, "answerCallbackQuery", { "callback_query_id": callback_id })
            
        elif data.startswith("set_act_"):
            act_val = float(data.replace("set_act_", ""))
            
            user["activity"] = act_val
            user["targets"] = calculate_user_calorie_goal(
                user.get("gender", "male"),
                user.get("age", 25),
                user.get("height", 175),
                user.get("weight", 70),
                act_val
            )
            db[user_id] = user
            save_db(db)
            
            # Edit original message to remove inline keyboard or show confirmation
            telegram_api(token, "sendMessage", {
                "chat_id": chat_id,
                "text": f"✅ Уровень активности успешно обновлен до *{act_val}*!\n🔥 Суточная норма калорий пересчитана: *{user['targets']['calories']} ккал*.",
                "parse_mode": "Markdown"
            })
            
            telegram_api(token, "answerCallbackQuery", {
                "callback_query_id": callback_id,
                "text": "Активность обновлена!"
            })
            
        elif data == "edit_premium":
            # Direct mock purchase
            keyboard = {
                "inline_keyboard": [
                    [
                        {"text": "💳 Оплатить 490.00 ₽", "callback_data": "pay_premium_confirm"}
                    ],
                    [
                        {"text": "❌ Отмена", "callback_data": "pay_premium_cancel"}
                    ]
                ]
            }
            
            pay_msg = (
                f"💳 *Оплата подписки MacroSnap AI*\n\n"
                f"Получатель: ИП Тютин М. А.\n"
                f"Тариф: *Безлимит сканирований на 1 месяц*\n"
                f"Сумма к оплате: *490.00 ₽*\n\n"
                f"_После нажатия кнопки оплаты платеж будет успешно симулирован через Юкасса (стандарт PCI DSS)_."
            )
            
            telegram_api(token, "sendMessage", {
                "chat_id": chat_id,
                "text": pay_msg,
                "parse_mode": "Markdown",
                "reply_markup": keyboard
            })
            
            telegram_api(token, "answerCallbackQuery", { "callback_query_id": callback_id })
            
        elif data == "pay_premium_confirm":
            user["isPremium"] = True
            db[user_id] = user
            save_db(db)
            
            congrat_msg = (
                "🎉 *Оплата 490 ₽ успешно проведена через Юкасса!*\n\n"
                "Вам предоставлен *Безлимитный доступ* к ИИ-анализу блюд и персональным советам коуча без ограничений на 30 дней! Спасибо за поддержку сервиса! ❤️"
            )
            
            # Send message and remove inline keyboard
            telegram_api(token, "sendMessage", {
                "chat_id": chat_id,
                "text": congrat_msg,
                "parse_mode": "Markdown"
            })
            
            # Edit payment message to show success
            telegram_api(token, "editMessageText", {
                "chat_id": chat_id,
                "message_id": message_id,
                "text": "✅ *Платеж успешно проведен.*\nСумма: 490.00 ₽. Подписка активна.",
                "parse_mode": "Markdown"
            })
            
            telegram_api(token, "answerCallbackQuery", {
                "callback_query_id": callback_id,
                "text": "Подписка активирована! 🎉"
            })
            
        elif data == "pay_premium_cancel":
            telegram_api(token, "editMessageText", {
                "chat_id": chat_id,
                "message_id": message_id,
                "text": "❌ Оплата отменена пользователем.",
                "parse_mode": "Markdown"
            })
            telegram_api(token, "answerCallbackQuery", {
                "callback_query_id": callback_id,
                "text": "Оплата отменена."
            })

def run_bot():
    token = get_bot_token()
    if not token:
        print("[TELEGRAM] Token not configured. Bot thread disabled.")
        return
        
    print(f"[TELEGRAM] Bot starting polling with token: {token[:8]}...{token[-4:] if len(token) > 8 else ''}")
    
    # Clear webhook
    try:
        print("[TELEGRAM] Clearing webhook just in case...")
        clear_res = telegram_api(token, "deleteWebhook", {"drop_pending_updates": False})
        print(f"[TELEGRAM] deleteWebhook result: {json.dumps(clear_res)}")
    except Exception as e:
        print(f"[TELEGRAM] Error clearing webhook: {e}")
        
    # Configure WebApp Menu Button
    mini_app_url = get_mini_app_url()
    if mini_app_url:
        print(f"[TELEGRAM] Setting Menu Button to Mini App URL: {mini_app_url}")
        menu_res = telegram_api(token, "setChatMenuButton", {
            "menu_button": {
                "type": "web_app",
                "text": "MacroSnap AI",
                "web_app": {"url": mini_app_url}
            }
        })
        print(f"[TELEGRAM] setChatMenuButton result: {json.dumps(menu_res)}")

    offset = 0
    
    while True:
        try:
            url = f"https://api.telegram.org/bot{token}/getUpdates"
            params = {"offset": offset, "timeout": 20}
            data = urllib.parse.urlencode(params).encode('utf-8')
            res = make_request(url, data)
            
            if res and res.get("ok"):
                updates = res.get("result", [])
                if updates:
                    print(f"[TELEGRAM] Received {len(updates)} updates!")
                for update in updates:
                    print(f"[TELEGRAM] Processing update: {json.dumps(update, ensure_ascii=False)}")
                    offset = update["update_id"] + 1
                    process_update(token, update)
            else:
                # If there's an API error or empty response, log it and wait
                if res:
                    print(f"[TELEGRAM] API response not OK: {json.dumps(res)}")
                else:
                    print("[TELEGRAM] Empty or failed API response from getUpdates")
                time.sleep(5)
        except Exception as e:
            print(f"[TELEGRAM] Polling loop error: {e}")
            time.sleep(5)
