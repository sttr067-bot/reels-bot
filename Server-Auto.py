from flask import Flask, request
import requests
import os
import random
import re

PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN", "")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "banban1234")

app = Flask(__name__)

# เก็บข้อมูลโพสต์ไว้ จะได้ไม่ต้องยิง API บ่อย
POST_CACHE = {}

SHOPEE_LINK_PATTERN = r'https?://s\.shopee\.co\.th/[^\s]+'

def get_post_info(post_id_full):
    """ดึงแคปชั่นและคอมเมนต์แรกของเจ้าของโพสต์"""
    if post_id_full in POST_CACHE:
        return POST_CACHE[post_id_full]

    try:
        # post_id_full จะเป็น PAGEID_POSTID ต้องใช้ทั้งก้อนยิง API
        # 1. ดึงแคปชั่น
        url_post = f"https://graph.facebook.com/v21.0/{post_id_full}"
        r1 = requests.get(url_post, params={"fields": "message", "access_token": PAGE_ACCESS_TOKEN}, timeout=10)
        caption = ""
        if r1.status_code == 200:
            caption = r1.json().get("message", "")
        
        # 2. ดึงคอมเมนต์ทั้งหมด หาคอมเมนต์แรกที่เป็นของเพจเองที่มีลิงก์
        url_comments = f"https://graph.facebook.com/v21.0/{post_id_full}/comments"
        r2 = requests.get(url_comments, params={"fields": "message,from", "access_token": PAGE_ACCESS_TOKEN, "limit": 50, "order": "chronological"}, timeout=10)
        first_comment_link = ""
        first_comment_text = ""
        
        if r2.status_code == 200:
            comments = r2.json().get("data", [])
            for c in comments:
                msg = c.get("message", "")
                # หาคอมเมนต์ที่มีลิงก์ Shopee
                if "shopee.co.th" in msg.lower() or "http" in msg.lower():
                    first_comment_link = msg
                    first_comment_text = msg
                    break
            # ถ้าไม่เจอลิงก์ เอาคอมเมนต์แรกของเพจเลย
            if not first_comment_link and comments:
                first_comment_link = comments[0].get("message", "")

        info = {"caption": caption, "first_comment": first_comment_text or first_comment_link}
        POST_CACHE[post_id_full] = info
        print(f"Fetched Post Info: {info}")
        return info
    except Exception as e:
        print(f"get_post_info error: {e}")
        return {"caption": "", "first_comment": ""}

def extract_link(text):
    """ดึงลิงก์ออกมาจากข้อความ"""
    match = re.search(SHOPEE_LINK_PATTERN, text)
    if match:
        return match.group(0)
    # หา http ทั่วไป
    match2 = re.search(r'https?://[^\s]+', text)
    if match2:
        return match2.group(0)
    return ""

@app.route('/webhook', methods=['GET'])
def verify():
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    if token == VERIFY_TOKEN:
        return challenge or request.args.get('hub.challenge')
    return "fail", 403

@app.route('/', methods=['GET'])
def home():
    return "Bot AUTO is running! อ่านแคปชั่น + คอมเมนต์แรกเอง", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json
        for entry in data.get('entry', []):
            for change in entry.get('changes', []):
                if change.get('field') == 'feed':
                    value = change.get('value', {})
                    comment_id = value.get('comment_id')
                    message = value.get('message', '')
                    post_id_full = value.get('post_id', '')
                    
                    # กันบอทตอบตัวเองและตอบคอมเมนต์แรกของเจ้าของ
                    if not comment_id or not message:
                        continue
                    # ถ้าเป็นการสร้างโพสต์ใหม่หรือคอมเมนต์ของเพจเอง ข้าม
                    if value.get('item') == 'status' or value.get('verb') == 'add' and 'comment_id' not in value:
                        continue
                    
                    # เช็คว่าคนเม้นเป็นเพจเองไหม
                    from_id = value.get('from', {}).get('id', '')
                    if from_id and post_id_full and from_id in post_id_full:
                        continue

                    print(f"New Comment: {comment_id} on Post: {post_id_full} Message: {message}")
                    reply = ask_ai_auto(message, post_id_full)
                    reply_comment(comment_id, reply)
    except Exception as e:
        print(f"webhook error: {e}")
    return "ok", 200

def ask_ai_auto(user_comment, post_id_full):
    text = user_comment.lower()
    keywords = ["สนใจ", "สน", "ราคา", "เท่าไหร่", "พิกัด", "ขอ", "ซื้อ", "อยากได้", "ที่ไหน", "ลิ้ง", "ลิงก์", "link", "price", "how"]
    is_sonj = any(k in text for k in keywords)

    if not is_sonj:
        replies_other = [
            "ขอบคุณสำหรับคอมเมนต์นะคะ 🙏 ฝากติดตามด้วยน้าา",
            "ขอบคุณมากๆเลยนะคะ ❤️",
            "ขอบคุณค่าา 🥰",
        ]
        return random.choice(replies_other)

    # ถ้าคนสนใจ -> ไปดึงข้อมูลโพสต์นั้น
    post_info = get_post_info(post_id_full)
    caption = post_info.get("caption", "")[:100] # ตัดให้สั้น
    first_comment = post_info.get("first_comment", "")
    
    link = extract_link(first_comment)
    if not link:
        # ถ้าหาลิงก์ในคอมเมนต์แรกไม่เจอ หาในแคปชั่น
        link = extract_link(caption)
    
    # ถ้ายังไม่มีลิงก์เลย ใช้ลิงก์ระแนงเป็น fallback
    if not link:
        link = "https://s.shopee.co.th/9KilDEXtbt"

    # สร้างคำตอบสุ่ม แต่ใช้ข้อมูลจริงจากโพสต์
    # ดึงราคา/ชื่อจากคอมเมนต์แรก เช่น "พิกัด 18 บาทค่ะ"
    price_info = first_comment if first_comment else "พิกัดตามนี้เลยค่ะ"
    
    templates = [
        f"ขอบคุณที่สนใจค่ะ 🙏 {price_info} 👉 {link}",
        f"รับทราบค่ะ ❤️ {price_info} ลิงก์นี้เลยนะคะ {link}",
        f"ได้เลยค่ะ {first_comment} กดดูในนี้ได้เลยค่ะ {link}",
        f"ขอบคุณที่สนใจนะคะ 🥰 {price_info} {link} กดเลือกขนาด/สีในลิงก์ได้เลยค่ะ",
        f"ยินดีค่ะ 🙏 {price_info} ตามนี้เลยค่ะ {link}",
        f"ส่งพิกัดให้นะคะ 👉 {price_info} {link}",
    ]
    
    # ถ้าคอมเมนต์แรกยาวเกินไป ให้สั้นลง
    reply = random.choice(templates)
    if len(reply) > 300:
        reply = f"ขอบคุณที่สนใจค่ะ 🙏 พิกัดตามนี้เลยค่ะ {link} {first_comment[:50]}"
    
    return reply

def reply_comment(comment_id, text):
    url = f"https://graph.facebook.com/v21.0/{comment_id}/comments"
    r = requests.post(url, data={"message": text, "access_token": PAGE_ACCESS_TOKEN})
    print(f"Reply Result: {r.text}")
    return r.json()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
