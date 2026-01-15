# app.py - Railway용 까르띠에 재고 확인 웹 버전
from flask import Flask, render_template, request, jsonify
import threading
import time
import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
import re

app = Flask(__name__)

# 전역 변수
monitoring_active = False
monitoring_thread = None
url_list = []
url_data = {}  # {url: {'title': '', 'memo': '', 'last_status': '', 'last_check': ''}}
check_count = 0
logs = []
check_interval = 60  # 초
DATA_FILE = "data.json"

# 텔레그램 설정
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "7581538889:AAHqA9oitAEARZj9v8HaTvh9xKRRiJNY67U")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "-1002901540928")

# HTTP 세션 설정
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Cache-Control': 'no-cache',
})

def add_log(msg):
    """로그 추가"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = {"time": timestamp, "msg": msg}
    logs.append(log_entry)
    if len(logs) > 200:
        logs.pop(0)
    print(f"[{timestamp}] {msg}")

def save_data():
    """데이터 저장"""
    data = {
        "url_list": url_list,
        "url_data": url_data,
        "check_interval": check_interval
    }
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        add_log(f"데이터 저장 실패: {e}")

def load_data():
    """데이터 로드"""
    global url_list, url_data, check_interval
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                url_list = data.get("url_list", [])
                url_data = data.get("url_data", {})
                check_interval = data.get("check_interval", 60)
                add_log(f"데이터 로드 완료: {len(url_list)}개 URL")
    except Exception as e:
        add_log(f"데이터 로드 실패: {e}")

def send_telegram(message):
    """텔레그램 메시지 전송"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        response = requests.post(url, data=data, timeout=10)
        if response.status_code == 200:
            add_log("텔레그램 전송 성공")
        else:
            add_log(f"텔레그램 전송 실패: {response.status_code}")
    except Exception as e:
        add_log(f"텔레그램 오류: {e}")

def check_stock(url):
    """재고 확인 (requests + BeautifulSoup)"""
    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
        
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')
        
        # 제목 추출
        title = ""
        title_elem = soup.select_one('h1.pdp-header__title')
        if title_elem:
            title = title_elem.get_text(strip=True)
        
        # 재고 상태 판별
        # 방법 1: 버튼 텍스트 확인
        if '상담원 연결' in html or 'contact-customer-care' in html:
            return "품절", title
        
        # 방법 2: 쇼핑백 추가 버튼 확인
        add_btn = soup.select_one('button.add-to-cart[data-product-component="add-button"]')
        if add_btn and '쇼핑백에 추가하기' in add_btn.get_text():
            return "재고있음", title
        
        # 방법 3: HTML 텍스트로 확인
        if '쇼핑백에 추가하기' in html:
            return "재고있음", title
        
        return "확인불가", title
        
    except requests.exceptions.Timeout:
        add_log(f"타임아웃: {url[:40]}")
        return "오류", ""
    except requests.exceptions.RequestException as e:
        add_log(f"요청 오류: {e}")
        return "오류", ""
    except Exception as e:
        add_log(f"재고 확인 오류: {e}")
        return "오류", ""

def monitoring_loop():
    """모니터링 루프"""
    global monitoring_active, check_count
    
    add_log("모니터링 시작")
    
    while monitoring_active:
        if not url_list:
            time.sleep(5)
            continue
            
        for url in url_list[:]:  # 복사본으로 순회
            if not monitoring_active:
                break
                
            add_log(f"확인 중: {url[:50]}...")
            status, title = check_stock(url)
            check_count += 1
            
            # URL 데이터 업데이트
            if url not in url_data:
                url_data[url] = {'title': '', 'memo': '', 'last_status': '', 'last_check': ''}
            
            if title and not url_data[url]['title']:
                url_data[url]['title'] = title
            
            prev_status = url_data[url]['last_status']
            url_data[url]['last_status'] = status
            url_data[url]['last_check'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 상태 변화 알림
            display_name = url_data[url]['title'] or url_data[url]['memo'] or url[:40]
            
            if status == "재고있음":
                if prev_status != "재고있음":
                    msg = f"🔔 <b>재고 입고!</b>\n\n{display_name}\n\n{url}"
                    send_telegram(msg)
                    add_log(f"✅ 재고 입고: {display_name}")
                else:
                    add_log(f"✅ 재고 유지: {display_name}")
            elif status == "품절":
                add_log(f"❌ 품절: {display_name}")
            else:
                add_log(f"⚠️ {status}: {display_name}")
            
            save_data()
            time.sleep(2)  # 요청 간 딜레이
        
        # 다음 체크까지 대기
        if monitoring_active:
            add_log(f"다음 체크까지 {check_interval}초 대기...")
            for _ in range(check_interval):
                if not monitoring_active:
                    break
                time.sleep(1)
    
    add_log("모니터링 종료")

# Flask 라우트
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    """현재 상태 조회"""
    return jsonify({
        "monitoring": monitoring_active,
        "check_count": check_count,
        "url_count": len(url_list),
        "check_interval": check_interval,
        "urls": [
            {
                "url": url,
                "title": url_data.get(url, {}).get('title', ''),
                "memo": url_data.get(url, {}).get('memo', ''),
                "status": url_data.get(url, {}).get('last_status', '미확인'),
                "last_check": url_data.get(url, {}).get('last_check', '')
            }
            for url in url_list
        ],
        "logs": logs[-50:]  # 최근 50개 로그
    })

@app.route('/api/add_url', methods=['POST'])
def add_url():
    """URL 추가"""
    data = request.json
    url = data.get('url', '').strip()
    memo = data.get('memo', '').strip()
    
    if not url:
        return jsonify({"success": False, "error": "URL을 입력하세요"})
    
    if url in url_list:
        return jsonify({"success": False, "error": "이미 등록된 URL입니다"})
    
    url_list.append(url)
    url_data[url] = {
        'title': '',
        'memo': memo,
        'last_status': '미확인',
        'last_check': ''
    }
    save_data()
    add_log(f"URL 추가: {memo or url[:40]}")
    
    return jsonify({"success": True})

@app.route('/api/remove_url', methods=['POST'])
def remove_url():
    """URL 삭제"""
    data = request.json
    url = data.get('url', '')
    
    if url in url_list:
        url_list.remove(url)
        if url in url_data:
            del url_data[url]
        save_data()
        add_log(f"URL 삭제: {url[:40]}")
        return jsonify({"success": True})
    
    return jsonify({"success": False, "error": "URL을 찾을 수 없습니다"})

@app.route('/api/update_memo', methods=['POST'])
def update_memo():
    """메모 수정"""
    data = request.json
    url = data.get('url', '')
    memo = data.get('memo', '')
    
    if url in url_data:
        url_data[url]['memo'] = memo
        save_data()
        return jsonify({"success": True})
    
    return jsonify({"success": False, "error": "URL을 찾을 수 없습니다"})

@app.route('/api/set_interval', methods=['POST'])
def set_interval():
    """체크 간격 설정"""
    global check_interval
    data = request.json
    interval = data.get('interval', 60)
    
    if interval < 30:
        return jsonify({"success": False, "error": "최소 30초 이상이어야 합니다"})
    
    check_interval = interval
    save_data()
    add_log(f"체크 간격 변경: {interval}초")
    
    return jsonify({"success": True})

@app.route('/api/start', methods=['POST'])
def start_monitoring():
    """모니터링 시작"""
    global monitoring_active, monitoring_thread
    
    if monitoring_active:
        return jsonify({"success": False, "error": "이미 모니터링 중입니다"})
    
    if not url_list:
        return jsonify({"success": False, "error": "등록된 URL이 없습니다"})
    
    monitoring_active = True
    monitoring_thread = threading.Thread(target=monitoring_loop, daemon=True)
    monitoring_thread.start()
    
    return jsonify({"success": True})

@app.route('/api/stop', methods=['POST'])
def stop_monitoring():
    """모니터링 중지"""
    global monitoring_active
    
    monitoring_active = False
    add_log("모니터링 중지 요청")
    
    return jsonify({"success": True})

@app.route('/api/check_now', methods=['POST'])
def check_now():
    """즉시 확인"""
    data = request.json
    url = data.get('url', '')
    
    if not url:
        return jsonify({"success": False, "error": "URL이 없습니다"})
    
    add_log(f"수동 확인: {url[:40]}")
    status, title = check_stock(url)
    
    if url in url_data:
        url_data[url]['last_status'] = status
        url_data[url]['last_check'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if title:
            url_data[url]['title'] = title
        save_data()
    
    return jsonify({
        "success": True,
        "status": status,
        "title": title
    })

@app.route('/api/test_telegram', methods=['POST'])
def test_telegram():
    """텔레그램 테스트"""
    send_telegram("🔔 테스트 메시지입니다!")
    return jsonify({"success": True})

# 앱 시작 시 데이터 로드
load_data()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
