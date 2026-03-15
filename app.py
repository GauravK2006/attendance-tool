import streamlit as st
import pdfplumber
import pandas as pd

st.set_page_config(
    page_title="KPMSOL Attendance Calculator",
    page_icon="📊",
    layout="wide"
)

# ---------- INSTRUCTIONS ----------
if "show_instructions" not in st.session_state:
    st.session_state.show_instructions = True

if st.session_state.show_instructions:
    st.info("""
**How to use**

1. Download your **Detailed Attendance Report** from the SAP Portal.  
2. Upload it here.  
3. Check your **attendance percentage**.  
4. Cross check your **cumulative attendance** with the minimum required lectures listed below according to the credit structure.
""")

    if st.button("Close"):
        st.session_state.show_instructions = False


# ---------- HEADER ----------
st.title("KPMSOL Attendance Calculator")
st.markdown("---")
st.caption("Created by Gaurav Khopkar")

st.markdown(
    '### Upload your Detailed Attendance Report from <a href="https://sdc-sppap1.svkm.ac.in:50001/irj/portal" target="_blank">SAP</a> here',
    unsafe_allow_html=True
)

st.caption("From: 2ⁿᵈ Jan 2026 To: Yesterday")

uploaded_file = st.file_uploader("Upload File", type="pdf")


# ---------- PROCESS PDF ----------
if uploaded_file:

    with st.spinner("Processing attendance report..."):

        rows = []

        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                table = page.extract_table()

                if table:
                    for row in table[1:]:
                        rows.append(row)

        df = pd.DataFrame(rows)

        df = df[[1,2,5]]
        df.columns = ["Subject","Date","Attendance"]
        df = df.dropna()

        # -------- SUBJECT LIST --------
        subjects = df["Subject"].unique()

        result = pd.DataFrame({
            "Subject": subjects
        })

        # lectures conducted
        conducted = df.groupby("Subject").size()

        # lectures attended
        attended = df[df["Attendance"]=="P"].groupby("Subject").size()

        # missed dates
        missed_dates = (
            df[df["Attendance"]=="A"]
            .groupby("Subject")["Date"]
            .apply(lambda x: ", ".join(x.astype(str)))
        )

        result["Total Lectures Conducted"] = result["Subject"].map(conducted).fillna(0)
        result["Total Lectures Attended"] = result["Subject"].map(attended).fillna(0)
        result["Dates Missed"] = result["Subject"].map(missed_dates).fillna("")

        # ---------- GROUP T1 & U1 ----------
        result["Base Subject"] = result["Subject"].str.replace(r" (T1|U1).*","",regex=True)
        result["Type"] = result["Subject"].str.extract(r"(T1|U1)")

        result = result.sort_values(by=["Base Subject","Type"])

        # cumulative calculations
        combined_conducted = result.groupby("Base Subject")["Total Lectures Conducted"].transform("sum")
        combined_attended = result.groupby("Base Subject")["Total Lectures Attended"].transform("sum")

        result["Cumulative Attendance"] = combined_attended
        result["Attendance Percentage"] = (combined_attended / combined_conducted * 100).round(2)

        # cleanup
        result.drop(columns=["Base Subject","Type"], inplace=True)

        # serial numbers
        result.insert(0, "Sr. No.", range(1, len(result)+1))

        result = result[
            [
                "Sr. No.",
                "Subject",
                "Total Lectures Conducted",
                "Total Lectures Attended",
                "Cumulative Attendance",
                "Attendance Percentage",
                "Dates Missed"
            ]
        ]

    st.dataframe(
        result,
        use_container_width=True,
        height=650,
        hide_index=True
    )


# ---------- CREDIT STRUCTURE ----------
st.markdown("### Credits")

credit_data = {
    "Credits": ["4 Credit", "3 Credit", "2 Credit", "Non-Credit"],
    "Total Lectures": [
        "60 Lectures + 15 Tutorials",
        "45 Lectures + 15 Tutorials",
        "30 Lectures",
        "30 Lectures"
    ],
    "Lectures + Tutorials Required": ["53", "42", "21", "21"]
}

credit_df = pd.DataFrame(credit_data)

st.table(credit_df)
import requests

# ---------- PAGE VIEW COUNTER ----------
try:
    response = requests.get("https://api.countapi.xyz/hit/kpmsol-attendance-tool/views")
    views = response.json()["value"]
    st.markdown("---")
    st.caption(f"👀 Page Views: {views}")
except:
    pass
