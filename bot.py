import logging
import os
import random
from collections import defaultdict
from typing import Dict, List

from dotenv import load_dotenv
from openai import AsyncOpenAI
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

load_dotenv()
logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
logger = logging.getLogger("eco-energy-bot")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE") or None
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")
client = AsyncOpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_API_BASE) if OPENAI_API_KEY else None
ai_history: Dict[int, List[dict]] = defaultdict(list)
sessions: Dict[int, dict] = {}
content_seen: Dict[int, dict] = defaultdict(dict)

MAIN_BUTTONS = [
    ["⚡ Սկսել թեստ", "🎮 Խաղալ"],
    ["🔋 Համեմատել էներգիայի ծախսը", "📚 Իմանալ ավելին"],
    ["🌱 Ստանալ էկո խորհուրդներ", "📊 Իմ արդյունքները"],
    ["🤖 ԱԲ օգնական", "❓ Օգնություն"],
]

SYSTEM_PROMPT = """Դու EcoEnergyBot-ի հայերեն էներգաարդյունավետության խորհրդատուն ես։
ՊԱՏԱՍԽԱՆԻՐ ՄԻԱՅՆ ՊԱՐԶ ԱՐԵՎԵԼԱՀԱՅԵՐԵՆՈՎ։ Մի օգտագործիր անգլերեն նախադասություններ կամ անգլերեն բառեր։
Փոխարենը գրիր հայերեն՝ «սպասման ռեժիմ», «էներգախնայող լամպ», «էլեկտրաէներգիա»։ Միայն չափման միավորները
կարող են մնալ՝ Վտ, կՎտժ, °C։ Պատասխանիր հենց օգտատիրոջ հարցին, մի շեղվիր և մի հորինիր հարցի իմաստը։
Եթե հարցը անորոշ է, մեկ կարճ ճշտող հարց տուր։ Օգնիր խնայել էլեկտրաէներգիա, ջուր և ջեռուցման ծախսեր՝
առանց վտանգավոր էլեկտրատեխնիկական խորհուրդների։ Պատասխանը պահիր պարզ, կարճ և գործնական՝ 2-5 քայլով։
Օգտագործիր բնական խոսակցական ձև՝ «փոխիր», «օգտագործիր», «անջատիր», ոչ թե ծանր պաշտոնական ձևեր։
Մի հորինիր բառեր և մի թարգմանիր բառացի։ «Շարժման սենսոր» գրիր, ոչ թե «շարժումայն անջատիչ»։"""

FAST_REPLIES = {
    "ինչ անեմ որ շատ խնայեմ": "Ավելի շատ խնայելու արագ քայլերը՝\n\n1. Փոխիր լամպերը էներգախնայող LED լամպերով։\n2. Չօգտագործվող սարքերը հանիր վարդակից։\n3. Ջեռուցումն ու օդորակիչը պահիր չափավոր ջերմաստիճանում։\n4. Փակիր պատուհանների և դռների ճեղքերը։\n5. Լվացքի մեքենան միացրու լիարժեք բեռնվածությամբ։",
    "ինչպես անեմ որ խնայեմ ավելի շատ": "Սկսիր ամենամեծ ծախս ունեցող սարքերից․ չափիր ջեռուցիչի, սառնարանի և օդորակիչի օգտագործման ժամերը, կրճատիր անօգուտ աշխատանքը, անջատիր սպասման ռեժիմը և ամեն ամիս համեմատիր հաշվիչի ցուցմունքը։",
    "ինչպես խնայել հոսանքը": "Հոսանք խնայելու համար օգտագործիր էներգախնայող լամպեր, անջատիր չօգտագործվող սարքերը, օդորակիչը պահիր մոտ 24–26°C-ում և սարքերը միացրու միայն անհրաժեշտ ժամանակ։",
    "ինչպես խնայել լույսի վրա": "Լույսի վրա խնայելու համար օգտագործիր էներգախնայող լամպեր, օրվա ընթացքում բացիր վարագույրները, անջատիր լույսը դատարկ սենյակում և լուսավորիր միայն այն հատվածը, որտեղ աշխատում ես։",
    "ինչպես խնայել լույսը": "Լույսի վրա խնայելու համար օգտագործիր էներգախնայող լամպեր, օրվա ընթացքում բացիր վարագույրները, անջատիր լույսը դատարկ սենյակում և լուսավորիր միայն այն հատվածը, որտեղ աշխատում ես։",
    "ինչպես խնայեմ լույսը": "Լույսը խնայելու համար՝\n\n1. Փոխիր հին լամպերը լուսադիոդային լամպերով։\n2. Ցերեկը բացիր վարագույրները և օգտագործիր բնական լույսը։\n3. Սենյակից դուրս գալիս անջատիր լույսը։\n4. Միացրու միայն անհրաժեշտ լույսը։\n5. Չօգտագործվող սարքերը լրիվ անջատիր։",
    "ինչպես խնայել էլեկտրաէներգիա": "Էլեկտրաէներգիա խնայելու համար՝ օգտագործիր լուսադիոդային լամպեր, անջատիր դատարկ սենյակի լույսը, հանիր չօգտագործվող սարքերը վարդակից և ջեռուցումն օգտագործիր չափավոր։",
}

INFO_CARDS = [
    "💡 LED լամպերը նույն լուսավորությունը տալիս են ավելի քիչ էլեկտրաէներգիայով։ Տան ամենաշատ օգտագործվող լամպերը առաջինը փոխիր։",
    "🌡️ Ջեռուցման համար չափավոր ջերմաստիճանը սովորաբար ավելի խնայող է, քան սենյակը շատ տաք պահելը։ Գիշերը կամ բացակայելիս նվազեցրու կարգավորումը։",
    "🔌 Սպասման ռեժիմում գտնվող սարքերը կարող են շարունակել փոքր քանակով էլեկտրաէներգիա ծախսել։ Օգտագործիր անջատիչով երկարացուցիչ։",
    "🧊 Սառնարանը մի դիր ջեռոցի, մարտկոցի կամ արևի ուղիղ ճառագայթների կողքին․ տաք միջավայրը մեծացնում է դրա աշխատանքը։",
    "🚿 Տաք ջրի խնայողությունը նաև էներգիայի խնայողություն է․ կարճացրու ցնցուղի ժամանակը և վերացրու ծորակի արտահոսքը։",
    "🧺 Լվացքի մեքենան միացրու լիարժեք բեռնվածությամբ, իսկ հնարավորության դեպքում օգտագործիր ցածր ջերմաստիճան։",
]

TIP_CARDS = [
    "🌱 Այսօրվա խորհուրդը․ օրը մեկ անգամ ստուգիր, թե որ սարքերն են անտեղի միացված և անջատիր դրանք։",
    "🌱 Այսօրվա խորհուրդը․ արևոտ ժամերին վարագույրները բացիր և արհեստական լույսը միացրու միայն անհրաժեշտության դեպքում։",
    "🌱 Այսօրվա խորհուրդը․ փակիր դռների ու պատուհանների ճեղքերը, որպեսզի ջեռուցված օդը դուրս չգա։",
    "🌱 Այսօրվա խորհուրդը․ օդորակիչի ֆիլտրը մաքուր պահիր․ կեղտոտ ֆիլտրը կարող է վատացնել արդյունավետությունը։",
    "🌱 Այսօրվա խորհուրդը․ սարք գնելիս նայիր ոչ միայն գնին, այլև դրա էներգասպառման պիտակին։",
    "🌱 Այսօրվա խորհուրդը․ ամիսը մեկ գրանցիր հաշվիչի ցուցմունքը, որ տեսնես՝ որ սովորությունն է իրականում օգնում։",
]

QUIZ_BANK = [
    ("Ո՞ր լամպն է սովորաբար ամենախնայողը։", ["LED", "Շիկացման", "Մոմ"], 0),
    ("Ի՞նչ անել չօգտագործվող լիցքավորիչի հետ։", ["Հանել վարդակից", "Թողնել միացված", "Փաթաթել պլաստիկով"], 0),
    ("Ո՞ր ջերմաստիճանն է ավելի խնայող օդորակիչի սառեցման ժամանակ։", ["16°C", "24–26°C", "30°C"], 1),
    ("Սառնարանի դուռը երկար բաց թողնելը…", ["Խնայում է", "Չի ազդում", "Ավելացնում է ծախսը"], 2),
    ("Լվացքի մեքենան ավելի խնայող է, երբ…", ["Կիսադատարկ է", "Լիարժեք է և ցածր ջերմաստիճանով", "Աշխատում է բաց դռնով"], 1),
    ("Ջեռուցման ծախսը նվազեցնելու համար լավ է…", ["Փակել պատուհանների ճեղքերը", "Բացել բոլոր պատուհանները", "Միացնել բոլոր սարքերը"], 0),
    ("Սպասման ռեժիմում գտնվող սարքերը…", ["Միշտ զրո են ծախսում", "Կարող են փոքր ծախս շարունակել", "Էլեկտրաէներգիա են արտադրում"], 1),
    ("Արևոտ օրերին ինչն է օգնում խնայել։", ["Օրվա լույսը օգտագործելը", "Բոլոր լույսերը միացնելը", "Վարագույրները փակելը"], 0),
    ("Սարքի ծախսը մոտավոր հաշվվում է՝", ["Վտ × ժամ / 1000", "Վտ + ժամ", "Վտ × 1000"], 0),
    ("Էկո սովորությունը պետք է լինի…", ["Միանգամյա", "Կայուն և ամենօրյա", "Միայն տոն օրերին"], 1),
]

ADVENTURE = [
    ("Անիին հասցրու Էներգիայի Կանաչ Քաղաք։ Առաջին դարպասը բացվում է, եթե ընտրես ճիշտ լույսը։", ["LED լամպ", "1000 Վտ շիկացման լամպ", "Բոլոր լույսերը"], 0),
    ("Քաղաքի ջրային կայանը շատ էներգիա է ծախսում։ Ի՞նչ քայլ է պետք անել։", ["Ծորակը թողնել բաց", "Վերացնել ջրի արտահոսքերը", "Ավելի երկար տաքացնել ջուրը"], 1),
    ("Անին հասավ սառնարանի լաբորատորիա։ Ո՞ր լուծումն է ճիշտ։", ["Սառնարանը դնել ջեռոցի կողքին", "Դուռը անընդհատ բացել", "Դնել արևից ու ջերմությունից հեռու"], 2),
    ("Վերջին կամուրջը կառուցվում է ջեռուցման խնայողությամբ։ Ընտրիր։", ["Փակել ճեղքերը և կարգավորել ջերմաստիճանը", "Պատուհանը բաց պահել", "Ջերմաստիճանը դնել առավելագույնի"], 0),
    ("Կանաչ Քաղաքի կենտրոնում մնացել է մեկ մարտկոց։ Ի՞նչ անել։", ["Անջատել սպասման ռեժիմում գտնվող սարքերը", "Միացնել բոլոր սարքերը", "Թողնել լիցքավորիչները միացված"], 0),
]

GAME_IMAGES = [
    "/home/ubuntu/eco-energy-bot/game-stage-1-fast.jpg",
    "/home/ubuntu/eco-energy-bot/game-stage-2-fast.jpg",
    "/home/ubuntu/eco-energy-bot/game-stage-3-fast.jpg",
    "/home/ubuntu/eco-energy-bot/game-stage-4-fast.jpg",
    "/home/ubuntu/eco-energy-bot/game-stage-5-fast.jpg",
]


def main_keyboard():
    return ReplyKeyboardMarkup(MAIN_BUTTONS, resize_keyboard=True, is_persistent=True)


def back_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Գլխավոր մենյու", callback_data="home")]])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    sessions.pop(user.id, None)
    await update.message.reply_text(
        f"Ողջույն, {user.first_name or 'ընկեր'}։ Ես EcoEnergyBot-ն եմ 🌿\n\n"
        "Քո էներգախնայողության օգնականը։ Ընտրիր բաժինը կամ միացրու ԱԲ օգնականը։",
        reply_markup=main_keyboard(),
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❓ Օգնություն\n\n"
        "⚡ Սկսել թեստ — ամեն անգամ 5 պատահական հարց\n"
        "🎮 Խաղալ — Անիի էներգախնայողության արկածը\n"
        "🤖 ԱԲ օգնական — հարցրու էներգիայի, ջեռուցման կամ ծախսի մասին\n"
        "📊 Իմ արդյունքները — քո վերջին միավորները\n\n"
        "Ցանկացած պահի /start-ը վերադարձնում է գլխավոր մենյու։",
        reply_markup=main_keyboard(),
    )


async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    previous = content_seen[user_id].get("info")
    choices = [i for i in range(len(INFO_CARDS)) if i != previous] or list(range(len(INFO_CARDS)))
    selected = random.choice(choices)
    content_seen[user_id]["info"] = selected
    await update.message.reply_text(
        f"📚 Իմանալ ավելին\n\n{INFO_CARDS[selected]}",
        reply_markup=back_keyboard(),
    )


async def tips(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    previous = content_seen[user_id].get("tip")
    choices = [i for i in range(len(TIP_CARDS)) if i != previous] or list(range(len(TIP_CARDS)))
    selected = random.choice(choices)
    content_seen[user_id]["tip"] = selected
    await update.message.reply_text(
        f"🌱 Նոր էկո խորհուրդ\n\n{TIP_CARDS[selected]}",
        reply_markup=back_keyboard(),
    )


async def compare(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔋 Գրիր օրինակ՝\n`սարք 1՝ 100 Վտ, 5 ժամ; սարք 2՝ 60 Վտ, 8 ժամ`\n\nԲանաձևը՝ Վտ × ժամ / 1000 = կՎտժ։ ԱԲ օգնականը կարող է նաև օգնել հաշվարկել։",
        parse_mode="Markdown", reply_markup=back_keyboard(),
    )


async def start_round(update: Update, context: ContextTypes.DEFAULT_TYPE, mode: str):
    user_id = update.effective_user.id
    bank = QUIZ_BANK if mode == "quiz" else ADVENTURE
    questions = random.sample(bank, 5) if mode == "quiz" else bank
    sessions[user_id] = {"mode": mode, "questions": questions, "index": 0, "score": 0}
    if mode == "game":
        await update.message.reply_text("🎮 Արկածը սկսվում է… Անիին հասցնենք Կանաչ Քաղաք ⚡🌿")
    await send_round_question(user_id, context)


async def send_round_question(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    state = sessions[user_id]
    if state["index"] >= len(state["questions"]):
        score = state["score"]
        if state["mode"] == "quiz":
            text = f"🎉 Թեստն ավարտվեց։ Քո արդյունքը՝ {score}/5։\n\n" + ("Գերազանց էներգախնայող ես 🌟" if score >= 4 else "Լավ սկիզբ է․ փորձիր նորից ու բարելավիր արդյունքը 🌱")
        else:
            text = f"🏙️ Անիին հասցրիր Կանաչ Քաղաք։ Արդյունք՝ {score}/{len(state['questions'])}։\n\nՔաղաքը փրկվեց էներգիայի վատնումից ⚡🌿"
        await context.bot.send_message(user_id, text, reply_markup=main_keyboard())
        return
    title = "⚡ Թեստ" if state["mode"] == "quiz" else "🎮 Անիի արկածը"
    question, answers, _ = state["questions"][state["index"]]
    keyboard = [[InlineKeyboardButton(answer, callback_data=f"round:{i}")] for i, answer in enumerate(answers)]
    progress = f"Քայլ {state['index'] + 1}/{len(state['questions'])}  {'🟩' * state['index']}{'⬜' * (len(state['questions']) - state['index'])}"
    caption = f"{title}\n{progress}\n\n{question}"
    if state["mode"] == "game" and os.path.exists(GAME_IMAGES[state["index"]]):
        with open(GAME_IMAGES[state["index"]], "rb") as image:
            await context.bot.send_photo(user_id, photo=image, caption=caption, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await context.bot.send_message(user_id, caption, reply_markup=InlineKeyboardMarkup(keyboard))


async def ai_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 ԱԲ օգնականը միացված է։ Գրիր քո հարցը։\n\nՕրինակ՝ «Ինչպե՞ս նվազեցնեմ տան հոսանքի ծախսը»։ Դուրս գալու համար սեղմիր /start։",
        reply_markup=main_keyboard(),
    )


async def ask_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not client:
        await update.message.reply_text("ԱԲ օգնականը միացված չէ․ .env-ում չկա OPENAI_API_KEY։")
        return
    user_id = update.effective_user.id
    question = update.message.text.strip()
    normalized = " ".join(question.lower().replace("՞", "").replace("?", "").split())
    if normalized in FAST_REPLIES:
        await update.message.reply_text(FAST_REPLIES[normalized], reply_markup=main_keyboard())
        return
    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    try:
        response = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, *ai_history[user_id][-8:], {"role": "user", "content": question}],
            temperature=0.2,
            max_tokens=2500,
        )
        answer = response.choices[0].message.content
        if not answer:
            response = await client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "system", "content": SYSTEM_PROMPT + " Պատասխանիր միայն հայերեն տառերով։"}, {"role": "user", "content": question}],
                max_tokens=2500,
            )
            answer = response.choices[0].message.content
        bad_words = ("կորիզ", "շարժումայն", "standby", "միացրեք կամ ամբողջությամբ անջատեք")
        if answer and (sum(c.isascii() and c.isalpha() for c in answer) > 12 or any(word in answer.lower() for word in bad_words)):
            response = await client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "system", "content": SYSTEM_PROMPT + " Քո նախորդ պատասխանը սխալ էր։ Վերագրիր այն միայն հայերեն տառերով։"}, {"role": "user", "content": question}],
                max_tokens=2500,
            )
            answer = response.choices[0].message.content
        if not answer:
            answer = "Կարող ես սկսել սրանցից․ օգտագործիր էներգախնայող լամպեր, անջատիր սպասման ռեժիմում գտնվող սարքերը, փակիր պատուհանների ճեղքերը և ջեռուցումը պահիր չափավոր ջերմաստիճանում։"
        ai_history[user_id].extend([{"role": "user", "content": question}, {"role": "assistant", "content": answer}])
        await update.message.reply_text(answer, reply_markup=main_keyboard())
    except Exception:
        logger.exception("AI request failed")
        await update.message.reply_text(
            "Ամենաարագ խնայողության քայլերը՝ LED լամպեր օգտագործիր, չօգտագործվող սարքերը հանիր վարդակից, փակիր պատուհանների ճեղքերը և օդորակիչը պահիր մոտ 24–26°C-ում։ Եթե ուզում ես՝ գրիր տան սարքերի հզորությունն ու օգտագործման ժամերը, և կօգնեմ հաշվարկել։",
            reply_markup=main_keyboard(),
        )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if query.data == "home":
        await query.message.reply_text("Գլխավոր մենյու 🏠", reply_markup=main_keyboard())
        return
    if query.data.startswith("round:"):
        state = sessions.get(user_id)
        if not state:
            await query.message.reply_text("Սկսիր նոր փուլ գլխավոր մենյուից։", reply_markup=main_keyboard())
            return
        question, answers, correct = state["questions"][state["index"]]
        if int(query.data.split(":")[1]) == correct:
            state["score"] += 1
            result = "✅ Ճիշտ է։"
        else:
            result = f"❌ Ճիշտ պատասխանը՝ {answers[correct]}"
        state["index"] += 1
        if query.message.photo:
            await query.edit_message_caption(caption=result)
        else:
            await query.edit_message_text(result)
        await send_round_question(user_id, context)


async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    routes = {
        "⚡ Սկսել թեստ": lambda: start_round(update, context, "quiz"),
        "🎮 Խաղալ": lambda: start_round(update, context, "game"),
        "🔋 Համեմատել էներգիայի ծախսը": lambda: compare(update, context),
        "📚 Իմանալ ավելին": lambda: info(update, context),
        "🌱 Ստանալ էկո խորհուրդներ": lambda: tips(update, context),
        "🤖 ԱԲ օգնական": lambda: ai_mode(update, context),
        "❓ Օգնություն": lambda: help_cmd(update, context),
        "📊 Իմ արդյունքները": lambda: update.message.reply_text("📊 Այս փուլում արդյունքները պահվում են ընթացիկ սեսիայի համար։ Նորից անցիր թեստը՝ արդյունք ստանալու համար։", reply_markup=main_keyboard()),
    }
    handler = routes.get(update.message.text)
    if handler:
        await handler()
    else:
        await ask_ai(update, context)


def build_app():
    if not BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is missing")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))
    return app


if __name__ == "__main__":
    build_app().run_polling(allowed_updates=Update.ALL_TYPES)
