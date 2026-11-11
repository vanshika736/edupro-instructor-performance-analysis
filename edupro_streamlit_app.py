from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

# ------------------------------------------------------------
# EduPro: Instructor Performance & Course Quality Dashboard
# ------------------------------------------------------------

st.set_page_config(
    page_title="EduPro Analytics",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = Path(__file__).resolve().parent
DATA_CANDIDATES = [
    BASE_DIR / "EduPro_Platform_Sanitized.xlsx",
    BASE_DIR / "EduPro Online Platform.xlsx",
    BASE_DIR / "EduPro_Instructor_Performance_Dashboard.xlsx",
]

REQUIRED_SHEETS = ["Users", "Teachers", "Courses", "Transactions"]

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.6rem; padding-bottom: 2rem;}
    [data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e8edf4;
        padding: 14px 16px;
        border-radius: 12px;
    }
    h1, h2, h3 {letter-spacing: -0.35px;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🎓 EduPro | Instructor Performance & Course Quality")
st.caption(
    "Instructor performance · Course quality · Learner activity "
    "| Interactive internship analytics project"
)


def find_default_workbook():
    """Find a workbook beside this script using known deployment filenames."""
    for candidate in DATA_CANDIDATES:
        if candidate.is_file():
            return candidate
    return None


@st.cache_data(show_spinner="Loading EduPro workbook...")
def load_data_from_bytes(file_bytes):
    """Load and validate the four source sheets from an Excel workbook."""
    from io import BytesIO

    excel = pd.ExcelFile(BytesIO(file_bytes))
    missing_sheets = [sheet for sheet in REQUIRED_SHEETS if sheet not in excel.sheet_names]
    if missing_sheets:
        raise ValueError(
            "The workbook is missing required sheet(s): "
            + ", ".join(missing_sheets)
        )

    users = pd.read_excel(excel, sheet_name="Users")
    teachers = pd.read_excel(excel, sheet_name="Teachers")
    courses = pd.read_excel(excel, sheet_name="Courses")
    transactions = pd.read_excel(excel, sheet_name="Transactions")

    required_columns = {
        "Users": (users, ["UserID"]),
        "Teachers": (
            teachers,
            ["TeacherID", "TeacherName", "Expertise", "Gender",
             "Age", "YearsOfExperience", "TeacherRating"],
        ),
        "Courses": (
            courses,
            ["CourseID", "CourseName", "CourseCategory",
             "CourseLevel", "CourseRating"],
        ),
        "Transactions": (
            transactions,
            ["TransactionID", "UserID", "CourseID", "TeacherID", "Amount"],
        ),
    }

    for sheet_name, (frame, columns) in required_columns.items():
        missing_columns = [column for column in columns if column not in frame.columns]
        if missing_columns:
            raise ValueError(
                f"Sheet '{sheet_name}' is missing column(s): "
                + ", ".join(missing_columns)
            )

    # Convert numeric fields safely; malformed values become missing.
    for column in ["Age", "YearsOfExperience", "TeacherRating"]:
        teachers[column] = pd.to_numeric(teachers[column], errors="coerce")

    courses["CourseRating"] = pd.to_numeric(
        courses["CourseRating"], errors="coerce"
    )
    transactions["Amount"] = pd.to_numeric(
        transactions["Amount"], errors="coerce"
    ).fillna(0)

    teacher_activity = (
        transactions.groupby("TeacherID", dropna=False)
        .agg(
            Transactions=("TransactionID", "count"),
            TransactionAmount=("Amount", "sum"),
            UniqueCourses=("CourseID", "nunique"),
        )
        .reset_index()
    )
    teacher_view = teachers.merge(
        teacher_activity, on="TeacherID", how="left"
    )
    for column in ["Transactions", "TransactionAmount", "UniqueCourses"]:
        teacher_view[column] = teacher_view[column].fillna(0)

    course_activity = (
        transactions.groupby("CourseID", dropna=False)
        .agg(
            Transactions=("TransactionID", "count"),
            TransactionAmount=("Amount", "sum"),
            InstructorCount=("TeacherID", "nunique"),
        )
        .reset_index()
    )
    course_view = courses.merge(
        course_activity, on="CourseID", how="left"
    )
    for column in ["Transactions", "TransactionAmount", "InstructorCount"]:
        course_view[column] = course_view[column].fillna(0)

    return users, teachers, courses, transactions, teacher_view, course_view


# Dataset source: upload override, otherwise locate workbook beside this script.
st.sidebar.header("Dataset")
uploaded_file = st.sidebar.file_uploader(
    "Upload an Excel workbook (.xlsx)", type=["xlsx"]
)

if uploaded_file is not None:
    workbook_bytes = uploaded_file.getvalue()
    workbook_name = uploaded_file.name
else:
    default_workbook = find_default_workbook()
    if default_workbook is None:
        st.error(
            "EduPro workbook not found. Upload the sanitized workbook using the "
            "sidebar, or place EduPro_Platform_Sanitized.xlsx in the same "
            "GitHub folder as edupro_streamlit_app.py."
        )
        st.stop()
    workbook_bytes = default_workbook.read_bytes()
    workbook_name = default_workbook.name

try:
    (
        users,
        teachers,
        courses,
        transactions,
        teacher_view,
        course_view,
    ) = load_data_from_bytes(workbook_bytes)
except Exception as error:
    st.error(f"Unable to load '{workbook_name}': {error}")
    st.info(
        "Check that the workbook is a valid .xlsx file and contains the "
        "Users, Teachers, Courses and Transactions sheets."
    )
    st.stop()

st.sidebar.success(f"Loaded: {workbook_name}")
st.sidebar.header("Dashboard filters")

# Filter controls
expertise_options = sorted(
    teacher_view["Expertise"].dropna().astype(str).unique().tolist()
)
gender_options = sorted(
    teacher_view["Gender"].dropna().astype(str).unique().tolist()
)
category_options = sorted(
    course_view["CourseCategory"].dropna().astype(str).unique().tolist()
)
level_options = sorted(
    course_view["CourseLevel"].dropna().astype(str).unique().tolist()
)

selected_expertise = st.sidebar.multiselect(
    "Instructor expertise", expertise_options, default=expertise_options
)
selected_gender = st.sidebar.multiselect(
    "Instructor gender", gender_options, default=gender_options
)
selected_category = st.sidebar.multiselect(
    "Course category", category_options, default=category_options
)
selected_level = st.sidebar.multiselect(
    "Course level", level_options, default=level_options
)

rating_values = teacher_view["TeacherRating"].dropna()
if not rating_values.empty:
    rating_min = float(rating_values.min())
    rating_max = float(rating_values.max())
    if rating_min < rating_max:
        rating_range = st.sidebar.slider(
            "Teacher rating range",
            min_value=rating_min,
            max_value=rating_max,
            value=(rating_min, rating_max),
        )
    else:
        rating_range = (rating_min, rating_max)
else:
    rating_range = (0.0, 5.0)

filtered_teachers = teacher_view[
    teacher_view["Expertise"].astype(str).isin(selected_expertise)
    & teacher_view["Gender"].astype(str).isin(selected_gender)
    & teacher_view["TeacherRating"].between(*rating_range)
].copy()

filtered_courses = course_view[
    course_view["CourseCategory"].astype(str).isin(selected_category)
    & course_view["CourseLevel"].astype(str).isin(selected_level)
].copy()

if st.sidebar.button("Reset filters", use_container_width=True):
    st.rerun()

# KPI summary
st.subheader("Platform overview")
kpi_cols = st.columns(6)
teacher_avg = filtered_teachers["TeacherRating"].mean()
course_avg = filtered_courses["CourseRating"].mean()

kpis = [
    ("Instructors", f"{len(filtered_teachers):,}"),
    ("Courses", f"{len(filtered_courses):,}"),
    ("Transactions", f"{len(transactions):,}"),
    ("Avg. teacher rating", f"{teacher_avg:.2f}/5" if pd.notna(teacher_avg) else "N/A"),
    ("Avg. course rating", f"{course_avg:.2f}/5" if pd.notna(course_avg) else "N/A"),
    ("Transaction amount", f"{transactions['Amount'].sum():,.0f}"),
]
for column, (label, value) in zip(kpi_cols, kpis):
    column.metric(label, value)

overview_tab, leaderboard_tab, demographics_tab, course_tab, expertise_tab, quality_tab = st.tabs(
    [
        "Overview",
        "Instructor leaderboard",
        "Experience & demographics",
        "Course quality",
        "Expertise analysis",
        "Data quality & methodology",
    ]
)

with overview_tab:
    left, right = st.columns(2)
    with left:
        if not filtered_teachers.empty:
            chart = px.histogram(
                filtered_teachers,
                x="TeacherRating",
                nbins=10,
                title="Teacher rating distribution",
                color_discrete_sequence=["#6558d3"],
            )
            chart.update_layout(bargap=0.15)
            st.plotly_chart(chart, use_container_width=True)
        else:
            st.info("No instructors match the selected filters.")

    with right:
        if not filtered_courses.empty:
            chart = px.histogram(
                filtered_courses,
                x="CourseRating",
                nbins=10,
                title="Course rating distribution",
                color_discrete_sequence=["#249b91"],
            )
            chart.update_layout(bargap=0.15)
            st.plotly_chart(chart, use_container_width=True)
        else:
            st.info("No courses match the selected filters.")

    if not filtered_teachers.empty:
        scatter_data = filtered_teachers.dropna(
            subset=["YearsOfExperience", "TeacherRating"]
        )
        if not scatter_data.empty:
            chart = px.scatter(
                scatter_data,
                x="YearsOfExperience",
                y="TeacherRating",
                color="Expertise",
                hover_name="TeacherName",
                title="Instructor experience vs. teacher rating",
            )
            st.plotly_chart(chart, use_container_width=True)

with leaderboard_tab:
    if not filtered_teachers.empty:
        ranking_metric = st.selectbox(
            "Rank instructors by",
            ["TeacherRating", "Transactions", "YearsOfExperience"],
        )
        leaderboard = filtered_teachers.sort_values(
            ranking_metric, ascending=False
        )
        display_columns = [
            column for column in [
                "TeacherName", "Expertise", "Gender", "Age",
                "YearsOfExperience", "TeacherRating", "Transactions",
            ]
            if column in leaderboard.columns
        ]
        st.dataframe(
            leaderboard[display_columns],
            use_container_width=True,
            hide_index=True,
        )
        top_instructors = leaderboard.head(15)
        chart = px.bar(
            top_instructors,
            x=ranking_metric,
            y="TeacherName",
            color="Expertise",
            orientation="h",
            title=f"Top 15 instructors by {ranking_metric}",
        )
        chart.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(chart, use_container_width=True)
        st.download_button(
            "Download filtered instructor leaderboard (CSV)",
            leaderboard.to_csv(index=False).encode("utf-8"),
            file_name="EduPro_Instructor_Leaderboard.csv",
            mime="text/csv",
        )
    else:
        st.info("No instructors match the selected filters.")

with demographics_tab:
    left, right = st.columns(2)
    with left:
        if not filtered_teachers.empty:
            chart = px.box(
                filtered_teachers.dropna(subset=["Gender", "TeacherRating"]),
                x="Gender",
                y="TeacherRating",
                title="Teacher rating by gender",
            )
            st.plotly_chart(chart, use_container_width=True)
    with right:
        scatter_data = filtered_teachers.dropna(subset=["Age", "TeacherRating"])
        if not scatter_data.empty:
            chart = px.scatter(
                scatter_data,
                x="Age",
                y="TeacherRating",
                color="Expertise",
                hover_name="TeacherName",
                title="Age vs. teacher rating",
            )
            st.plotly_chart(chart, use_container_width=True)

    correlation_data = filtered_teachers[
        ["YearsOfExperience", "TeacherRating"]
    ].dropna()
    correlation = (
        correlation_data["YearsOfExperience"].corr(correlation_data["TeacherRating"])
        if len(correlation_data) > 1
        else np.nan
    )
    st.metric(
        "Experience–rating Pearson correlation",
        f"{correlation:.3f}" if pd.notna(correlation) else "N/A",
    )
    st.caption(
        "Correlation is descriptive and does not establish that experience causes "
        "higher teacher ratings."
    )

with course_tab:
    if not filtered_courses.empty:
        heatmap_data = filtered_courses.pivot_table(
            index="CourseCategory",
            columns="CourseLevel",
            values="CourseRating",
            aggfunc="mean",
        )
        if not heatmap_data.empty:
            chart = px.imshow(
                heatmap_data,
                text_auto=".2f",
                aspect="auto",
                color_continuous_scale="Tealgrn",
                title="Average course rating by category and level",
            )
            st.plotly_chart(chart, use_container_width=True)

        course_sort_column = (
            "CourseRating" if "CourseRating" in filtered_courses.columns else "CourseName"
        )
        st.dataframe(
            filtered_courses.sort_values(course_sort_column, ascending=False),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No courses match the selected filters.")

with expertise_tab:
    if not filtered_teachers.empty:
        expertise_summary = (
            filtered_teachers.groupby("Expertise", as_index=False)
            .agg(
                Instructors=("TeacherID", "nunique"),
                AverageTeacherRating=("TeacherRating", "mean"),
                AverageExperience=("YearsOfExperience", "mean"),
                TransactionCount=("Transactions", "sum"),
            )
            .sort_values("AverageTeacherRating", ascending=False)
        )
        chart = px.bar(
            expertise_summary,
            x="Expertise",
            y="AverageTeacherRating",
            color="Instructors",
            title="Average teacher rating by expertise",
        )
        st.plotly_chart(chart, use_container_width=True)
        st.dataframe(
            expertise_summary,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No instructor data is available for the selected filters.")

with quality_tab:
    source_tables = {
        "Users": users,
        "Teachers": teachers,
        "Courses": courses,
        "Transactions": transactions,
    }
    missing_cells = sum(
        int(frame.isna().sum().sum()) for frame in source_tables.values()
    )
    duplicate_transactions = int(
        transactions["TransactionID"].duplicated().sum()
    )
    unmatched_users = int(
        (~transactions["UserID"].isin(users["UserID"])).sum()
    )
    unmatched_courses = int(
        (~transactions["CourseID"].isin(courses["CourseID"])).sum()
    )
    unmatched_teachers = int(
        (~transactions["TeacherID"].isin(teachers["TeacherID"])).sum()
    )
    unmatched_total = (
        unmatched_users + unmatched_courses + unmatched_teachers
    )

    quality_cols = st.columns(3)
    quality_cols[0].metric("Missing cells", f"{missing_cells:,}")
    quality_cols[1].metric(
        "Duplicate transaction IDs", f"{duplicate_transactions:,}"
    )
    quality_cols[2].metric(
        "Unmatched transaction references", f"{unmatched_total:,}"
    )

    st.subheader("Source table sizes")
    st.dataframe(
        pd.DataFrame(
            {
                "Table": list(source_tables.keys()),
                "Rows": [len(frame) for frame in source_tables.values()],
                "Columns": [len(frame.columns) for frame in source_tables.values()],
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.warning(
        "Interpretation limitations: transaction rows are activity/transaction "
        "proxies and do not confirm completed course enrollments. Course ratings "
        "are course-level, not instructor-level; do not treat them as individual "
        "teacher ratings. Correlations are descriptive, not causal."
    )

st.divider()
st.subheader("Project resources")

resource_files = [
    ("Research report", "EduPro_Complete_Research_Report.pdf"),
    ("Executive summary", "EduPro_Executive_Summary.pdf"),
    ("Stakeholder presentation", "EduPro_Stakeholder_Presentation.pptx"),
    ("Excel dashboard", "EduPro_Instructor_Performance_Dashboard.xlsx"),
]
resource_cols = st.columns(2)
for index, (label, filename) in enumerate(resource_files):
    resource_path = BASE_DIR / filename
    if resource_path.is_file():
        with resource_cols[index % 2]:
            st.download_button(
                f"Download {label}",
                data=resource_path.read_bytes(),
                file_name=filename,
                use_container_width=True,
            )

st.caption(
    "Built with Streamlit, Python, Pandas, NumPy and Plotly | EduPro Analytics"
)
