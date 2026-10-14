from flask import Flask, request
import requests
import os

# ดึงจาก Environment Variable ที่คุณตั้งใน Render
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN", "ใส่_PAGE_TOKEN_ของคุณ")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "banban1234")

app = Flask(__name__)

# 1. Facebook จะมาตรวจ webhook ครั้งแรก
@app.route('/webhook', methods=['GET'])
def verify():
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    # รองรับแบบเก่าด้วย
    if token == VERIFY_TOKEN:
        return challenge or request.args.get('hub.challenge')
    return "fail", 403

@app.route('/', methods=['GET'])
def home():
    return "Bot is running! ใช้งานได้แล้วครับ", 200

# 2. มีคนเม้น Reels -> Facebook ยิงมาทางนี้
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json
        print(f"Webhook received: {data}")
        for entry in data.get('entry', []):
            for change in entry.get('changes', []):
                if change.get('field') == 'feed':
                    value = change.get('value', {})
                    comment_id = value.get('comment_id')
                    message = value.get('message', '')
                    post_id = value.get('post_id', '')
                    print(f"Comment: {comment_id} Message: {message}")
                    
                    if comment_id and message:
                        # กันบอทตอบตัวเอง
                        if value.get('from', {}).get('id') == value.get('post_id'):
                            continue
                        ai_reply = ask_ai(message)
                        reply_comment(comment_id, ai_reply)
    except Exception as e:
        print(f"Error: {e}")
    return "ok", 200

def ask_ai(user_comment):
    prompt = f"""
    คุณคือแอดมินเพจ ตอบคอมเมนต์ใน Reels
    กฎ: สุภาพ ตอบตรงคำถาม สั้น ไม่เกิน 2 บรรทัด ถ้าไม่รู้ให้บอกให้ทักแชท
    คอมเมนต์ลูกค้า: "{user_comment}"
    ตอบ:
    """
    # ตอนนี้ตอบแบบง่ายๆก่อน เดี๋ยวค่อยต่อ AI จริง
    return f"ขอบคุณที่คอมเมนต์นะคะ '{user_comment}' แอดมินขอทักไปให้รายละเอียดเพิ่มเติมน้าา"

def reply_comment(comment_id, text):
    url = f"https://graph.facebook.com/v21.0/{comment_id}/comments"
    r = requests.post(url, data={
        "message": text,
        "access_token": PAGE_ACCESS_TOKEN
    })
    print(f"Reply result: {r.text}")
    return r.json()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
