import requests
import time
import json
import os
from datetime import datetime, timedelta, timezone

TOKEN = os.environ.get("TOKEN")
PROVIDER_TOKEN = os.environ.get("PROVIDER_TOKEN")
BASE_URL       = f"https://tapi.bale.ai/bot{TOKEN}"
BOT_USERNAME = "ARKA_MEMBER_BOT"
ADMIN_IDS    = int(os.environ.get("ADMIN", "0"))
DATA_FILE    = "bot_data.json"

SVCLABEL = {
    "bale_view_single":  "بازدید تکی بله",
    "bale_reaction":     "ری‌اکشن بله",
    "rubika_view":       "بازدید تکی روبیکا",
    "eitaa_view":        "بازدید ایتا",
    "bale_member":       "ممبر بله",
    "rubika_member":     "ممبر روبیکا",
    "eitaa_member":      "ممبر ایتا",
    "rubika_follower":   "فالوور روبیکا",
}

SVC_PLATFORM = {
    "bale_view_single":  "bale",
    "bale_reaction":     "bale",
    "rubika_view":       "rubika",
    "eitaa_view":        "eitaa",
    "bale_member":       "bale",
    "rubika_member":     "rubika",
    "eitaa_member":      "eitaa",
    "rubika_follower":   "rubika",
}

ALL_SVC_KEYS = list(SVCLABEL.keys())

# ══════════════════════════════════════════
#  DATA
# ══════════════════════════════════════════
def default_data():
    return {
        "settings": {
            "forced_join":      True,
            "channel":          "@IRANI_MEMBER",
            "channel_link":     "https://ble.ir/IRANI_MEMBER",
            "bale_view_single": {"enabled": True, "min": 500,   "max": 3000,  "price_per_1000": 25200,  "stock": 999999},
            "bale_reaction":    {"enabled": True, "min": 100,   "max": 1000,  "price_per_1000": 25200,  "stock": 999999},
            "rubika_view":      {"enabled": True, "min": 100,   "max": 50000, "price_per_1000": 25200,  "stock": 999999},
            "eitaa_view":       {"enabled": True, "min": 100,   "max": 10000, "price_per_1000": 56000,  "stock": 999999},
            "bale_member":      {"enabled": True, "min": 100,   "max": 10000, "price_per_1000": 288000, "stock": 999999},
            "rubika_member":    {"enabled": True, "min": 100,   "max": 20000, "price_per_1000": 480000, "stock": 999999},
            "eitaa_member":     {"enabled": True, "min": 100,   "max": 10000, "price_per_1000": 372000, "stock": 999999},
            "rubika_follower":  {"enabled": True, "min": 100,   "max": 20000, "price_per_1000": 216000, "stock": 999999},
        },
        "stats": {
            "total_users": 0, "total_orders": 0,
            "total_revenue": 0, "daily_stats": {}
        },
        "users":          {},
        "orders":         [],
        "tickets":        {},
        "ticket_counter": 0,
        "order_counter":  0,
    }

def migrate_data(data):
    defaults = default_data()
    for k, v in defaults.items():
        if k not in data:
            data[k] = v
    for svc_key, svc_default in defaults["settings"].items():
        if svc_key not in data["settings"]:
            data["settings"][svc_key] = svc_default
        elif isinstance(svc_default, dict):
            for field, field_default in svc_default.items():
                if field not in data["settings"][svc_key]:
                    data["settings"][svc_key][field] = field_default
    return data

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return migrate_data(data)
        except:
            pass
    return default_data()

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_today():
    return datetime.now().strftime("%Y-%m-%d")

# ══════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════
def is_admin(chat_id):
    return int(chat_id) in ADMIN_IDS

def register_user(data, chat_id, uinfo=None):
    uid = str(chat_id)
    if uid not in data["users"]:
        data["users"][uid] = {
            "chat_id":     chat_id,
            "first_seen":  datetime.now().isoformat(),
            "last_seen":   datetime.now().isoformat(),
            "orders":      0,
            "total_spent": 0,
            "blocked":     False,
            "username":    (uinfo or {}).get("username", ""),
            "first_name":  (uinfo or {}).get("first_name", ""),
        }
        data["stats"]["total_users"] += 1
    else:
        data["users"][uid]["last_seen"] = datetime.now().isoformat()
        if uinfo:
            data["users"][uid]["username"]   = uinfo.get("username",   data["users"][uid].get("username",""))
            data["users"][uid]["first_name"] = uinfo.get("first_name", data["users"][uid].get("first_name",""))
    save_data(data)

def check_membership(chat_id):
    data = load_data()
    if not data["settings"]["forced_join"]:
        return True
    try:
        r = requests.get(
            f"{BASE_URL}/getChatMember",
            params={"chat_id": data["settings"]["channel"], "user_id": chat_id},
            timeout=10
        ).json()
        if r.get("ok"):
            return r["result"].get("status","") in ["member","administrator","creator"]
        return False
    except Exception as e:
        print(f"check_membership error: {e}")
        return False

def validate_bale_link(link):
    link = link.strip()
    if link.startswith("@") and len(link) > 1:
        return True
    for p in ["https://ble.ir/","http://ble.ir/","ble.ir/"]:
        if link.startswith(p) and len(link) > len(p):
            return True
    return False

def validate_rubika_link(link):
    link = link.strip()
    if link.startswith("@") and len(link) > 1:
        return True
    for p in ["https://rubika.ir/","http://rubika.ir/","rubika.ir/"]:
        if link.startswith(p) and len(link) > len(p):
            return True
    return False

def validate_eitaa_link(link):
    link = link.strip()
    if link.startswith("@") and len(link) > 1:
        return True
    for p in ["https://eitaa.com/","http://eitaa.com/","eitaa.com/"]:
        if link.startswith(p) and len(link) > len(p):
            return True
    return False

def gregorian_to_jalali(gy, gm, gd):
    g_days_in_month = [31,28,31,30,31,30,31,31,30,31,30,31]
    j_days_in_month = [31,31,31,31,31,31,30,30,30,30,30,29]
    gy2=gy-1600; gm2=gm-1; gd2=gd-1
    g_day_no = 365*gy2+(gy2+3)//4-(gy2+99)//100+(gy2+399)//400
    for i in range(gm2): g_day_no += g_days_in_month[i]
    if gm2>1 and ((gy%4==0 and gy%100!=0) or (gy%400==0)): g_day_no+=1
    g_day_no+=gd2
    j_day_no=g_day_no-79
    j_np=j_day_no//12053; j_day_no%=12053
    jy=979+33*j_np+4*(j_day_no//1461); j_day_no%=1461
    if j_day_no>=366:
        jy+=(j_day_no-1)//365; j_day_no=(j_day_no-1)%365
    for i in range(11):
        if j_day_no<j_days_in_month[i]: jm=i+1; jd=j_day_no+1; break
        j_day_no-=j_days_in_month[i]
    else: jm=12; jd=j_day_no+1
    return jy,jm,jd

def now_jalali_str():
    utc_now  = datetime.now(timezone.utc).replace(tzinfo=None)
    iran_now = utc_now + timedelta(hours=3, minutes=30)
    jy,jm,jd = gregorian_to_jalali(iran_now.year, iran_now.month, iran_now.day)
    return f"{jy:04d}/{jm:02d}/{jd:02d} - {iran_now.strftime('%H:%M:%S')}"

def mask_user_id(chat_id):
    s=str(chat_id); n=len(s)
    if n<=4: return "*"*n
    vs=max(2,(n-4)//2); ve=n-vs-4
    if ve<2: ve=2; vs=n-ve-4
    if vs<1: vs=1
    ml=n-vs-ve
    if ml<1: ml=1
    return s[:vs]+("*"*ml)+s[n-ve:]

def send(chat_id, text, markup=None):
    payload = {"chat_id":chat_id,"text":text,"parse_mode":"Markdown"}
    if markup: payload["reply_markup"] = markup
    try:
        requests.post(f"{BASE_URL}/sendMessage", json=payload, timeout=10)
    except Exception as e:
        print(f"send error: {e}")

def kb(*rows):
    return {"keyboard":[[{"text":t} for t in row] for row in rows],"resize_keyboard":True}

BACK_BTN      = kb(["🔙 بازگشت"])
BACK_BTN_USER = kb(["🔙 بازگشت به منوی اصلی 🏠"])

# ══════════════════════════════════════════
#  JOIN / START
# ══════════════════════════════════════════
def send_join_required(chat_id):
    data = load_data()
    send(chat_id,
        "*✨🥳 اوه! ی لحظه صبر کن! 🥳✨\n\n"
        "برای اینکه بتونی از تمام قدرتِ ربات استفاده کنی و اولین سفارش‌ها خفن رو ثبت کنی، باید اول به باشگاه ویژه ما بیای! 🏃‍♂️️💨\n\n"
        "🌈 فقط کافیه عضو کانال ما بشی تا قفل ربات باز بشه:\n\n"
        "🌟 با عضویت در کانال، از تخفیف‌ها، خبر‌های داغ و آپدیت‌های جدید ما جا نمونی! 🌟\n\n"
        "✅ بعد از عضویت، دوباره به اینجا برگرد تا بترکونیم! 🚀🔥",
        {"inline_keyboard":[
            [{"text":"افزایش ممبر | بازدید ایران","url":data["settings"]["channel_link"]}],
            [{"text":"تأیید عضویت✔️","callback_data":"check_join"}]
        ]}
    )

def send_not_joined(chat_id):
    data = load_data()
    send(chat_id,
        "⚠️ اوپس! یه کوچولو اشتباه شد! 😅✨\n\n"
        "ای وای! انگار هنوز عضو کانال رسمی ما نشدی رفیق! 🧐💔\n\n"
        "نگران نباش، خیلی ساده‌ست! فقط چند لحظه وقت بذار و عضو بشو تا بتونیم با هم شروع کنیم به رشد و بترکونیم! 🚀🌈\n\n"
        "👇 سریع برو عضو شو و دوباره برگرد:\n\n"
        "🌟 منتظر برگشتت هستیم تا قفل ربات رو برات باز کنیم! 🌟\n\n"
        "✨ بزن بریم! ✨",
        {"inline_keyboard":[
            [{"text":"افزایش ممبر | بازدید ایران","url":data["settings"]["channel_link"]}],
            [{"text":"تأیید عضویت✔️","callback_data":"check_join"}]
        ]}
    )

def send_start(chat_id):
    send(chat_id,
        "🌈 سلام سلام! به ربات افزایش ممبر | بازدید ایران خوش اومدی! 🌈🎉\n\n"
        "چه خوب که اینجایی 😍💖\n\n"
        "اینجا قراره با یه عالمه انرژی خوب،\n"
        "ممبر و بازدید رو سریع، راحت و جذاب تجربه کنی 🚀🔥\n\n"
        "💫 چرا اینجا؟\n\n"
        "🌟 سریع و آسان\n\n"
        "🌟 شاد و کاربرپسند\n\n"
        "🌟 پشتیبانی همیشه همراه\n\n"
        "🌟 مناسب برای رشد بهتر و بیشتر\n\n"
        "🚀 برای شروع همین الان وارد شو:\n\n"
        "🔗 @IRANI_MEMBER\n\n"
        "💌 پشتیبانی مهربون و پاسخ‌گو:\n\n"
        "🆔 @ARKA_SUPPORT_IR\n\n"
        "🌸✨ منتظر یه تجربه عالی و پرانرژی باش! ✨🌸\n\n"
        "با ما، رشدت شیرین‌تره 🍭💎\n\n"
        "👇 از دکمه‌های زیر برای دسترسی به خدمات ربات استفاده کنید:",
        kb(
            ["سفارش بازدید 👁️",   "سفارش ممبر 👥"],
            ["حساب کاربری 👤",     "پیگیری سفارش 🔎"],
            ["قوانین ⚖️",          "📞 پشتیبانی"]
        )
    )

# ══════════════════════════════════════════
#  حساب کاربری
# ══════════════════════════════════════════
def send_account(chat_id):
    data    = load_data()
    uid     = str(chat_id)
    u       = data["users"].get(uid, {})
    name    = u.get("first_name", "نامشخص")
    uname   = f"@{u['username']}" if u.get("username") else "ندارد"
    total   = u.get("orders", 0)
    done    = sum(1 for o in data["orders"] if str(o.get("user_id"))==uid and o.get("status")=="done")
    pending = sum(1 for o in data["orders"] if str(o.get("user_id"))==uid and o.get("status")=="pending")
    send(chat_id,
        f"👤 حساب کاربری\n"
        f"━━━━━━━━━━━━\n\n"
        f"🆔 شناسه کاربری: {chat_id}\n"
        f"👤 نام: {name}\n"
        f"🔗 نام کاربری: {uname}\n\n"
        f"📦 آمار سفارش‌ها\n"
        f"📋 کل سفارش‌ها: {total}\n"
        f"⏳ در حال انجام: {pending}\n"
        f"✅ تکمیل شده: {done}*",
        BACK_BTN_USER
    )

# ══════════════════════════════════════════
#  پیگیری سفارش
# ══════════════════════════════════════════
def send_tracking(chat_id):
    data   = load_data()
    uid    = str(chat_id)
    orders = [o for o in data["orders"] if str(o.get("user_id"))==uid]
    if not orders:
        send(chat_id, "*📋 شما هنوز هیچ سفارشی ثبت نکرده‌اید.*", BACK_BTN_USER)
        return
    send(chat_id, f"*🔎 پیگیری سفارش‌ها | {len(orders)} سفارش*")
    for o in reversed(orders[-20:]):
        st = o.get("status","")
        if st=="done":              st_icon="✅ تکمیل شده"
        elif st=="pending":         st_icon="⏳ در حال انجام"
        elif st=="pending_payment": st_icon="💳 در انتظار پرداخت"
        else:                       st_icon="❓ نامشخص"
        date_str = o.get("date","")[:10]
        send(chat_id,
            f"*🆔 {o.get('id','?')}\n"
            f"📦 {o.get('service','?')}\n"
            f"🔢 تعداد: {o.get('amount',0):,}\n"
            f"💰 مبلغ: {o.get('price',0):,} تومان\n"
            f"🔗 لینک: {o.get('link','?')}\n"
            f"📅 تاریخ: {date_str}\n"

f"وضعیت: {st_icon}*"
        )
    send(chat_id, "👆 لیست سفارش‌های شما", BACK_BTN_USER)

# ══════════════════════════════════════════
#  قوانین
# ══════════════════════════════════════════
def send_rules(chat_id):
    send(chat_id,
        "*━━━━━━━━━━━━━━━━━━\n"
        "⚖️ قوانین و ضوابط استفاده از ربات «افزایش ممبر | بازدید ایران»\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "استفاده از خدمات این ربات به منزله‌ی تایید کامل تمامی موارد زیر می‌باشد. لطفاً پیش از ثبت سفارش، با دقت مطالعه کنید:\n\n"
        "📍 بخش اول: مسئولیت کاربر\n"
        "🔹 دقت در اطلاعات: مسئولیت صحت تمامی اطلاعات وارد شده (لینک، آیدی، تعداد و پلتفرم) بر عهده کاربر است. اشتباه در ارسال لینک، منجر به عدم انجام سفارش می‌شود.\n"
        "🔹 فرمت صحیح: ثبت سفارش با لینک‌های نامعتبر یا فرمت اشتباه، مسئولیت خود کاربر است.\n\n"
        "⚠️ بخش دوم: سیاست‌های مهم (حتماً بخوانید)\n"
        "🚫 عدم بازگشت وجه: با توجه به ماهیت دیجیتالی خدمات، به هیچ عنوان امکان استرداد یا بازگشت وجه پس از ثبت سفارش و پرداخت وجود ندارد. لطفاً قبل از خرید، از انتخاب صحیح سرویس اطمینان حاصل کنید.\n"
        "🚫 ماهیت سرویس: توجه داشته باشید که برخی خدمات (مانند بازدید) صرفاً جهت بهبود آمار و نمایش هستند و هدف تبلیغاتی یا جذب مخاطب واقعی (Engagement) نمی‌باشند.\n\n"
        "💡 توصیه نهایی:\n"
        "برای دریافت بهترین نتیجه، همیشه ابتدا با مقادیر کم تست کنید. 🚀\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🆘 نیاز به کمک دارید؟\n"
        "ارتباط با پشتیبانی: [@ARKA_SUPPORT_IR]\n"
        "━━━━━━━━━━━━━━━━━━*",
        BACK_BTN_USER
    )

# ══════════════════════════════════════════
#  سیستم تیکت پشتیبانی
# ══════════════════════════════════════════
def get_user_open_ticket(data, chat_id):
    uid = str(chat_id)
    for tid, t in data["tickets"].items():
        if str(t.get("user_id"))==uid and t.get("status")=="open":
            return tid, t
    return None, None

def create_ticket(data, chat_id, first_msg, uinfo=None):
    data["ticket_counter"] = data.get("ticket_counter",0) + 1
    tid   = f"TKT{data['ticket_counter']}"
    name  = (uinfo or {}).get("first_name","کاربر")
    uname = (uinfo or {}).get("username","")
    data["tickets"][tid] = {
        "id":       tid,
        "user_id":  chat_id,
        "name":     name,
        "username": uname,
        "status":   "open",
        "created":  datetime.now().isoformat(),
        "messages": [{"from":"user","text":first_msg,"time":datetime.now().isoformat()}]
    }
    save_data(data)
    return tid

def send_support_menu(chat_id):
    data   = load_data()
    tid, t = get_user_open_ticket(data, chat_id)
    if tid:
        send(chat_id,
            f"*📞 پشتیبانی\n\n"
            f"شما یک گفتگوی باز دارید: #{tid}\n\n"
            f"پیام خود را ارسال کنید تا پشتیبان پاسخ دهد.*",
            kb(["❌ بستن تیکت","🔙 بازگشت به منوی اصلی 🏠"])
        )
    else:
        send(chat_id,
            "*📞 پشتیبانی\n\n"
            "پیام خود را بنویسید تا گفتگو با پشتیبان شروع شود.\n\n"
            "💡 سوال، مشکل یا درخواست خود را ارسال کنید:*",
            kb(["🔙 بازگشت به منوی اصلی 🏠"])
        )

def handle_support_message(chat_id, text, data, states, uinfo=None):
    uid = str(chat_id)

    if text=="❌ بستن تیکت":
        tid, t = get_user_open_ticket(data, chat_id)
        if tid:
            data["tickets"][tid]["status"]="closed"; save_data(data)
            states.pop(uid,None)
            send(chat_id, f"*✅ گفتگو #{tid} بسته شد.*", BACK_BTN_USER)
            for aid in ADMIN_IDS:
                send(aid, f"*🔴 تیکت #{tid} توسط کاربر بسته شد.*")
        else:
            states.pop(uid,None)
            send(chat_id, "*هیچ گفتگوی بازی وجود ندارد.*", BACK_BTN_USER)
        return

    tid, t = get_user_open_ticket(data, chat_id)
    if not tid:
        tid   = create_ticket(data, chat_id, text, uinfo)
        uname = (uinfo or {}).get("username","")
        uname_str = f"@{uname}" if uname else str(chat_id)
        name  = (uinfo or {}).get("first_name","کاربر")
        send(chat_id,
            f"*✅ گفتگو #{tid} شروع شد!\n\n"
            f"پشتیبان پیام شما را دریافت کرد و به زودی پاسخ می‌دهد.\n"
            f"می‌توانید ادامه گفتگو را همینجا دنبال کنید.*",
            kb(["❌ بستن تیکت","🔙 بازگشت به منوی اصلی 🏠"])
        )
        for aid in ADMIN_IDS:
            send(aid,
                f"*🎫 گفتگوی جدید #{tid}\n\n"
                f"👤 {name} ({uname_str})\n"
                f"🆔 آیدی: {chat_id}\n\n"
                f"💬 پیام:\n{text}*",
                {"inline_keyboard":[
                    [{"text":f"↩️ پاسخ به #{tid}","callback_data":f"reply_ticket|{tid}"}],
                    [{"text":f"🔴 بستن #{tid}","callback_data":f"close_ticket|{tid}"}]
                ]}
            )
    else:
        t["messages"].append({"from":"user","text":text,"time":datetime.now().isoformat()})
        save_data(data)
        send(chat_id, "*✅ پیام ارسال شد. منتظر پاسخ باشید.*",
             kb(["❌ بستن تیکت","🔙 بازگشت به منوی اصلی 🏠"]))
        uname     = t.get("username","")
        uname_str = f"@{uname}" if uname else str(chat_id)
        for aid in ADMIN_IDS:
            send(aid,
                f"*💬 پیام جدید در #{tid}\n\n"
                f"👤 {t.get('name','کاربر')} ({uname_str})\n\n"
                f"📩 پیام:\n{text}*",
                {"inline_keyboard":[
                    [{"text":f"↩️ پاسخ به #{tid}","callback_data":f"reply_ticket|{tid}"}],
                    [{"text":f"🔴 بستن #{tid}","callback_data":f"close_ticket|{tid}"}]
                ]}
            )

def admin_reply_to_ticket(admin_chat_id, tid, reply_text, data):
    t = data["tickets"].get(tid)
    if not t:
        send(admin_chat_id, f"*⚠️ تیکت #{tid} یافت نشد."); return
    if t.get("status")=="closed":
        send(admin_chat_id, f"⚠️ تیکت #{tid} بسته است."); return
    t["messages"].append({"from":"admin","text":reply_text,"time":datetime.now().isoformat()})
    save_data(data)
    user_id = t.get("user_id")
    send(user_id,
        f"📩 پاسخ پشتیبانی - گفتگو #{tid}\n\n"
        f"━━━━━━━━━━━━\n\n"
        f"{reply_text}\n\n"
        f"━━━━━━━━━━━━\n"
        f"می‌توانید پاسخ دهید یا گفتگو را ببندید.*",
        kb(["❌ بستن تیکت","🔙 بازگشت به منوی اصلی 🏠"])
    )
    send(admin_chat_id,
        f"*✅ پاسخ به #{tid} ارسال شد.*",
        {"inline_keyboard":[
            [{"text":f"↩️ پاسخ دیگر به #{tid}","callback_data":f"reply_ticket|{tid}"}],
            [{"text":f"🔴 بستن #{tid}","callback_data":f"close_ticket|{tid}"}]
        ]}
    )

# ══════════════════════════════════════════
#  ORDER
# ══════════════════════════════════════════
def send_platform(chat_id):
    send(chat_id,
        "*👁️ بزن بریم برای رشد! سفارش بازدید شروع شد… 🚀✨\n\n"
        "━━━━━━━━━━━━\n\n"
        "خب رفیق! حالا وقتشه که مشخص کنیم قراره کجا رو بترکونیم! 😍💥\n\n"
        "لطفاً پلتفرم مورد نظرت رو انتخاب کن تا با سرعت جت شروع کنیم: 👇🌈",
        kb(
            ["🔵 سفارش بازدید | بله 🚀"],
            ["🔴 سفارش بازدید | روبیکا ⚡️"],
            ["🟢 سفارش بازدید | ایتا ☕️"],
            ["🔙 بازگشت به منوی اصلی 🏠"]
        )
    )

def send_bale_services(chat_id):
    data = load_data()
    s    = data["settings"]
    rows = []
    if s["bale_view_single"]["enabled"]: rows.append(["بازدید تکی 👁️"])
    if s["bale_reaction"]["enabled"]:    rows.append(["ری‌اکشن بله ❤️"])
    rows.append(["🔙 بازگشت به منوی اصلی 🏠"])
    send(chat_id,
        "✨ بزن بریم برای شروع! چه نوع سرویسی می‌خوای؟ ✨\n\n"
        "━━━━━━━━━━━━\n\n"
        "خب رفیق! حالا مشخص کن چطوری می‌خوای بدرخشی! 😍👇\n\n"
        "🔹 بازدید تکی 🎯 | (فقط برای یک پست خاص که خودت انتخاب می‌کنی)\n\n"
        "🔹 ری‌اکشن بله ❤️ | (به پست‌هات با کلی ری‌اکشن و عشق برس!)\n\n"
        "👇 یکی رو انتخاب کن تا شروع کنیم:*",
        kb(*rows)
    )

def send_member_platform(chat_id):
    send(chat_id,
        "*👥 بزن بریم برای رشد! سفارش ممبر شروع شد… 🚀✨\n\n"
        "━━━━━━━━━━━━\n\n"
        "خب رفیق! حالا وقتشه که مشخص کنیم قراره کجا رو بترکونیم! 😍💥\n\n"
        "لطفاً پلتفرم مورد نظرت رو انتخاب کن تا با سرعت جت شروع کنیم: 👇🌈*",
        kb(
            ["🔵 سفارش ممبر | بله 🚀"],
            ["🔴 سفارش ممبر | روبیکا ⚡️"],
            ["🟢 سفارش ممبر | ایتا ☕️"],
            ["🟣 سفارش فالوور | روبیکا 🔥"]

,
            ["🔙 بازگشت به منوی اصلی 🏠"]
        )
    )

def send_service_info(chat_id, key):
    data = load_data()
    s    = data["settings"][key]
    INFO = {
        "bale_view_single": ("👁️","افزایش سین برای پست دلخواه کانال بله","بازدید",
            "✅ - فقط برای کانال‌ها و پست‌های بله\n👁️ - نوع: بازدید/سین پست\n⚡ - زمان انجام: آنی\n🛡️ - ریزش: ندارد یا بسیار کم"),
        "bale_reaction":    ("❤️","افزایش ری‌اکشن برای پست‌های بله","ری‌اکشن",
            "✅ - فقط برای کانال‌ها و پست‌های بله\n❤️ - ری‌اکشن روی پست\n⚡ - زمان انجام: آنی\n🛡️ - ریزش: ندارد یا بسیار کم"),
        "rubika_view":      ("👁️","افزایش سین برای پست دلخواه کانال روبیکا","بازدید",
            "✅ - مخصوص روبیکا/روبینو\n🇮🇷 - کیفیت: ایرانی\n⚡ - زمان انجام: سریع\n↘️ - ریزش: ممکن است داشته باشد"),
        "eitaa_view":       ("👁️","افزایش سین (بازدید) پست کانال ایتا برای پست دلخواه","بازدید",
            "✅ - مخصوص ایتا\n🇮🇷 - کیفیت: ایرانی\n⚡ - زمان انجام: سریع\n↘️ - ریزش: ممکن است داشته باشد"),
        "bale_member":      ("👥","افزایش عضو کانال بله","ممبر",
            "✅ - فقط برای کانال‌های بله\n🇮🇷 - کیفیت: اجباری ایرانی\n👁️ - بازدید: پایین\n⚡ - زمان انجام: آنی\n↘️ - ریزش: دارد"),
        "rubika_member":    ("👥","افزایش عضو (ممبر) کانال روبیکا","ممبر",
            "✅ - مخصوص روبیکا/روبینو\n🇮🇷 - کیفیت: ایرانی\n⚡ - زمان انجام: سریع\n↘️ - ریزش: ممکن است داشته باشد"),
        "eitaa_member":     ("👥","افزایش عضو (ممبر) کانال ایتا","ممبر",
            "✅ - مخصوص ایتا\n🇮🇷 - کیفیت: ایرانی\n⚡ - زمان انجام: سریع\n↘️ - ریزش: ممکن است داشته باشد"),
        "rubika_follower":  ("👥","افزایش فالوور روبیکا (روبینو)","فالوور",
            "✅ - مخصوص روبیکا/روبینو\n🇮🇷 - کیفیت: ایرانی\n⚡ - زمان انجام: سریع\n↘️ - ریزش: ممکن است داشته باشد"),
    }
    icon,title,unit,notes = INFO.get(key,("📦",key,"عدد",""))
    send(chat_id,
        f"*{icon} {title}\n"
        f"• حداقل: {s['min']:,}  |  حداکثر: {s['max']:,}\n"
        f"• قیمت هر ۱۰۰۰ {unit}: {s['price_per_1000']:,} تومان\n\n"
        f"📌 نکات\n{notes}\n\n"
        f"⚠️ - در هر بار سفارش از {s['min']:,} تا {s['max']:,} {unit} میتونید ثبت کنید\n\n"
        f"🔢 تعداد {unit} موردنظر را ارسال کنید:*",
        BACK_BTN_USER
    )

def check_stock_and_start(chat_id, key, data, states):
    s = data["settings"].get(key,{})
    if not s.get("enabled",True):
        send(chat_id,"*⚠️ این سرویس موقتاً غیرفعال است."); return
    stock = s.get("stock",999999)
    if stock<=0:
        send(chat_id,"⚠️ موجودی این سرویس تمام شده. لطفاً بعداً مراجعه کنید.*"); return
    states[str(chat_id)] = f"order_qty|{key}"
    send_service_info(chat_id, key)

def send_invoice(chat_id, key, qty, price, link):
    data = load_data()
    data["order_counter"] = data.get("order_counter",0)+1
    oid  = data["order_counter"]
    data["orders"].append({
        "id":      f"ORK{oid}",
        "user_id": chat_id,
        "service": SVCLABEL[key],
        "key":     key,
        "amount":  qty,
        "price":   price,
        "link":    link,
        "status":  "pending_payment",
        "date":    datetime.now().isoformat()
    })
    save_data(data)
    result = requests.post(f"{BASE_URL}/sendInvoice", json={
        "chat_id":        chat_id,
        "title":          f"🛒 {SVCLABEL[key]}",
        "description":    f"📦 سرویس: {SVCLABEL[key]}\n🔢 تعداد: {qty:,}\n🔗 لینک: {link}\n🆔 سفارش: ORK{oid}",
        "payload":        f"order_{oid}",
        "provider_token": PROVIDER_TOKEN,
        "currency":       "IRR",
        "prices":         [{"label":SVCLABEL[key],"amount":price*10}],
        "start_parameter":"pay"
    }, timeout=15).json()
    print(f"INVOICE RESULT = {result}")
    if not result.get("ok"):
        send(chat_id,"*❌ خطا در ارسال فاکتور! با پشتیبانی تماس بگیرید: @ARKA_SUPPORT_IR*")

def register_successful_order(chat_id, payload):
    data = load_data()
    order_num = None
    try: order_num = int(payload.replace("order_",""))
    except: pass
    target = None
    for o in data["orders"]:
        if o["id"]==f"ORK{order_num}" and o["user_id"]==chat_id and o["status"]=="pending_payment":
            target=o; break
    if not target:
        for o in reversed(data["orders"]):
            if o["user_id"]==chat_id and o["status"]=="pending_payment":
                target=o; break
    if target:
        target["status"]="pending"
        today=get_today()
        data["stats"]["total_orders"]  +=1
        data["stats"]["total_revenue"] +=target["price"]
        uid=str(chat_id)
        if uid in data["users"]:
            data["users"][uid]["orders"]      = data["users"][uid].get("orders",0)+1
            data["users"][uid]["total_spent"] = data["users"][uid].get("total_spent",0)+target["price"]
        if today not in data["stats"]["daily_stats"]:
            data["stats"]["daily_stats"][today]={"orders":0,"revenue":0}
        data["stats"]["daily_stats"][today]["orders"]  +=1
        data["stats"]["daily_stats"][today]["revenue"] +=target["price"]
        key=target.get("key","")
        if key in data["settings"] and isinstance(data["settings"][key],dict):
            cur=data["settings"][key].get("stock",999999)
            data["settings"][key]["stock"]=max(0,cur-target["amount"])
        save_data(data)
        send(chat_id,
            f"*🎉 پرداخت موفق! سفارش ثبت شد!\n\n"
            f"━━━━━━━━━━━━\n\n"
            f"🆔 شماره سفارش: {target['id']}\n"
            f"📦 سرویس: {target['service']}\n"
            f"🔢 تعداد: {target['amount']:,}\n"
            f"🔗 لینک: {target['link']}\n"
            f"💰 مبلغ: {target['price']:,} تومان\n\n"
            f"⏳ سفارش در حال پردازش است.\n"
            f"💌 پشتیبانی: @ARKA_SUPPORT_IR*"
        )
        for aid in ADMIN_IDS:
            try:
                send(aid,
                    f"*🔔 سفارش جدید!\n\n"
                    f"🆔 {target['id']} | 👤 {chat_id}\n"
                    f"📦 {target['service']} | {target['amount']:,}\n"
                    f"🔗 {target['link']}\n"
                    f"💰 {target['price']:,} تومان*",
                    {"inline_keyboard":[[{"text":"✅ تکمیل سفارش","callback_data":f"complete|{target['id']}"}]]}
                )
            except: pass
    else:
        send(chat_id,"*✅ پرداخت انجام شد!\n\n⏳ سفارش در حال پردازش است.\n💌 @ARKA_SUPPORT_IR*")

def complete_order(order_id):
    data   = load_data()
    target = next((o for o in data["orders"] if o["id"]==order_id),None)
    if not target: return False,"سفارش یافت نشد."
    if target["status"]=="done": return False,"این سفارش قبلاً تکمیل شده."
    target["status"]="done"; save_data(data)
    masked=mask_user_id(target["user_id"]); jalali_now=now_jalali_str()
    channel=data["settings"]["channel"]
    requests.post(f"{BASE_URL}/sendMessage", json={
        "chat_id":    channel,
        "text":       f"*✅ گزارش خرید #موفق\n\n📦 {target['service']}\n🔢 {target['amount']:,}\n💰 {target['price']:,} تومان\n👤 {masked}\n🕒 {jalali_now}*",
        "parse_mode": "Markdown",
        "reply_markup":{"inline_keyboard":[[{"text":"ربات ممبر | بازدید ایران 🚀","url":f"https://ble.ir/{BOT_USERNAME}"}]]}
    }, timeout=10)
    return True, target

# ══════════════════════════════════════════
#  ADMIN LOOKUP MAPS
# ══════════════════════════════════════════
PRICE_MAP = {
    "ap_price_bale_view":       ("bale_view_single","بازدید بله"),
    "ap_price_reaction":        ("bale_reaction",   "ری‌اکشن"),
    "ap_price_rubika_view":     ("rubika_view",     "بازدید روبیکا"),
    "ap_price_eitaa_view":      ("eitaa_view",      "بازدید ایتا"),
    "ap_price_bale_member":     ("bale_member",     "ممبر بله"),
    "ap_price_rubika_member":   ("rubika_member",   "ممبر روبیکا"),
    "ap_price_eitaa_member":    ("eitaa_member",    "ممبر ایتا"),
    "ap_price_rubika_follower": ("rubika_follower", "فالوور روبیکا"),
}
MM_MAP = {
    "ap_mm_bale_view":       "bale_view_single",
    "ap_mm_reaction":        "bale_reaction",
    "ap_mm_rubika_view":     "rubika_view",
    "ap_mm_eitaa_view":      "eitaa_view",
    "ap_mm_bale_member":     "bale_member",
    "ap_mm_rubika_member":   "rubika_member",
    "ap_mm_eitaa_member":    "eitaa_member",
    "ap_mm_rubika_follower": "rubika_follower",
}
STOCK_MAP = {

"ap_stock_bale_view":       "bale_view_single",
    "ap_stock_reaction":        "bale_reaction",
    "ap_stock_rubika_view":     "rubika_view",
    "ap_stock_eitaa_view":      "eitaa_view",
    "ap_stock_bale_member":     "bale_member",
    "ap_stock_rubika_member":   "rubika_member",
    "ap_stock_eitaa_member":    "eitaa_member",
    "ap_stock_rubika_follower": "rubika_follower",
}
TOGGLE_MAP = {
    "👁️ بازدید بله روشن/خاموش":      ("bale_view_single","بازدید بله"),
    "❤️ ری‌اکشن روشن/خاموش":         ("bale_reaction",   "ری‌اکشن"),
    "🔴 بازدید روبیکا روشن/خاموش":  ("rubika_view",     "بازدید روبیکا"),
    "🟢 بازدید ایتا روشن/خاموش":    ("eitaa_view",      "بازدید ایتا"),
    "🔵 ممبر بله روشن/خاموش":        ("bale_member",     "ممبر بله"),
    "🔴 ممبر روبیکا روشن/خاموش":    ("rubika_member",   "ممبر روبیکا"),
    "🟢 ممبر ایتا روشن/خاموش":      ("eitaa_member",    "ممبر ایتا"),
    "🟣 فالوور روبیکا روشن/خاموش":  ("rubika_follower", "فالوور روبیکا"),
}
MM_BTNS = {
    "🔢 بازدید بله":      "ap_mm_bale_view",
    "🔢 ری‌اکشن":         "ap_mm_reaction",
    "🔢 بازدید روبیکا":  "ap_mm_rubika_view",
    "🔢 بازدید ایتا":    "ap_mm_eitaa_view",
    "🔢 ممبر بله":        "ap_mm_bale_member",
    "🔢 ممبر روبیکا":    "ap_mm_rubika_member",
    "🔢 ممبر ایتا":      "ap_mm_eitaa_member",
    "🔢 فالوور روبیکا":  "ap_mm_rubika_follower",
}
PRICE_BTNS = {
    "💰 نرخ بازدید بله":      "ap_price_bale_view",
    "💰 نرخ ری‌اکشن":         "ap_price_reaction",
    "💰 نرخ بازدید روبیکا":  "ap_price_rubika_view",
    "💰 نرخ بازدید ایتا":    "ap_price_eitaa_view",
    "💰 نرخ ممبر بله":        "ap_price_bale_member",
    "💰 نرخ ممبر روبیکا":    "ap_price_rubika_member",
    "💰 نرخ ممبر ایتا":      "ap_price_eitaa_member",
    "💰 نرخ فالوور روبیکا":  "ap_price_rubika_follower",
}
STOCK_BTNS = {
    "📦 موجودی بازدید بله":      "ap_stock_bale_view",
    "📦 موجودی ری‌اکشن":         "ap_stock_reaction",
    "📦 موجودی بازدید روبیکا":  "ap_stock_rubika_view",
    "📦 موجودی بازدید ایتا":    "ap_stock_eitaa_view",
    "📦 موجودی ممبر بله":        "ap_stock_bale_member",
    "📦 موجودی ممبر روبیکا":    "ap_stock_rubika_member",
    "📦 موجودی ممبر ایتا":      "ap_stock_eitaa_member",
    "📦 موجودی فالوور روبیکا":  "ap_stock_rubika_follower",
}

# ══════════════════════════════════════════
#  ADMIN PANEL
# ══════════════════════════════════════════
def send_admin_panel(chat_id):
    data = load_data()
    s  = data["settings"]
    st = data["stats"]
    td = st["daily_stats"].get(get_today(),{})
    open_t   = sum(1 for t in data["tickets"].values() if t.get("status")=="open")
    closed_t = sum(1 for t in data["tickets"].values() if t.get("status")=="closed")
    send(chat_id,
        f"*🔧 پنل مدیریت ربات آرکا\n\n"
        f"━━━━━━━━━━━━\n"
        f"👥 کاربران: {st['total_users']:,}  |  📦 سفارشات: {st['total_orders']:,}\n"
        f"💰 درآمد کل: {st['total_revenue']:,} تومان\n"
        f"📅 امروز: {td.get('orders',0):,} سفارش | {td.get('revenue',0):,} تومان\n"
        f"🎫 تیکت باز: {open_t} | بسته: {closed_t}\n"
        f"🔒 جوین اجباری: {'✅' if s['forced_join'] else '❌'}\n"
        f"━━━━━━━━━━━━\n\n"
        f"👇 یک بخش را انتخاب کنید:*",
        kb(
            ["📊 آمار و گزارشات",   "📦 مدیریت سفارشات"],
            ["⚙️ مدیریت خدمات",    "💰 نرخ و قیمت‌ها"],
            ["👥 مدیریت کاربران",  "📨 پیام همگانی"],
            ["🔒 جوین اجباری",     "📢 تنظیمات کانال"],
            ["📦 مدیریت موجودی",   "🗑️ پاک‌سازی تاریخچه"],
            ["🎫 تیکت‌های باز",    "🔴 تیکت‌های بسته"],
            ["🏠 خروج از پنل ادمین"]
        )
    )

def send_open_tickets(chat_id, data):
    tickets = [(tid,t) for tid,t in data["tickets"].items() if t.get("status")=="open"]
    if not tickets:
        send(chat_id,"*هیچ تیکت باز فعالی وجود ندارد.*",BACK_BTN); return
    send(chat_id,f"*🎫 تیکت‌های باز: {len(tickets)} مورد*")
    for tid,t in tickets[-20:]:
        uname_str = f"@{t['username']}" if t.get("username") else str(t.get("user_id",""))
        last_msg  = t["messages"][-1]["text"][:80] if t.get("messages") else "-"
        send(chat_id,
            f"*🎫 #{tid} | {t.get('name','?')} ({uname_str})\n"
            f"💬 {len(t.get('messages',[]))} پیام | آخرین: {last_msg}*",
            {"inline_keyboard":[
                [{"text":f"↩️ پاسخ به #{tid}","callback_data":f"reply_ticket|{tid}"}],
                [{"text":f"🔴 بستن #{tid}","callback_data":f"close_ticket|{tid}"}]
            ]}
        )
    send(chat_id,"👆 تیکت‌های باز", kb(["🗑️ ریست تیکت‌های باز","🔙 بازگشت"]))

def send_closed_tickets(chat_id, data):
    tickets = [(tid,t) for tid,t in data["tickets"].items() if t.get("status")=="closed"]
    if not tickets:
        send(chat_id,"*هیچ تیکت بسته‌ای وجود ندارد.*",BACK_BTN); return
    send(chat_id,f"*🔴 تیکت‌های بسته: {len(tickets)} مورد*")
    for tid,t in tickets[-20:]:
        uname_str = f"@{t['username']}" if t.get("username") else str(t.get("user_id",""))
        send(chat_id,
            f"*🔴 #{tid} | {t.get('name','?')} ({uname_str}) | {len(t.get('messages',[]))} پیام*"
        )
    send(chat_id,"👆 تیکت‌های بسته", kb(["🗑️ ریست تیکت‌های بسته","🔙 بازگشت"]))

def handle_admin(chat_id, text, data, states):
    uid   = str(chat_id)
    state = states.get(uid,"")

    if text in ("/cancel","🔙 بازگشت"):
        states[uid]="admin"; send_admin_panel(chat_id); return
    if text=="🏠 خروج از پنل ادمین":
        states.pop(uid,None); send_start(chat_id); return

    # ─ پاسخ به تیکت ────────────────────────────────────
    if state.startswith("ap_reply_ticket|"):
        tid = state.split("|",1)[1]
        admin_reply_to_ticket(chat_id, tid, text, data)
        states[uid]="admin"; return

    # ─ قیمت ─────────────────────────────────────────────
    if state in PRICE_MAP:
        key,label = PRICE_MAP[state]
        try:
            price=int(text.replace(",","").strip())
            data["settings"][key]["price_per_1000"]=price; save_data(data); states[uid]="admin"
            send(chat_id,f"*✅ نرخ {label} → {price:,} تومان*",BACK_BTN)
        except: send(chat_id,"*⚠️ فقط عدد ارسال کنید.",BACK_BTN)
        return

    # ─ min/max ──────────────────────────────────────────
    if state in MM_MAP:
        key=MM_MAP[state]
        try:
            parts=text.strip().split(); mn,mx=int(parts[0]),int(parts[1])
            assert mn<mx
            data["settings"][key]["min"]=mn; data["settings"][key]["max"]=mx
            save_data(data); states[uid]="admin"
            send(chat_id,f"✅ {mn:,} تا {mx:,}*",BACK_BTN)
        except: send(chat_id,"*⚠️ فرمت اشتباه. مثال: 100 5000",BACK_BTN)
        return

    # ─ موجودی ───────────────────────────────────────────
    if state in STOCK_MAP:
        key=STOCK_MAP[state]
        try:
            val=text.strip()
            stock=999999 if val in ("0","نامحدود","-") else int(val.replace(",",""))
            data["settings"][key]["stock"]=stock; save_data(data); states[uid]="admin"
            disp="نامحدود" if stock>=999999 else f"{stock:,}"
            send(chat_id,f"✅ موجودی {SVCLABEL.get(key,key)} → {disp}*",BACK_BTN)
        except: send(chat_id,"*⚠️ فقط عدد. برای نامحدود: 0",BACK_BTN)
        return

    # ─ سایر state ها ────────────────────────────────────
    if state=="ap_set_channel":
        ch=text.strip()
        if not ch.startswith("@"): send(chat_id,"⚠️ با @ شروع شود.",BACK_BTN); return
        data["settings"]["channel"]=ch; save_data(data); states[uid]="admin"
        send(chat_id,f"✅ کانال → {ch}*",BACK_BTN); return

    if state=="ap_set_link":
        data["settings"]["channel_link"]=text.strip(); save_data(data); states[uid]="admin"
        send(chat_id,"*✅ لینک کانال به‌روز شد.*",BACK_BTN); return

    if state=="ap_broadcast":
        if text=="❌ لغو": states[uid]="admin"; send_admin_panel(chat_id); return
        ok=fail=0
        for u in data["users"].values():
            try: send(u["chat_id"],text); ok+=1; time.sleep(0.05)
            except: fail+=1
        states[uid]="admin"
        send(chat_id,f"*📨 ارسال شد.\n✅ {ok}\n❌ {fail}*",BACK_BTN); return

    if state=="ap_block":
        try:
            t=str(int(text.strip()))
            if t in data["users"]: data["users"][t]["blocked"]=True; save_data(data); send(chat_id,f"*✅ {t} مسدود شد.*",BACK_BTN)
            else: send(chat_id,"*⚠️ کاربر یافت نشد.",BACK_BTN)
        except: send(chat_id,"⚠️ آیدی اشتباه.",BACK_BTN)
        states[uid]="admin"; return

    if state=="ap_unblock":
        try:
            t=str(int(text.strip()))
            if t in data["users"]: data["users"][t]["blocked"]=False; save_data(data); send(chat_id,f"✅ {t} رفع مسدودیت شد.*",BACK_BTN)
            else: send(chat_id,"*⚠️ کاربر یافت نشد.",BACK_BTN)
        except: send(chat_id,"⚠️ آیدی اشتباه.",BACK_BTN)
        states[uid]="admin"; return

    if state=="ap_search":
        try:
            t=str(int(text.strip())); u=data["users"].get(t)
            if u:
                send(chat_id,
                    f"🔍 {t}:\n"
                    f"👤 {u.get('first_name','?')} | @{u.get('username','ندارد')}\n"
                    f"📅 {u.get('first_seen','')[:10]}\n"
                    f"📦 {u.get('orders',0)} سفارش | {u.get('total_spent',0):,} تومان\n"
                    f"🚫 {'مسدود' if u.get('blocked') else 'فعال'}*",BACK_BTN)
            else: send(chat_id,"*⚠️ یافت نشد.",BACK_BTN)
        except: send(chat_id,"⚠️ آیدی اشتباه.",BACK_BTN)
        states[uid]="admin"; return

    # ══════════════════════════════════════════
    #  منوهای پنل
    # ══════════════════════════════════════════
    if text=="📊 آمار و گزارشات":
        send(chat_id,"📊 آمار*",
             kb(["📊 آمار کلی","📅 آمار امروز"],["📊 آمار هفتگی","📊 آمار ماهانه"],
                ["🔄 ریست آمار امروز"],["🔙 بازگشت"])); return

    if text=="📦 مدیریت سفارشات":
        send(chat_id,"*📦 سفارشات*",
             kb(["⏳ سفارش‌های فعال"],["✅ سفارش‌های تکمیل‌شده"],
                ["📋 ۱۰ سفارش آخر","📤 خروجی کامل آمار"],["🔙 بازگشت"])); return

    if text=="⚙️ مدیریت خدمات":
        s=data["settings"]
        def st(k): return "✅" if s[k]["enabled"] else "❌"
        send(chat_id,
            f"*⚙️ خدمات\n\n"
            f"👁️بله:{st('bale_view_single')} ❤️ری‌اکشن:{st('bale_reaction')}\n"
            f"🔴روبیکا:{st('rubika_view')} 🟢ایتا:{st('eitaa_view')}\n"
            f"🔵ممبر بله:{st('bale_member')} 🔴ممبر روبیکا:{st('rubika_member')}\n"
            f"🟢ممبر ایتا:{st('eitaa_member')} 🟣فالوور:{st('rubika_follower')}*",
            kb(
                ["👁️ بازدید بله روشن/خاموش",     "❤️ ری‌اکشن روشن/خاموش"],
                ["🔴 بازدید روبیکا روشن/خاموش", "🟢 بازدید ایتا روشن/خاموش"],
                ["🔵 ممبر بله روشن/خاموش",       "🔴 ممبر روبیکا روشن/خاموش"],
                ["🟢 ممبر ایتا روشن/خاموش",     "🟣 فالوور روبیکا روشن/خاموش"],
                ["🔢 تغییر حداقل/حداکثر"],
                ["🔙 بازگشت"]
            )); return

    if text=="💰 نرخ و قیمت‌ها":
        s=data["settings"]
        def p(k): return f"{s[k]['price_per_1000']:,}"
        send(chat_id,
            f"*💰 نرخ‌ها (تومان/۱۰۰۰)\n\n"
            f"👁️بازدید بله:{p('bale_view_single')}\n❤️ری‌اکشن:{p('bale_reaction')}\n"
            f"🔴بازدید روبیکا:{p('rubika_view')}\n🟢بازدید ایتا:{p('eitaa_view')}\n"
            f"🔵ممبر بله:{p('bale_member')}\n🔴ممبر روبیکا:{p('rubika_member')}\n"
            f"🟢ممبر ایتا:{p('eitaa_member')}\n🟣فالوور:{p('rubika_follower')}*",
            kb(
                ["💰 نرخ بازدید بله",      "💰 نرخ ری‌اکشن"],
                ["💰 نرخ بازدید روبیکا",  "💰 نرخ بازدید ایتا"],
                ["💰 نرخ ممبر بله",        "💰 نرخ ممبر روبیکا"],
                ["💰 نرخ ممبر ایتا",       "💰 نرخ فالوور روبیکا"],
                ["🔙 بازگشت"]
            )); return

    if text=="📦 مدیریت موجودی":
        s=data["settings"]
        def stk(k):
            v=s[k].get("stock",999999)
            return "نامحدود" if v>=999999 else f"{v:,}"
        send(chat_id,
            f"*📦 موجودی\n\n"
            f"👁️بازدید بله:{stk('bale_view_single')}\n❤️ری‌اکشن:{stk('bale_reaction')}\n"
            f"🔴بازدید روبیکا:{stk('rubika_view')}\n🟢بازدید ایتا:{stk('eitaa_view')}\n"
            f"🔵ممبر بله:{stk('bale_member')}\n🔴ممبر روبیکا:{stk('rubika_member')}\n"

f"🟢ممبر ایتا:{stk('eitaa_member')}\n🟣فالوور:{stk('rubika_follower')}*",
            kb(
                ["📦 موجودی بازدید بله",      "📦 موجودی ری‌اکشن"],
                ["📦 موجودی بازدید روبیکا",  "📦 موجودی بازدید ایتا"],
                ["📦 موجودی ممبر بله",        "📦 موجودی ممبر روبیکا"],
                ["📦 موجودی ممبر ایتا",       "📦 موجودی فالوور روبیکا"],
                ["♾️ نامحدود همه سرویس‌ها"],
                ["🔙 بازگشت"]
            )); return

    if text=="🗑️ پاک‌سازی تاریخچه":
        send(chat_id,"*🗑️ پاک‌سازی\n\n⚠️ برگشت‌پذیر نیست!",
             kb(["🗑️ پاک کردن همه سفارشات"],["🗑️ پاک کردن سفارشات تکمیل‌شده"],
                ["🗑️ پاک کردن آمار روزانه"],["🗑️ ریست کامل (همه چیز)"],["🔙 بازگشت"])); return

    if text=="🎫 تیکت‌های باز":   send_open_tickets(chat_id,data);   return
    if text=="🔴 تیکت‌های بسته": send_closed_tickets(chat_id,data); return

    if text=="👥 مدیریت کاربران":
        bc=sum(1 for u in data["users"].values() if u.get("blocked"))
        send(chat_id,f"👥 کاربران: {len(data['users']):,} | مسدود: {bc}*",
             kb(["🚫 مسدود کردن کاربر","✅ رفع مسدودیت"],
                ["📵 لیست کاربران مسدود","🔍 جستجوی کاربر"],["🔙 بازگشت"])); return

    if text=="📢 تنظیمات کانال":
        send(chat_id,"*📢 تنظیمات کانال*",
             kb(["📢 تغییر آیدی کانال","📌 تغییر لینک کانال"],["🔙 بازگشت"])); return

    if text=="🔒 جوین اجباری":
        cur=data["settings"]["forced_join"]; data["settings"]["forced_join"]=not cur
        save_data(data); send(chat_id,f"*🔒 {'✅ فعال شد' if not cur else '❌ غیرفعال شد'}*",BACK_BTN); return

    if text=="📨 پیام همگانی":
        states[uid]="ap_broadcast"
        send(chat_id,"*📨 متن پیام را ارسال کنید:*",kb(["❌ لغو"])); return

    # ─ پاک‌سازی ─────────────────────────────────────────
    if text=="🗑️ پاک کردن همه سفارشات":
        data["orders"]=[]; data["stats"]["total_orders"]=0; data["stats"]["total_revenue"]=0
        save_data(data); send(chat_id,"*✅ همه سفارشات پاک شد.*",BACK_BTN); return
    if text=="🗑️ پاک کردن سفارشات تکمیل‌شده":
        before=len(data["orders"]); data["orders"]=[o for o in data["orders"] if o.get("status")!="done"]
        save_data(data); send(chat_id,f"*✅ {before-len(data['orders'])} سفارش پاک شد.*",BACK_BTN); return
    if text=="🗑️ پاک کردن آمار روزانه":
        data["stats"]["daily_stats"]={}; save_data(data)
        send(chat_id,"*✅ آمار روزانه پاک شد.*",BACK_BTN); return
    if text=="🗑️ ریست کامل (همه چیز)":
        nd=default_data(); nd["settings"]=data["settings"]; save_data(nd)
        send(chat_id,"*✅ ریست کامل. تنظیمات حفظ شد.*",BACK_BTN); return

    # ─ تیکت‌ها ──────────────────────────────────────────
    if text=="🗑️ ریست تیکت‌های باز":
        data["tickets"]={tid:t for tid,t in data["tickets"].items() if t.get("status")!="open"}
        save_data(data); send(chat_id,"*✅ تیکت‌های باز پاک شد.*",BACK_BTN); return
    if text=="🗑️ ریست تیکت‌های بسته":
        data["tickets"]={tid:t for tid,t in data["tickets"].items() if t.get("status")!="closed"}
        save_data(data); send(chat_id,"*✅ تیکت‌های بسته پاک شد.*",BACK_BTN); return

    # ─ آمار ─────────────────────────────────────────────
    if text=="📊 آمار کلی":
        st=data["stats"]
        send(chat_id,f"*📊:\n👥 {st['total_users']:,}\n📦 {st['total_orders']:,}\n💰 {st['total_revenue']:,} تومان*",BACK_BTN); return
    if text=="📅 آمار امروز":
        td=data["stats"]["daily_stats"].get(get_today(),{})
        send(chat_id,f"*📅 امروز:\n📦 {td.get('orders',0):,}\n💵 {td.get('revenue',0):,} تومان*",BACK_BTN); return
    if text=="📊 آمار هفتگی":
        to=tr=0
        for i in range(7):
            d=data["stats"]["daily_stats"].get((datetime.now()-timedelta(days=i)).strftime("%Y-%m-%d"),{})
            to+=d.get("orders",0); tr+=d.get("revenue",0)
        send(chat_id,f"*📊 ۷ روز:\n📦 {to:,}\n💰 {tr:,} تومان*",BACK_BTN); return
    if text=="📊 آمار ماهانه":
        month=datetime.now().strftime("%Y-%m"); to=tr=0
        for day,d in data["stats"]["daily_stats"].items():
            if day.startswith(month): to+=d.get("orders",0); tr+=d.get("revenue",0)
        send(chat_id,f"*📊 این ماه:\n📦 {to:,}\n💰 {tr:,} تومان*",BACK_BTN); return
    if text=="🔄 ریست آمار امروز":
        data["stats"]["daily_stats"][get_today()]={"orders":0,"revenue":0}; save_data(data)
        send(chat_id,"*✅ آمار امروز ریست شد.*",BACK_BTN); return

    # ─ سفارشات ──────────────────────────────────────────
    def _olist(lst,title,show_btn):
        if not lst: send(chat_id,f"*{title}: خالی*",BACK_BTN); return
        send(chat_id,f"*{title}: {len(lst)} مورد*")
        for o in lst[-15:]:
            st=o.get("status","")
            lbl="⏳ انتظار پرداخت" if st=="pending_payment" else ("🔄 در حال پردازش" if st=="pending" else "✅ تکمیل")
            mu={"inline_keyboard":[[{"text":"✅ تکمیل","callback_data":f"complete|{o['id']}"}]]} if show_btn and st=="pending" else None
            send(chat_id,f"*🆔{o.get('id','?')}|👤{o.get('user_id','?')}\n📦{o.get('service','?')}|{o.get('amount',0):,}|{o.get('price',0):,}t\n{lbl}*",mu)
        send(chat_id,"👆",BACK_BTN)

    if text=="⏳ سفارش‌های فعال":
        _olist([o for o in data["orders"] if o.get("status") in ("pending","pending_payment")],"⏳ فعال",True); return
    if text=="✅ سفارش‌های تکمیل‌شده":
        _olist([o for o in data["orders"] if o.get("status")=="done"],"✅ تکمیل‌شده",False); return
    if text=="📋 ۱۰ سفارش آخر":
        lst=data["orders"][-10:]
        if not lst: send(chat_id,"*خالی*",BACK_BTN); return
        msg="*📋 ۱۰ سفارش آخر:\n\n"
        for o in reversed(lst): msg+=f"🆔{o.get('id','?')}|{o.get('service','?')}|{o.get('amount',0):,}|{o.get('price',0):,}t|{o.get('status','?')}\n"
        send(chat_id,msg+"*",BACK_BTN); return
    if text=="📤 خروجی کامل آمار":
        st=data["stats"]
        msg=f"*📤 آمار:\n👥{st['total_users']:,}\n📦{st['total_orders']:,}\n💰{st['total_revenue']:,}t\n\n۷روز:\n"
        for i in range(7):
            day=(datetime.now()-timedelta(days=i)).strftime("%Y-%m-%d")
            d=st["daily_stats"].get(day,{})
            msg+=f"{day}:{d.get('orders',0)}|{d.get('revenue',0):,}t\n"
        send(chat_id,msg+"*",BACK_BTN); return

    # ─ toggle ────────────────────────────────────────────
    if text in TOGGLE_MAP:
        key,label=TOGGLE_MAP[text]; cur=data["settings"][key]["enabled"]
        data["settings"][key]["enabled"]=not cur; save_data(data)
        send(chat_id,f"*{label} {'✅ فعال' if not cur else '❌ غیرفعال'} شد.*",BACK_BTN); return

    if text=="🔢 تغییر حداقل/حداکثر":
        s=data["settings"]
        def mm(k): return f"{s[k]['min']:,}-{s[k]['max']:,}"
        send(chat_id,
            f"*🔢 حداقل/حداکثر\n\n"
            f"👁️بازدید بله:{mm('bale_view_single')}\n❤️ری‌اکشن:{mm('bale_reaction')}\n"
            f"🔴بازدید روبیکا:{mm('rubika_view')}\n🟢بازدید ایتا:{mm('eitaa_view')}\n"
            f"🔵ممبر بله:{mm('bale_member')}\n🔴ممبر روبیکا:{mm('rubika_member')}\n"
            f"🟢ممبر ایتا:{mm('eitaa_member')}\n🟣فالوور:{mm('rubika_follower')}*",
            kb(
                ["🔢 بازدید بله","🔢 ری‌اکشن"],["🔢 بازدید روبیکا","🔢 بازدید ایتا"],
                ["🔢 ممبر بله","🔢 ممبر روبیکا"],["🔢 ممبر ایتا","🔢 فالوور روبیکا"],
                ["🔙 بازگشت"]
            )); return

    if text in MM_BTNS:
        st_key=MM_BTNS[text]; svc_key=MM_MAP[st_key]; states[uid]=st_key
        s=data["settings"][svc_key]
        send(chat_id,f"*فعلی: {s['min']:,} تا {s['max']:,}\nحداقل و حداکثر جدید (مثال: 100 5000):*",BACK_BTN); return

    if text in PRICE_BTNS:
        st_key=PRICE_BTNS[text]; svc_key=PRICE_MAP[st_key][0]; states[uid]=st_key
        send(chat_id,f"*نرخ فعلی: {data['settings'][svc_key]['price_per_1000']:,} تومان\nنرخ جدید:*",BACK_BTN); return

    if text in STOCK_BTNS:
        st_key=STOCK_BTNS[text]; svc_key=STOCK_MAP[st_key]; states[uid]=st_key
        cur=data["settings"][svc_key].get("stock",999999)
        send(chat_id,f"*موجودی {SVCLABEL.get(svc_key,svc_key)}: {'نامحدود' if cur>=999999 else f'{cur:,}'}\n\nموجودی جدید (0=نامحدود):*",BACK_BTN); return

    if text=="♾️ نامحدود همه سرویس‌ها":
        for k in ALL_SVC_KEYS: data["settings"][k]["stock"]=999999
        save_data(data); send(chat_id,"*✅ همه موجودی‌ها نامحدود شد.*",BACK_BTN); return

    # ─ کاربران ──────────────────────────────────────────
    if text=="🚫 مسدود کردن کاربر": states[uid]="ap_block"; send(chat_id,"*آیدی عددی:*",BACK_BTN); return
    if text=="✅ رفع مسدودیت":       states[uid]="ap_unblock"; send(chat_id,"*آیدی عددی:*",BACK_BTN); return
    if text=="🔍 جستجوی کاربر":      states[uid]="ap_search"; send(chat_id,"*آیدی عددی:*",BACK_BTN); return
    if text=="📵 لیست کاربران مسدود":
        bl=[(u,v) for u,v in data["users"].items() if v.get("blocked")]
        if not bl: send(chat_id,"*هیچ کاربر مسدودی نیست.*",BACK_BTN); return
        msg=f"*📵 مسدود ({len(bl)}):\n\n"
        for u,v in bl[:30]: msg+=f"🆔{u}|{v.get('first_name','?')}\n"
        send(chat_id,msg+"*",BACK_BTN); return

    # ─ کانال ────────────────────────────────────────────
    if text=="📢 تغییر آیدی کانال": states[uid]="ap_set_channel"; send(chat_id,f"*کانال فعلی: {data['settings']['channel']}\n\nجدید (@channel):*",BACK_BTN); return
    if text=="📌 تغییر لینک کانال": states[uid]="ap_set_link"; send(chat_id,f"*لینک فعلی: {data['settings']['channel_link']}\n\nجدید:*",BACK_BTN); return

    send_admin_panel(chat_id)

# ══════════════════════════════════════════
#  MAIN LOOP
# ══════════════════════════════════════════
last_update_id = 0
states         = {}

SVC_KEYS_TEXT = {
    "بازدید تکی 👁️":  "bale_view_single",
    "ری‌اکشن بله ❤️": "bale_reaction",
}
BTN_TO_SVC = {
    "🔴 سفارش بازدید | روبیکا ⚡️": "rubika_view",
    "🟢 سفارش بازدید | ایتا ☕️":   "eitaa_view",
    "🔵 سفارش ممبر | بله 🚀":       "bale_member",
    "🔴 سفارش ممبر | روبیکا ⚡️":   "rubika_member",
    "🟢 سفارش ممبر | ایتا ☕️":     "eitaa_member",
    "🟣 سفارش فالوور | روبیکا 🔥":  "rubika_follower",
}

print("===================================")
print("🤖 ربات فروش ممبر آرکا استارت شد")
print("===================================")

try:
    _me = requests.get(f"{BASE_URL}/getMe",timeout=10).json()
    if _me.get("ok") and _me["result"].get("username"):
        BOT_USERNAME = _me["result"]["username"]
        print(f"✅ یوزرنیم: @{BOT_USERNAME}")
except Exception as e:
    print(f"⚠️ یوزرنیم: {e}")

while True:
    try:
        resp   = requests.get(f"{BASE_URL}/getUpdates",
                              params={"offset":last_update_id+1,"timeout":25},timeout=30)
        result = resp.json()
        if not isinstance(result,dict) or not result.get("ok"):
            time.sleep(2); continue
        updates = result.get("result",[])
        if not isinstance(updates,list):
            time.sleep(2); continue

        for upd in updates:
            try:
                last_update_id = upd["update_id"]
                data = load_data()

                # ── Pre-checkout ─────────────────────────
                if "pre_checkout_query" in upd:
                    pcq=upd["pre_checkout_query"]
                    requests.post(f"{BASE_URL}/answerPreCheckoutQuery",
                                  json={"pre_checkout_query_id":pcq["id"],"ok":True},timeout=10)
                    continue

                # ── Callback ─────────────────────────────
                if "callback_query" in upd:
                    cb      = upd["callback_query"]
                    chat_id = cb["message"]["chat"]["id"]
                    cb_data = cb.get("data","")
                    requests.post(f"{BASE_URL}/answerCallbackQuery",
                                  json={"callback_query_id":cb["id"]},timeout=5)

                    if cb_data=="check_join":
                        if check_membership(chat_id): register_user(data,chat_id); send_start(chat_id)
                        else: send_not_joined(chat_id)

                    elif cb_data=="cancel_order":
                        states.pop(str(chat_id),None)
                        send(chat_id,"*❌ سفارش لغو شد.*"); send_start(chat_id)

                    elif cb_data.startswith("complete|"):
                        if not is_admin(chat_id): continue
                        oid=cb_data.split(

"|",1)[1]
                        ok,res=complete_order(oid)
                        send(chat_id,f"*{'✅ تکمیل شد.' if ok else '⚠️ '+str(res)}")

                    elif cb_data.startswith("reply_ticket|"):
                        if not is_admin(chat_id): continue
                        tid=cb_data.split("|",1)[1]
                        t=data["tickets"].get(tid)
                        if not t: send(chat_id,"⚠️ تیکت یافت نشد."); continue
                        if t.get("status")=="closed": send(chat_id,f"⚠️ تیکت #{tid} بسته است.*"); continue
                        states[str(chat_id)]=f"ap_reply_ticket|{tid}"
                        history=""
                        for m in t.get("messages",[])[-5:]:
                            sender="👤 کاربر" if m["from"]=="user" else "🛡️ ادمین"
                            history+=f"{sender}: {m['text'][:100]}\n"
                        send(chat_id,
                            f"*↩️ پاسخ به تیکت #{tid}\n\n"
                            f"📝 آخرین پیام‌ها:\n{history}\n\n"
                            f"پاسخ خود را ارسال کنید:*",
                            kb(["🔙 بازگشت"])
                        )

                    elif cb_data.startswith("close_ticket|"):
                        if not is_admin(chat_id): continue
                        tid=cb_data.split("|",1)[1]
                        t=data["tickets"].get(tid)
                        if t:
                            t["status"]="closed"; save_data(data)
                            send(chat_id,f"*✅ تیکت #{tid} بسته شد.*")
                            try:
                                send(t["user_id"],
                                    f"*🔴 گفتگوی #{tid} توسط پشتیبانی بسته شد.\n\n"
                                    f"برای مشکل جدید می‌توانید دوباره پیام بدید.*",
                                    BACK_BTN_USER
                                )
                                states.pop(str(t["user_id"]),None)
                            except: pass
                        else: send(chat_id,"*⚠️ تیکت یافت نشد.")
                    continue

                # ── Message ──────────────────────────────
                if "message" not in upd: continue
                msg     = upd["message"]
                chat_id = msg["chat"]["id"]
                uid     = str(chat_id)
                uinfo   = msg.get("from",{})

                if "successful_payment" in msg:
                    register_successful_order(chat_id,msg["successful_payment"].get("invoice_payload",""))
                    states.pop(uid,None); continue

                text = msg.get("text","").strip()
                if not text: continue

                register_user(data,chat_id,uinfo)

                if data["users"].get(uid,{}).get("blocked"):
                    send(chat_id,"⛔ دسترسی شما مسدود شده است.*"); continue

                if text=="/admin":
                    if is_admin(chat_id): states[uid]="admin"; send_admin_panel(chat_id)
                    continue

                cur_state=states.get(uid,"")
                if cur_state=="admin" or cur_state.startswith("ap_"):
                    handle_admin(chat_id,text,data,states); continue

                if not check_membership(chat_id):
                    send_join_required(chat_id); continue

                if text=="/start":
                    states.pop(uid,None); send_start(chat_id); continue

                if text in ("🔙 بازگشت به منوی اصلی 🏠","🏠 بازگشت","🔙 بازگشت"):
                    states.pop(uid,None); send_start(chat_id); continue

                # ─ منوی اصلی ─────────────────────────────
                if text=="سفارش بازدید 👁️":
                    states.pop(uid,None); send_platform(chat_id); continue
                if text=="سفارش ممبر 👥":
                    states.pop(uid,None); send_member_platform(chat_id); continue
                if text=="حساب کاربری 👤":
                    send_account(chat_id); continue
                if text=="پیگیری سفارش 🔎":
                    send_tracking(chat_id); continue
                if text=="قوانین ⚖️":
                    send_rules(chat_id); continue
                if text=="📞 پشتیبانی":
                    states[uid]="support"; send_support_menu(chat_id); continue

                # ─ بازدید بله زیرمنو ─────────────────────
                if text=="🔵 سفارش بازدید | بله 🚀":
                    send_bale_services(chat_id); continue

                # ─ سرویس مستقیم ──────────────────────────
                if text in BTN_TO_SVC:
                    check_stock_and_start(chat_id,BTN_TO_SVC[text],data,states); continue

                if text in SVC_KEYS_TEXT:
                    check_stock_and_start(chat_id,SVC_KEYS_TEXT[text],data,states); continue

                # ─ پشتیبانی: بستن تیکت ──────────────────
                if text=="❌ بستن تیکت":
                    handle_support_message(chat_id,text,data,states,uinfo); continue

                # ─ اگه در state پشتیبانی بود ─────────────
                cur_state=states.get(uid,"")
                if cur_state=="support":
                    handle_support_message(chat_id,text,data,states,uinfo); continue

                # ─ اگه تیکت باز دارد → ادامه گفتگو ──────
                tid,t=get_user_open_ticket(data,chat_id)
                if tid:
                    handle_support_message(chat_id,text,data,states,uinfo); continue

                # ─ تعداد سفارش ───────────────────────────
                if cur_state.startswith("order_qty|"):
                    key=cur_state.split("|")[1]
                    s=data["settings"][key]
                    try: qty=int(text.replace(",","").strip())
                    except: send(chat_id,"*⚠️ فقط عدد ارسال کنید."); continue
                    if qty<s["min"]:
                        send(chat_id,f"⚠️ حداقل {s['min']:,} می‌باشد."); continue
                    if qty>s["max"]:
                        send(chat_id,f"⚠️ حداکثر {s['max']:,} می‌باشد."); continue
                    stock=s.get("stock",999999)
                    if stock<qty:
                        send(chat_id,f"⚠️ موجودی ربات {stock:,} عدد هست. عدد کمتری وارد کنید.*"); continue
                    price=int(qty*s["price_per_1000"]/1000)
                    states[uid]=f"order_link|{key}|{qty}|{price}"
                    platform=SVC_PLATFORM.get(key,"bale")
                    if platform=="rubika": hint="🔗 لینک روبیکا:\n• https://rubika.ir/channel\n• @username"
                    elif platform=="eitaa": hint="🔗 لینک ایتا:\n• https://eitaa.com/channel\n• @username"
                    else: hint="🔗 لینک بله:\n• https://ble.ir/channel\n• @username"
                    send(chat_id,f"*✅ تعداد {qty:,} | مبلغ {price:,} تومان\n\n{hint}*",BACK_BTN_USER); continue

                # ─ لینک سفارش ────────────────────────────
                if cur_state.startswith("order_link|"):
                    parts=cur_state.split("|"); key=parts[1]; qty=int(parts[2]); price=int(parts[3])
                    link=text.strip(); platform=SVC_PLATFORM.get(key,"bale")
                    if platform=="rubika":
                        valid=validate_rubika_link(link)
                        err="*⚠️ لینک روبیکا معتبر نیست!\n• https://rubika.ir/channel\n• @username"
                    elif platform=="eitaa":
                        valid=validate_eitaa_link(link)
                        err="⚠️ لینک ایتا معتبر نیست!\n• https://eitaa.com/channel\n• @username"
                    else:
                        valid=validate_bale_link(link)
                        err="⚠️ لینک بله معتبر نیست!\n• https://ble.ir/channel\n• @username"
                    if not valid: send(chat_id,err); continue
                    states.pop(uid,None); send_invoice(chat_id,key,qty,price,link); continue

                # ─ fallback ───────────────────────────────
                send(chat_id,"👇 از دکمه‌های منو استفاده کنید:*",
                     kb(["سفارش بازدید 👁️","سفارش ممبر 👥"],
                        ["حساب کاربری 👤","پیگیری سفارش 🔎"],
                        ["قوانین ⚖️","📞 پشتیبانی"]))

            except Exception as ie:
                print(f"inner error: {ie}")
                continue

        time.sleep(1)

    except Exception as e:
        print(f"ERROR: {e}")
        time.sleep(5)
