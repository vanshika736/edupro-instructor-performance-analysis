import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="EduPro Analytics Dashboard",
    page_icon="🎓",
    layout="wide"
)

# ----------------- DATA LOADING -----------------
@st.cache_data
def load_data():
    file_path = "EduPro Online Platform.xlsx"
    try:
        teachers = pd.read_excel(file_path, sheet_name="Teachers")
        courses = pd.read_excel(file_path, sheet_name="Courses")
        transactions = pd.read_excel(file_path, sheet_name="Transactions")
    except Exception:
        # Fallback dummy data generation if file is missing in repo during initial build
        teachers = pd.DataFrame({
            "TeacherID": [f"TC{i:05d}" for i in range(1, 61)],
            "TeacherName": [f"Instructor {i}" for i in range(1, 61)],
            "Age": np.random.randint(27, 52, 60),
            "Gender": np.random.choice(["Male", "Female"], 60),
            "Expertise": np.random.choice(["Cybersecurity", "Data Science", "Machine Learning", "Digital Marketing", "Programming"], 60),
            "YearsOfExperience": np.random.randint(1, 25, 60),
            "TeacherRating": np.round(np.random.uniform(1.5, 5.0, 60), 2)
        })
        courses = pd.DataFrame({
            "CourseID": [f"CR{i:05d}" for i in range(1, 61)],
            "CourseName": [f"Course {i}" for i in range(1, 61)],
            "CourseCategory": np.random.choice(["Programming", "Data Science", "Marketing", "Business"], 60),
            "CourseLevel": np.random.choice(["Beginner", "Intermediate", "Advanced"], 60),
            "CourseRating": np.round(np.random.uniform(2.0, 5.0, 60), 2),
            "CoursePrice": np.random.choice([0.0, 49.99, 99.99, 199.99], 60)
        })
        transactions = pd.DataFrame({
            "TransactionID": [f"TT{i:05d}" for i in range(1, 501)],
            "TeacherID": np.random.choice(teachers["TeacherID"], 501),
            "CourseID": np.random.choice(courses["CourseID"], 501),
            "Amount": np.random.choice([0.0, 49.99, 99.99], 501)
        })

    # Enrollments calculation per teacher
    enrollments = transactions.groupby("TeacherID").size().reset_index(name="EnrollmentCount")
    teachers = teachers.merge(enrollments, on="TeacherID", how="left").fillna({"EnrollmentCount": 0})
    return teachers, courses, transactions

teachers_df, courses_df, transactions_df = load_data()

# ----------------- SIDEBAR FILTERS -----------------
st.sidebar.title("🔍 Navigation & Filters")

selected_expertise = st.sidebar.multiselect(
    "Select Instructor Expertise:",
    options=teachers_df["Expertise"].unique(),
    default=teachers_df["Expertise"].unique()
)

rating_range = st.sidebar.slider(
    "Instructor Rating Range:",
    min_value=1.0,
    max_value=5.0,
    value=(1.0, 5.0),
    step=0.1
)

min_exp = st.sidebar.number_input(
    "Minimum Years of Experience:",
    min_value=0,
    max_value=int(teachers_df["YearsOfExperience"].max()),
    value=0
)

# Apply filters
filtered_teachers = teachers_df[
    (teachers_df["Expertise"].isin(selected_expertise)) &
    (teachers_df["TeacherRating"] >= rating_range[0]) &
    (teachers_df["TeacherRating"] <= rating_range[1]) &
    (teachers_df["YearsOfExperience"] >= min_exp)
]

# ----------------- HEADER & KPIS -----------------
st.title("🎓 EduPro: Instructor Performance & Course Quality Dashboard")
st.markdown("Comprehensive evaluation framework analyzing teaching tenure, course design, and learner satisfaction.")
st.divider()

col1, col2, col3, col4 = st.columns(4)
avg_teacher_rating = filtered_teachers["TeacherRating"].mean() if not filtered_teachers.empty else 0
avg_course_rating = courses_df["CourseRating"].mean()
total_instructors = len(filtered_teachers)
total_enrollments = filtered_teachers["EnrollmentCount"].sum()

col1.metric("Avg Teacher Rating", f"{avg_teacher_rating:.2f} / 5.0")
col2.metric("Avg Course Rating", f"{avg_course_rating:.2f} / 5.0")
col3.metric("Filtered Instructors", total_instructors)
col4.metric("Total Enrollments", f"{int(total_enrollments):,}")

st.write("")

# ----------------- TABS SECTION -----------------
tab1, tab2, tab3 = st.tabs(["📊 Performance & Experience", "📚 Course Quality Heatmaps", "🏆 Instructor Leaderboard"])

with tab1:
    st.subheader("Teaching Tenure vs. Instructor Evaluation")
    c1, c2 = st.columns(2)
    
    with c1:
        fig_scatter = px.scatter(
            filtered_teachers,
            x="YearsOfExperience",
            y="TeacherRating",
            color="Expertise",
            size="EnrollmentCount",
            hover_name="TeacherName",
            title="Experience vs. Rating (Size = Enrollments)",
            labels={"YearsOfExperience": "Years of Experience", "TeacherRating": "Teacher Rating"},
            template="plotly_white"
        )
        st.plotly_chart(fig_scatter, use_container_width=True)
        
    with c2:
        fig_hist = px.histogram(
            filtered_teachers,
            x="TeacherRating",
            nbins=12,
            marginal="box",
            title="Distribution of Instructor Ratings",
            labels={"TeacherRating": "Teacher Rating"},
            color_discrete_sequence=["#1f77b4"],
            template="plotly_white"
        )
        st.plotly_chart(fig_hist, use_container_width=True)

with tab2:
    st.subheader("Course Category & Quality Breakdown")
    cat_summary = courses_df.groupby("CourseCategory").agg(
        AvgRating=("CourseRating", "mean"),
        TotalCourses=("CourseID", "count"),
        AvgPrice=("CoursePrice", "mean")
    ).reset_index().sort_values(by="AvgRating", ascending=False)
    
    c3, c4 = st.columns(2)
    with c3:
        fig_bar = px.bar(
            cat_summary,
            x="AvgRating",
            y="CourseCategory",
            orientation="h",
            color="AvgRating",
            color_continuous_scale="Viridis",
            title="Average Course Rating by Domain",
            labels={"AvgRating": "Average Rating", "CourseCategory": "Category"},
            template="plotly_white"
        )
        st.plotly_chart(fig_bar, use_container_width=True)
        
    with c4:
        fig_sunburst = px.sunburst(
            courses_df,
            path=["CourseCategory", "CourseLevel"],
            values="CourseRating",
            title="Course Rating Distribution Across Levels",
            color="CourseRating",
            color_continuous_scale="RdBu",
            template="plotly_white"
        )
        st.plotly_chart(fig_sunburst, use_container_width=True)

with tab3:
    st.subheader("Top-Performing Instructors")
    leaderboard = filtered_teachers[[
        "TeacherID", "TeacherName", "Expertise", "YearsOfExperience", "TeacherRating", "EnrollmentCount"
    ]].sort_values(by="TeacherRating", ascending=False)
    
    st.dataframe(
        leaderboard.style.format({
            "TeacherRating": "{:.2f}",
            "EnrollmentCount": "{:.0f}"
        }),
        use_container_width=True
    )
