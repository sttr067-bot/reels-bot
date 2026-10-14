from flask import Flask, request
import requests

PAGE_ACCESS_TOKEN = "ใส่_PAGE_TOKEN_ของคุณ"
VERIFY_TOKEN = "ตั้งเองเช่น sumeth123"

app = Flask(__name__)

# 1. Facebook จะมาตรวจ webhook ครั้งแรก
@app.route('/webhook', methods=['GET'])
def verify():
    if request.args.get('hub.verify_token') == VERIFY_TOKEN:
        return request.args.get('hub.challenge')
    return "fail", 403

# 2. มีคนเม้น Reels -> Facebook ยิงมาทางนี้
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    for entry in data.get('entry', []):
        for change in entry.get('changes', []):
            if change.get('field') == 'feed':
                comment_id = change['value'].get('comment_id')
                message = change['value'].get('message', '')
                
                if comment_id and message:
                    # 3. ส่งให้ AI คิด
                    ai_reply = ask_ai(message)
                    # 4. ตอบกลับใต้เม้นนั้น
                    reply_comment(comment_id, ai_reply)
    return "ok", 200

def ask_ai(user_comment):
    # ตรงนี้เปลี่ยนเป็น AI ที่คุณใช้ได้
    # ตัวอย่าง Prompt ภาษาไทย
    prompt = f"""
    คุณคือแอดมินเพจ ตอบคอมเมนต์ใน Reels
    กฎ: สุภาพ ตอบตรงคำถาม สั้น ไม่เกิน 2 บรรทัด ถ้าไม่รู้ให้บอกให้ทักแชท
    คอมเมนต์ลูกค้า: "{user_comment}"
    ตอบ:
    """
    # เรียก AI ของคุณที่นี่ แล้ว return ข้อความ
    # ตัวอย่าง return ง่ายๆก่อน
    return f"ขอบคุณที่คอมเมนต์นะคะ '{user_comment}' แอดมินขอทักไปให้รายละเอียดเพิ่มเติมน้าา"

def reply_comment(comment_id, text):
    url = f"https://graph.facebook.com/v21.0/{comment_id}/comments"
    requests.post(url, data={
        "message": text,
        "access_token": PAGE_ACCESS_TOKEN
    })

app.run(port=5000)
