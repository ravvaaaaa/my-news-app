import streamlit as st
import feedparser
import requests
from urllib.parse import quote
from datetime import datetime
from difflib import SequenceMatcher

# 1. 화면 설정
st.set_page_config(page_title="부동산 뉴스 스크랩", layout="wide")

# URL 단축 함수 (타임아웃 강화 및 에러 처리)
def get_safe_shortest_url(long_url):
    try:
        # 응답 시간을 3초로 제한하여 프로그램이 멈추는 리스크 방지
        api_url = f"https://is.gd/create.php?format=simple&url={long_url}"
        response = requests.get(api_url, timeout=3)
        if response.status_code == 200:
            return response.text.replace("is.gd/", "is\u200B.gd/")
    except:
        pass
    return long_url

def is_similar(a, b, threshold=0.6):
    return SequenceMatcher(None, a, b).ratio() > threshold

# 2. 세션 상태 초기화
if 'selected_articles' not in st.session_state:
    st.session_state['selected_articles'] = {}
if 'news_pool' not in st.session_state:
    st.session_state['news_pool'] = []

CATEGORIES = {
    "🔍 직접 키워드 검색": "CUSTOM",
    "■보증&공공기관&정부대책 관련": "(HUG OR 국토부 OR 양도세 OR HF OR 서울보증 OR 보증보험 OR 한국부동산원 OR SGI OR 주택금융공사 OR LH) (대책 OR 규제 OR 발표)",
    "■은행&보험사": "(은행 OR 시중은행 OR 주담대 OR 전세대출 OR 권리보험 OR 권리조사 OR 권원 OR 권원보험 OR 보험)",
    "■대출 및 금리 관련": "(대출 OR 금리 OR HF) (전세자금대출 OR 주택 OR 아파트)",
    "■부동산시장관련": "(아파트 OR 빌라 OR 오피스텔 OR 매입임대 OR 임대차 OR 임대주택 OR 임대차조사 OR 임차 OR 임차권 OR 전세 OR 전세권 OR 전입 OR 전입세대 OR 점유) (시황 OR 가격 OR 전세가)",
    "■부동산 AI 및 프롭테크": "(부동산 OR 보증금 OR 프롭테크) (AI OR 인공지능 OR 빅데이터 OR 리파인 OR 집파인)", 
    "■전세 사기 및 리스크 관리": "(전세사기 OR 전세조사 OR 임대차신고)",
    "■부동산관련 스터디자료": "(부동산 OR 임대차 OR 등기 OR 등기변동 OR 등기소 OR 설정등기 OR 세입자 OR 소유권 OR 신탁 OR 채권양도 OR 질권설정) (판례 OR 법률)"
}

# 3. 사이드바 UI
st.sidebar.header("⚙️ 뉴스 검색 설정")
selected_cat = st.sidebar.selectbox("카테고리 선택", list(CATEGORIES.keys()))

if selected_cat == "🔍 직접 키워드 검색":
    search_query = st.sidebar.text_input("검색어 입력", placeholder="예: GTX 노선")
else:
    search_query = CATEGORIES[selected_cat]

search_count = st.sidebar.slider("수집 개수", 10, 100, 30)
search_days = st.sidebar.select_slider("검색 기간", options=["1d", "2d", "3d", "7d"], value="1d")

if st.sidebar.button("🚀 뉴스 후보 가져오기", type="primary", use_container_width=True):
    if not search_query:
        st.sidebar.error("검색어를 입력해주세요!")
    else:
        with st.spinner('뉴스를 불러오는 중...'):
            url = f"https://news.google.com/rss/search?q={quote(search_query)}+when:{search_days}&hl=ko&gl=KR&ceid=KR:ko"
            feed = feedparser.parse(url)
            unique_articles = []
            for entry in feed.entries:
                if len(unique_articles) >= search_count: break
                new_title = entry.title.rsplit(' - ', 1)[0]
                if not any(is_similar(new_title, ex.title.rsplit(' - ', 1)[0]) for ex in unique_articles):
                    unique_articles.append(entry)
            st.session_state['news_pool'] = unique_articles
            st.rerun()

# 4. 메인 화면
st.title(f"📑 {selected_cat}")
for entry in st.session_state['news_pool']:
    parts = entry.title.rsplit(' - ', 1)
    title, source, link = parts[0], parts[1] if len(parts) > 1 else "뉴스", entry.link
    is_checked = link in st.session_state['selected_articles']
    
    col1, col2 = st.columns([0.05, 0.95])
    with col1:
        if st.checkbox(" ", key=f"cb_{link}", value=is_checked):
            if not is_checked:
                with st.spinner('처리 중...'):
                    st.session_state['selected_articles'][link] = {
                        "title": title, "link": get_safe_shortest_url(link), 
                        "cat": selected_cat, "source": source
                    }
                st.rerun()
        elif is_checked:
            del st.session_state['selected_articles'][link]
            st.rerun()
    with col2:
        st.markdown(f"**[{source}] [{title}]({link})**")
    st.divider()

# 5. 최종 결과창
st.markdown("---")
st.header("📋 최종 공유 텍스트")
if st.session_state['selected_articles']:
    today = datetime.now().strftime('%Y년 %m월 %d일')
    final_text = f"■ {today} 부동산 뉴스 브리핑\n\n"
    for cat in CATEGORIES.keys():
        articles = [a for a in st.session_state['selected_articles'].values() if a['cat'] == cat]
        if articles:
            final_text += f"<{cat}>\n"
            for i, art in enumerate(articles):
                final_text += f"{i+1}. {art['title']} ({art['source']})\n{art['link']}\n\n"
            final_text += "\n"
    st.text_area("카톡 복용", final_text, height=400)
    if st.button("🗑 초기화"):
        st.session_state['selected_articles'] = {}
        st.rerun()