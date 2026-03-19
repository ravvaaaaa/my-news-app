import streamlit as st
import feedparser
import requests
from urllib.parse import quote
from datetime import datetime
from difflib import SequenceMatcher
from googlenewsdecoder import gnewsdecoder

st.set_page_config(page_title="부동산 뉴스 스크랩", layout="wide")

def is_similar(a, b, threshold=0.6):
    return SequenceMatcher(None, a, b).ratio() > threshold

def decode_google_news_url(url):
    try:
        result = gnewsdecoder(url)
        if isinstance(result, dict) and result.get("decoded_url"):
            return result["decoded_url"], None
        if isinstance(result, str) and result.startswith("http"):
            return result, None
        return None, "디코딩 실패"
    except Exception as e:
        return None, f"디코딩 예외 | {e}"

def block_preview(url):
    """카톡 미리보기 차단용 투명 문자 삽입"""
    if not url: return url
    if url.startswith("https://"):
        return url.replace("https://", "https://\u200C", 1)
    if url.startswith("http://"):
        return url.replace("http://", "http://\u200C", 1)
    return url

if "selected_articles" not in st.session_state:
    st.session_state["selected_articles"] = {}
if "news_pool" not in st.session_state:
    st.session_state["news_pool"] = []

CATEGORIES = {
    "🔍 직접 키워드 검색": "CUSTOM",
    "■보증&공공기관&정부대책 관련": "(HUG OR 국토부 OR 양도세 OR HF OR 서울보증 OR 보증보험 OR 한국부동산원 OR SGI OR 주택금융공사 OR LH) (대책 OR 규제 OR 발표)",
    "■은행&보험사": "(은행 OR 시중은행 OR 주담대 OR 전세대출 OR 권리보험 OR 권리조사 OR 권원 OR 권원보험 OR 보험)",
    "■대출 및 금리 관련": "(대출 OR 금리 OR HF) (전세자금대출 OR 주택 OR 아파트)",
    "■부동산시장관련": "(아파트 OR 빌라 OR 오피스텔 OR 매입임대 OR 임대차 OR 임대주택 OR 임대차조사 OR 임차 OR 임차권 OR 전세 OR 전세권 OR 전입 OR 전입세대 OR 점유) (시황 OR 가격 OR 전세가)",
    "■부동산 AI 및 프롭테크": "(부동산 OR 보증금 OR 프롭테크) (AI OR 인공지능 OR 빅데이터 OR 리파인 OR 집파인)",
    "■전세 사기 및 리스크 관리": "전세사기 OR 전세조사 OR 임대차신고",
    "■부동산관련 스터디자료": "(부동산 OR 임대차 OR 등기 OR 등기변동 OR 등기소 OR 설정등기 OR 세입자 OR 소유권 OR 신탁 OR 채권양도 OR 질권설정) (판례 OR 법률)"
}

st.sidebar.header("⚙️ 뉴스 검색 설정")
selected_cat = st.sidebar.selectbox("카테고리 선택", list(CATEGORIES.keys()))
search_query = st.sidebar.text_input("검색어", "") if selected_cat == "🔍 직접 키워드 검색" else CATEGORIES[selected_cat]
search_count = st.sidebar.slider("수집 개수", 10, 100, 30)
search_days = st.sidebar.select_slider("검색 기간", options=["1d", "2d", "3d", "7d"], value="1d")

if st.sidebar.button("🚀 뉴스 후보 가져오기", type="primary", use_container_width=True):
    with st.spinner("뉴스 불러오는 중..."):
        url = f"https://news.google.com/rss/search?q={quote(search_query)}+when:{search_days}&hl=ko&gl=KR&ceid=KR:ko"
        feed = feedparser.parse(url)
        unique_articles = []
        for entry in feed.entries:
            if len(unique_articles) >= search_count: break
            title = entry.title.rsplit(" - ", 1)[0]
            if not any(is_similar(title, ex.title.rsplit(" - ", 1)[0]) for ex in unique_articles):
                unique_articles.append(entry)
        st.session_state["news_pool"] = unique_articles
        st.rerun()

st.title(f"📑 {selected_cat}")

for i, entry in enumerate(st.session_state["news_pool"]):
    parts = entry.title.rsplit(" - ", 1)
    title, source = parts[0], parts[1] if len(parts) > 1 else "뉴스"
    key = f"{title}_{i}"
    is_checked = key in st.session_state["selected_articles"]

    col1, col2 = st.columns([0.05, 0.95])
    with col1:
        checked = st.checkbox(" ", key=f"cb_{key}", value=is_checked)
        if checked and not is_checked:
            with st.spinner("링크 추출 중..."):
                final_url, error = decode_google_news_url(entry.link)
                if final_url:
                    st.session_state["selected_articles"][key] = {
                        "title": title, "cat": selected_cat,
                        "url": block_preview(final_url)
                    }
                    st.rerun()
        elif (not checked) and is_checked:
            del st.session_state["selected_articles"][key]
            st.rerun()
            
    with col2:
        # [수정] 스트림릿 화면에서 제목 클릭 시 기사 원문으로 바로 접속 가능하게 하이퍼링크 추가
        article_info = st.session_state["selected_articles"].get(key)
        # 이미 추출된 원본 주소가 있다면 특수문자를 제거한 주소로, 없다면 구글 링크로 연결
        target_url = article_info["url"].replace("\u200C", "") if article_info else entry.link
        st.markdown(f"**[{source}] [{title}]({target_url})**")
        
    st.divider()

st.markdown("---")
st.header("📋 카톡 공유 텍스트")

if st.session_state["selected_articles"]:
    today_str = datetime.now().strftime('%Y년 %m월 %d일')
    # 1. 헤더 부분을 먼저 생성합니다.
    final_text = f"■ {today_str} 부동산 뉴스 브리핑\n관련기사들은 전날 기준 기사로 정리되었습니다.\n\n"

    # 2. 카테고리별 내용을 생성하여 final_text에 덧붙입니다.
    for cat in CATEGORIES.keys():
        items = [v for v in st.session_state["selected_articles"].values() if v["cat"] == cat]
        if items:
            final_text += f"<{cat}>\n"
            for idx, item in enumerate(items, 1):
                # 제목에서 신문사 제거 + 다음 줄에 원본 주소 (미리보기 차단 적용)
                final_text += f"{idx}. {item['title']}\n{item['url']}\n\n"
            final_text += "\n"
    
    # 3. 최종 완성된 final_text를 출력합니다.
    st.text_area("복사용", final_text, height=400)
else:
    st.info("기사를 선택하면 리스트가 생성됩니다.")