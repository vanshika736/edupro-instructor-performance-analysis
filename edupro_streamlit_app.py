import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="EduPro Analytics",page_icon="🎓",layout="wide")
st.title("🎓 EduPro | Instructor Performance & Course Quality")
st.caption("Teaching effectiveness • Course quality • Expertise • Enrollment performance")
uploaded=st.sidebar.file_uploader("Upload EduPro Excel workbook",type=["xlsx"])
@st.cache_data
def load(f):
    x=pd.ExcelFile(f)
    u=pd.read_excel(x,"Users"); t=pd.read_excel(x,"Teachers"); c=pd.read_excel(x,"Courses"); tx=pd.read_excel(x,"Transactions")
    ta=t.merge(tx.groupby("TeacherID").agg(Transactions=("TransactionID","count"),Revenue=("Amount","sum"),UniqueCourses=("CourseID","nunique")).reset_index(),on="TeacherID",how="left").fillna(0)
    ca=c.merge(tx.groupby("CourseID").agg(Transactions=("TransactionID","count"),Revenue=("Amount","sum"),InstructorCount=("TeacherID","nunique")).reset_index(),on="CourseID",how="left").fillna(0)
    return u,t,c,tx,ta,ca
try:
    data=load(uploaded if uploaded else "EduPro Online Platform.xlsx")
except Exception:
    st.warning("Upload EduPro Online Platform.xlsx using the sidebar.")
    st.stop()
u,t,c,tx,ta,ca=data
st.sidebar.header("Filters")
ex=st.sidebar.multiselect("Expertise",["All"]+sorted(ta.Expertise.dropna().astype(str).unique()),default=["All"])
cat=st.sidebar.multiselect("Course category",["All"]+sorted(ca.CourseCategory.dropna().astype(str).unique()),default=["All"])
lev=st.sidebar.multiselect("Course level",["All"]+sorted(ca.CourseLevel.dropna().astype(str).unique()),default=["All"])
rr=st.sidebar.slider("Teacher rating range",float(ta.TeacherRating.min()),float(ta.TeacherRating.max()),(float(ta.TeacherRating.min()),float(ta.TeacherRating.max())))
tv=ta.copy() if not ex or "All" in ex else ta[ta.Expertise.astype(str).isin(ex)]
tv=tv[tv.TeacherRating.between(*rr)]
cv=ca.copy() if not cat or "All" in cat else ca[ca.CourseCategory.astype(str).isin(cat)]
cv=cv.copy() if not lev or "All" in lev else cv[cv.CourseLevel.astype(str).isin(lev)]
k=st.columns(5)
for col,label,value in zip(k,["Instructors","Courses","Transactions","Avg teacher rating","Avg course rating"],[len(tv),len(cv),len(tx),tv.TeacherRating.mean(),cv.CourseRating.mean()]):
    col.metric(label,f"{value:,.2f}" if "rating" in label else f"{value:,.0f}")
tabs=st.tabs(["Overview","Instructor leaderboard","Experience & demographics","Course quality","Expertise","Data quality"])
with tabs[0]:
    a,b=st.columns(2)
    a.plotly_chart(px.histogram(tv,x="TeacherRating",title="Teacher rating distribution"),use_container_width=True)
    b.plotly_chart(px.histogram(cv,x="CourseRating",title="Course rating distribution"),use_container_width=True)
    st.plotly_chart(px.scatter(tv,x="YearsOfExperience",y="TeacherRating",color="Expertise",hover_name="TeacherName",trendline="ols",title="Experience vs teacher rating"),use_container_width=True)
with tabs[1]:
    order=st.selectbox("Rank by",["TeacherRating","Transactions","YearsOfExperience"])
    st.dataframe(tv.sort_values(order,ascending=False),use_container_width=True)
    st.plotly_chart(px.bar(tv.nlargest(15,order),x=order,y="TeacherName",color="Expertise",orientation="h"),use_container_width=True)
with tabs[2]:
    a,b=st.columns(2)
    a.plotly_chart(px.box(tv,x="Gender",y="TeacherRating",title="Rating by gender"),use_container_width=True)
    b.plotly_chart(px.scatter(tv,x="Age",y="TeacherRating",color="Expertise",hover_name="TeacherName",title="Age vs rating"),use_container_width=True)
with tabs[3]:
    heat=cv.pivot_table(index="CourseCategory",columns="CourseLevel",values="CourseRating",aggfunc="mean")
    if not heat.empty: st.plotly_chart(px.imshow(heat,text_auto=".2f",aspect="auto",color_continuous_scale="Greens",title="Course quality heatmap"),use_container_width=True)
    st.dataframe(cv.sort_values("CourseRating",ascending=False),use_container_width=True)
with tabs[4]:
    exv=tv.groupby("Expertise",as_index=False).agg(Instructors=("TeacherID","nunique"),AvgRating=("TeacherRating","mean"),AvgExperience=("YearsOfExperience","mean"),Transactions=("Transactions","sum"))
    st.plotly_chart(px.bar(exv,x="Expertise",y="AvgRating",color="Instructors",title="Expertise-wise teacher ratings"),use_container_width=True)
    st.dataframe(exv,use_container_width=True)
with tabs[5]:
    st.write(f"Users: {len(u):,} | Teachers: {len(t):,} | Courses: {len(c):,} | Transactions: {len(tx):,}")
    st.info("Transactions are used as enrollment proxies. CourseRating belongs to the course record, not an individual instructor. Correlation does not prove causation.")
