import streamlit as st
import feedparser
import requests
from urllib.parse import quote
from datetime import datetime, timedelta

# 1. 화면 설정
st.set_page_config(page_title="부동산 뉴스 스크랩", layout="wide")

# URL 단축 및 미리보기 방지 함수 (is.gd 사용)
def get_safe_shortest_url(long_url):
    try:
        api_url = f"https://is.gd/create.php?format=simple&url={long_url}"
        response = requests.get(api_url, timeout=5)
        if response.status_code == 200:
            short_url = response.text
            # 주소 중간에 제로 너비 공백(\u200B) 삽입하여 카톡 미리보기 차단
            return short_url.replace("is.gd/", "is\u200B.gd/")
        return long_url
    except:
        return long_url

# 2. 세션 상태 초기화
if 'selected_articles' not in st.session_state:
    st.session_state['selected_articles'] = {}
if 'news_pool' not in st.session_state:
    st.session_state['news_pool'] = []

CATEGORIES = {
    "🔍 직접 키워드 검색": "CUSTOM",
    "■보증&공공기관&정부대책 관련": "(HUG OR 국토부 OR 양도세) (대책 OR 규제 OR 발표)",
    "■은행&보험사": "(은행 OR 시중은행 OR 주담대 OR 전세대출)",
    "■대출 및 금리 관련": "(대출 OR 금리 OR HF) (전세자금대출 OR 주택 OR 아파트)",
    "■부동산시장관련": "(アパート OR 빌라 OR 오피스텔) (시황 OR 가격 OR 전세가)",
    "■부동산 AI 및 프롭테크": "(부동산 OR 프롭테크) (AI OR 인공지능 OR 빅데이터)", 
    "■전세 사기 및 리스크 관리": "전세사기 OR 전세조사 OR 임대차신고",
    "■부동산관련 스터디자료": "(부동산 OR 임대차) (판례 OR 법률)"
}

# 3. 사이드바 UI
st.sidebar.header("⚙️ 뉴스 검색 설정")
selected_cat = st.sidebar.selectbox("카테고리 선택", list(CATEGORIES.keys()))

search_query = ""
if selected_cat == "🔍 직접 키워드 검색":
    search_query = st.sidebar.text_input("검색어 입력", placeholder="예: GTX 노선")
else:
    search_query = CATEGORIES[selected_cat]

search_count = st.sidebar.slider("수집 개수", 10, 100, 30)
search_days = st.sidebar.select_slider("검색 기간 (과거)", options=["1d", "2d", "3d", "7d"], value="1d")

st.sidebar.markdown("---")
if st.sidebar.button("🚀 뉴스 후보 가져오기", type="primary", use_container_width=True):
    if not search_query:
        st.sidebar.error("검색어를 입력해주세요!")
    else:
        with st.spinner('뉴스를 불러오는 중...'):
            encoded_query = quote(search_query)
            url = f"https://news.google.com/rss/search?q={encoded_query}+when:{search_days}&hl=ko&gl=KR&ceid=KR:ko"
            feed = feedparser.parse(url)
            st.session_state['news_pool'] = feed.entries[:search_count]
            st.rerun()

# 4. 메인 화면 - 기사 선택 영역
st.title(f"📑 {selected_cat}")
if st.session_state['news_pool']:
    for entry in st.session_state['news_pool']:
        # 언론사 분리 및 제목 정리
        title_parts = entry.title.rsplit(' - ', 1)
        clean_title = title_parts[0]
        source = title_parts[1] if len(title_parts) > 1 else "뉴스"
        link = entry.link
        
        is_checked = link in st.session_state['selected_articles']
        
        col1, col2 = st.columns([0.05, 0.95])
        with col1:
            if st.checkbox(" ", key=f"cb_{link}", value=is_checked):
                if not is_checked:
                    with st.spinner('URL 처리 중...'):
                        safe_url = get_safe_shortest_url(link)
                        st.session_state['selected_articles'][link] = {
                            "title": clean_title, 
                            "link": safe_url, 
                            "cat": selected_cat,
                            "source": source
                        }
                    st.rerun()
            elif is_checked:
                del st.session_state['selected_articles'][link]
                st.rerun()
        with col2:
            # [복구] 제목을 클릭하면 기사 원문으로 이동할 수 있도록 링크 연결
            st.markdown(f"**[{source}] [{clean_title}]({link})**")
        st.divider()

# 5. 하단 결과창
st.markdown("---")
st.header("📋 최종 공유 텍스트")

if st.session_state['selected_articles']:
    today_str = datetime.now().strftime('%Y년 %m월 %d일')
    final_text = f"■ {today_str}\n 관련기사들은 전날 기준 기사로 정리되었습니다.\n\n"
    
    for cat in CATEGORIES.keys():
        articles = [a for a in st.session_state['selected_articles'].values() if a['cat'] == cat]
        if articles:
            final_text += f"<{cat}>\n"
            for i, article in enumerate(articles):
                # 가독성을 위해 제목 아래에 URL 배치 (미리보기 차단 적용)
                final_text += f"{i+1}. {article['title']} ({article['source']})\n{article['link']}\n\n"

    st.text_area("카톡 복사용 결과", final_text, height=450)
    
    if st.button("🗑 선택 초기화", type="secondary"):
        st.session_state['selected_articles'] = {}
        st.rerun()