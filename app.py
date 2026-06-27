import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium

st.set_page_config(page_title="따릉이 분석 대시보드", layout="wide")
st.title("🚲 따릉이 대여소 분석 대시보드")
st.caption("서울시 공공자전거 데이터로 보는 우리 동네")

@st.cache_data
def load_main():
    df = pd.read_csv("data.csv", encoding="utf-8-sig")
    df = df.dropna(subset=["위도", "경도"])
    df = df[(df["위도"] != 0) & (df["경도"] != 0)].copy()
    df["순유출"] = df["대여건수"] - df["반납건수"]
    return df

@st.cache_data
def load_od(name):
    return pd.read_csv(name, encoding="utf-8-sig")

df = load_main()

# ── 사이드바
st.sidebar.header("⚙️ 분석 설정")
analysis = st.sidebar.radio(
    "분석 유형",
    ["이용량 (어디서 많이 타나)",
     "불균형 (어디가 부족/과잉)",
     "이동흐름 OD (어디로 가나)"]
)

# ── 핵심 지표
c1, c2, c3, c4 = st.columns(4)
c1.metric("전체 대여소", f"{len(df):,}개")
c2.metric("총 대여건수", f"{df['대여건수'].sum():,.0f}")
c3.metric("총 반납건수", f"{df['반납건수'].sum():,.0f}")
c4.metric("자전거 부족 지점", f"{(df['순유출']>0).sum():,}개")

center = [df["위도"].mean(), df["경도"].mean()]
m = folium.Map(location=center, zoom_start=11, tiles="CartoDB positron")

# ── 1) 이용량
if analysis.startswith("이용량"):
    top_n = st.sidebar.slider("표시할 대여소 수", 50, len(df), 300)
    view = df.nlargest(top_n, "총이용건수")
    heat = [[r["위도"], r["경도"], r["총이용건수"]] for _, r in view.iterrows()]
    HeatMap(heat, radius=18, blur=14, min_opacity=0.3,
            gradient={0.2:"blue",0.5:"cyan",0.7:"yellow",1.0:"red"}).add_to(m)
    st.subheader("📍 이용량 히트맵 — 제일 많이 빌려가는 동네는?")
    st_folium(m, width=900, height=500)
    st.dataframe(view[["자치구","대여소명","대여건수","반납건수","총이용건수"]]
                 .reset_index(drop=True), use_container_width=True)

# ── 2) 불균형
elif analysis.startswith("불균형"):
    top_n = st.sidebar.slider("표시할 대여소 수", 50, len(df), 300)
    view = df.nlargest(top_n, "총이용건수")
    max_imb = df["순유출"].abs().max()
    for _, r in view.iterrows():
        color = "crimson" if r["순유출"] > 0 else "steelblue"
        radius = 3 + (abs(r["순유출"]) / max_imb) * 10
        folium.CircleMarker([r["위도"], r["경도"]], radius=radius,
            color=color, fill=True, fill_color=color, fill_opacity=0.5,
            popup=f"순유출: {r['순유출']:.0f}").add_to(m)
    st.subheader("📍 불균형 지도 — 🔴부족(대여>반납) / 🔵과잉(반납>대여)")
    st_folium(m, width=900, height=500)
    st.dataframe(view[["자치구","대여소명","대여건수","반납건수","순유출"]]
                 .reset_index(drop=True), use_container_width=True)

# ── 3) 이동흐름 OD
else:
    when = st.sidebar.radio("시간대", ["출근 (7~9시)", "퇴근 (17~19시)"])
    od = load_od("od_am.csv") if when.startswith("출근") else load_od("od_pm.csv")
    od = od.dropna(subset=["출발위도","도착위도"])
    max_trip = od["이동횟수"].max() if len(od) else 1
    for _, r in od.iterrows():
        w = 1 + (r["이동횟수"]/max_trip)*8
        folium.PolyLine([[r["출발위도"],r["출발경도"]],[r["도착위도"],r["도착경도"]]],
            color="crimson", weight=w, opacity=0.6,
            popup=f"{r['출발명']} → {r['도착명']}<br>{int(r['이동횟수'])}회").add_to(m)
        folium.CircleMarker([r["출발위도"],r["출발경도"]], radius=4,
            color="steelblue", fill=True, fill_opacity=0.8).add_to(m)
        folium.CircleMarker([r["도착위도"],r["도착경도"]], radius=4,
            color="crimson", fill=True, fill_opacity=0.8).add_to(m)
    st.subheader(f"📍 {when} 핵심 OD 구간 — 굵을수록 통행↑ (자전거도로 우선검토)")
    st_folium(m, width=900, height=500)
    od_show = load_od("od_am.csv" if when.startswith("출근") else "od_pm.csv")
    od_show = od_show[["출발명","도착명","이동횟수"]].reset_index(drop=True)
    od_show.index = od_show.index + 1
    st.dataframe(od_show, use_container_width=True)

st.caption("데이터: 서울시 공공자전거 따릉이 | 데이터로 읽는 우리 동네")
