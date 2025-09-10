import streamlit as st
import pandas as pd
import plotly.express as px
from fpdf import FPDF
import io
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date

# =========================================================
# GOOGLE SHEETS SETUP
# =========================================================
SHEET_ID = "1BoAArqUM8Acda63dNiCwKiqC7rH7rTq_0rWvo0aUlH4"
SHEET_NAME = "Sheet1"  # change if your sheet tab name differs

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"], 
    scopes=SCOPES
)

client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

# =========================================================
# EXPENSE TRACKER HELPERS
# =========================================================
EXPENSE_COLUMNS = ["Name", "Date", "Category", "Amount", "Notes"]
CATEGORY_OPTIONS = ["Food", "Gas", "Shopping", "House", "Entertainment", "Other"]

def load_expenses() -> pd.DataFrame:
    """Load all expenses from Google Sheets as a DataFrame with correct dtypes."""
    records = sheet.get_all_records()
    df = pd.DataFrame(records)
    if df.empty:
        df = pd.DataFrame(columns=EXPENSE_COLUMNS)

    # Ensure expected columns exist in the right order
    for col in EXPENSE_COLUMNS:
        if col not in df.columns:
            df[col] = pd.Series(dtype="object")
    df = df[EXPENSE_COLUMNS]

    # Coerce types
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0.0)
    # Make sure Date is ISO strings in the sheet; convert to datetime for charts/sorting
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.date

    return df

def append_expense(name: str, date_val: date, category: str, amount: float, notes: str):
    # Store date as ISO string to keep it consistent in Sheets
    sheet.append_row([name, str(date_val), category, float(amount), notes])

def update_expense(row_zero_based: int, name: str, date_val: date, category: str, amount: float, notes: str):
    # Header is row 1; data starts at row 2
    row_in_sheet = row_zero_based + 2
    sheet.update(f"A{row_in_sheet}:E{row_in_sheet}", [[name, str(date_val), category, float(amount), notes]])

def delete_expense(row_zero_based: int):
    # Header is row 1; data starts at row 2
    row_in_sheet = row_zero_based + 2
    sheet.delete_rows(row_in_sheet)

def build_row_labels(df: pd.DataFrame):
    labels = []
    for i, r in df.reset_index(drop=True).iterrows():
        d = r["Date"]
        d_str = d.isoformat() if isinstance(d, (datetime, date)) and pd.notna(d) else str(d)
        labels.append(f"{i+1}: {r['Name']} | {d_str} | ${float(r['Amount']):.2f} | {r['Category']} | {r['Notes']}")
    return labels

# =========================================================
# PDF EXPORT HELPER (unchanged from your original)
# =========================================================
def create_budget_pdf(name, income, expenses_dict, leftover, allocations, allocations_per_paycheck):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, txt=f"{name}'s Budget Summary", ln=True, align='C')
    pdf.ln(10)

    pdf.set_font("Arial", 'B', 12)
    pdf.cell(100, 10, "Category", 1)
    pdf.cell(50, 10, "Amount ($)", 1)
    pdf.ln()

    pdf.set_font("Arial", '', 12)
    for k, v in expenses_dict.items():
        pdf.cell(100, 10, k, 1)
        pdf.cell(50, 10, f"${v:.2f}", 1)
        pdf.ln()

    pdf.cell(100, 10, "Total Expenses", 1)
    pdf.cell(50, 10, f"${sum(expenses_dict.values()):.2f}", 1)
    pdf.ln()

    pdf.cell(100, 10, "Leftover After Expenses", 1)
    pdf.cell(50, 10, f"${leftover:.2f}", 1)
    pdf.ln(20)

    # Allocations
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="Allocations From Leftover", ln=True)
    pdf.set_font("Arial", '', 12)
    for k, v in allocations.items():
        pdf.cell(100, 10, k, 1)
        pdf.cell(50, 10, f"${v:.2f}", 1)
        pdf.ln()

    pdf.ln(10)

    # Allocations per paycheck
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="Allocations per Paycheck", ln=True)
    pdf.set_font("Arial", '', 12)
    for k, v in allocations_per_paycheck.items():
        pdf.cell(100, 10, k, 1)
        pdf.cell(50, 10, f"${v:.2f}", 1)
        pdf.ln()

    pdf_bytes = pdf.output(dest='S').encode('latin1')
    return io.BytesIO(pdf_bytes)

# =========================================================
# STREAMLIT APP
# =========================================================
st.set_page_config(page_title="Greg & Tyler's Budget", layout="wide")
st.title("🏠 Monthly Budget Planner — Greg & Tyler")

# -------------------------
# Tabs
# -------------------------
tab_expense, tab1, tab2, tab3 = st.tabs(["Expense Tracker", "Greg's Budget", "Tyler's Budget", "Combined View"])

# -------------------------
# Sidebar Inputs (Shared)
# -------------------------
with st.sidebar:
    st.header("📌 Shared Household Costs")
    rent = st.number_input("Monthly Rent ($)", min_value=0, value=1440)
    utilities = st.number_input("Monthly Utilities ($)", min_value=0, value=300)

# =========================================================
# EXPENSE TRACKER TAB (first tab)
# =========================================================
with tab_expense:
    st.header("💸 Expense Tracker")

    # ---- Add new expense (Sidebar form) ----
    st.sidebar.header("Add New Expense")
    with st.sidebar.form("expense_form", clear_on_submit=True):
        et_name = st.selectbox("Name", ['Greg', 'Tyler'])
        et_date = st.date_input("Date", datetime.today())
        et_category = st.selectbox("Category", CATEGORY_OPTIONS)
        et_amount = st.number_input("Amount", min_value=0.0, format="%.2f")
        et_notes = st.text_input("Notes (optional)")
        et_submitted = st.form_submit_button("Add Expense")
    if et_submitted:
        append_expense(et_name, et_date, et_category, et_amount, et_notes)
        st.sidebar.success("✅ Expense added!")
        st.experimental_rerun()

    # ---- Load & show ----
    df_exp = load_expenses()

    st.subheader("📊 Expense Dashboard")
    if df_exp.empty:
        st.info("No expenses yet. Add some from the sidebar.")
    else:
        # Show table (Name first)
        df_show = df_exp.copy()
        df_show = df_show[EXPENSE_COLUMNS]
        # Sort by date descending for display; NaT go last
        df_show = df_show.sort_values("Date", ascending=False)
        st.dataframe(df_show, use_container_width=True)

        # Total spent
        total_spent = float(df_exp["Amount"].sum())
        st.metric("Total Spent", f"${total_spent:,.2f}")

        # Spending by category
        category_sum = df_exp.groupby("Category", dropna=False)["Amount"].sum().reset_index()
        fig1 = px.pie(category_sum, values="Amount", names="Category", title="Expenses by Category")
        st.plotly_chart(fig1, use_container_width=True)

        # Spending over time (daily total)
        df_dates = df_exp.copy()
        df_dates["Date"] = pd.to_datetime(df_dates["Date"], errors="coerce")
        daily_sum = df_dates.dropna(subset=["Date"]).groupby(df_dates["Date"].dt.date)["Amount"].sum().reset_index()
        daily_sum.rename(columns={"Date": "Date", "Amount": "Amount"}, inplace=True)
        fig2 = px.line(daily_sum, x="Date", y="Amount", title="Expenses Over Time", markers=True)
        st.plotly_chart(fig2, use_container_width=True)

        # ---- Manage Expenses (Edit/Delete) ----
        st.subheader("📝 Manage Expenses")
        labels = build_row_labels(df_exp)
        if labels:
            # Select by label; map back to zero-based index
            selected_label = st.selectbox("Select a row to edit/delete", labels)
            selected_idx = labels.index(selected_label)  # zero-based idx into df_exp

            row = df_exp.iloc[selected_idx]
            # Edit form
            with st.form("edit_form"):
                new_name = st.selectbox("Name", ['Greg', 'Tyler'], index=['Greg', 'Tyler'].index(row["Name"]))
                # Ensure we pass a proper date to date_input
                existing_date = row["Date"]
                if pd.isna(existing_date):
                    existing_date = date.today()
                new_date = st.date_input("Date", existing_date)
                new_category = st.selectbox("Category", CATEGORY_OPTIONS, index=CATEGORY_OPTIONS.index(row["Category"]) if row["Category"] in CATEGORY_OPTIONS else 0)
                new_amount = st.number_input("Amount", min_value=0.0, value=float(row["Amount"]), format="%.2f")
                new_notes = st.text_input("Notes", value=row["Notes"] if pd.notna(row["Notes"]) else "")
                save_edit = st.form_submit_button("💾 Save Changes")
            if save_edit:
                update_expense(selected_idx, new_name, new_date, new_category, new_amount, new_notes)
                st.success("✅ Expense updated!")
                st.experimental_rerun()

            if st.button("❌ Delete This Expense"):
                delete_expense(selected_idx)
                st.success("🗑️ Expense deleted!")
                st.experimental_rerun()

# =========================================================
# GREG’S SECTION (tab1)
# =========================================================
with tab1:
    st.header("💼 Greg's Monthly Budget")

    col1, col2 = st.columns(2)
    with col1:
        greg_income = st.number_input("Greg's Monthly Income ($)", min_value=0, value=4788)
        greg_fixed = st.number_input("Greg's Fixed Costs", min_value=0, value=400)
    with col2:
        greg_subs = st.number_input("Greg's Subscriptions", min_value=0, value=80)

    # Pull Greg's tracked expenses from sheet
    df_exp_all = load_expenses()
    greg_tracked_expenses_total = float(df_exp_all[df_exp_all["Name"] == "Greg"]["Amount"].sum())

    # Expenses dict now includes tracked expenses
    greg_expenses = {
        'Rent (Shared)': rent / 2,
        'Utilities (Shared)': utilities / 2,
        'Fixed Costs': greg_fixed,
        'Subscriptions': greg_subs,
        'Tracked Expenses': greg_tracked_expenses_total
    }
    greg_total_expenses = sum(greg_expenses.values())

    # Leftover
    greg_leftover = greg_income - greg_total_expenses
    greg_leftover = max(greg_leftover, 0)
    greg_savings_rate = (greg_leftover / greg_income * 100) if greg_income else 0

    # Table — % of Income (format to two decimals)
    st.subheader("Breakdown — % of Income")
    greg_percent_df = pd.DataFrame.from_dict(greg_expenses, orient='index', columns=['Amount ($)'])
    greg_percent_df['% of Income'] = (greg_percent_df['Amount ($)'] / greg_income * 100).round(2) if greg_income else 0.0
    greg_percent_df.loc['Total Expenses'] = [greg_total_expenses, greg_percent_df['% of Income'].sum() if greg_income else greg_percent_df['% of Income'].sum()]
    leftover_percent = 100 - greg_percent_df['% of Income'].sum() if greg_income else 0.0
    greg_percent_df.loc['Net Leftover'] = [greg_leftover, leftover_percent]

    # Format columns (two decimals) without breaking strings
    greg_percent_df_display = greg_percent_df.copy()
    greg_percent_df_display['Amount ($)'] = greg_percent_df_display['Amount ($)'].map(lambda x: f"{float(x):.2f}")
    greg_percent_df_display['% of Income'] = greg_percent_df_display['% of Income'].map(lambda x: f"{float(x):.2f}")
    st.table(greg_percent_df_display)

    # Allocation (from leftover)
    st.subheader("Greg's Allocations (from leftover)")
    greg_allocations = {
        'Credit Card Payment (25%)': greg_leftover * 0.25,
        'Savings (40%)': greg_leftover * 0.40,
        'Spending Money (20%)': greg_leftover * 0.20,
        'Investments (15%)': greg_leftover * 0.15
    }
    greg_alloc_df = pd.DataFrame.from_dict(greg_allocations, orient='index', columns=['Amount ($)'])
    greg_alloc_df_display = greg_alloc_df.copy()
    greg_alloc_df_display['Amount ($)'] = greg_alloc_df_display['Amount ($)'].map(lambda x: f"{float(x):.2f}")
    st.table(greg_alloc_df_display)

    # NEW: Allocations per paycheck
    st.subheader("Allocations per paycheck")
    greg_allocations_per_paycheck = {k: v / 2 for k, v in greg_allocations.items()}
    greg_alloc_pp_df = pd.DataFrame.from_dict(greg_allocations_per_paycheck, orient='index', columns=['Amount ($)'])
    greg_alloc_pp_df_display = greg_alloc_pp_df.copy()
    greg_alloc_pp_df_display['Amount ($)'] = greg_alloc_pp_df_display['Amount ($)'].map(lambda x: f"{float(x):.2f}")
    st.table(greg_alloc_pp_df_display)

    # Charts
    st.plotly_chart(
        px.pie(
            pd.DataFrame(list(greg_expenses.items()), columns=['Category', 'Amount']),
            names='Category', values='Amount', title="Greg's Expenses"
        ),
        use_container_width=True
    )
    st.plotly_chart(
        px.bar(
            pd.DataFrame(list(greg_expenses.items()), columns=['Category', 'Amount']),
            x='Category', y='Amount', title="Greg's Expenses", color='Category'
        ),
        use_container_width=True
    )

    # PDF
    greg_pdf_buffer = create_budget_pdf("Greg", greg_income, greg_expenses, greg_leftover, greg_allocations, greg_allocations_per_paycheck)
    st.download_button("Download Greg's Budget PDF", data=greg_pdf_buffer, file_name="greg_budget.pdf", mime="application/pdf")

    # Save to session for combined tab use
    st.session_state["greg_income_value"] = greg_income
    st.session_state["greg_fixed"] = greg_fixed
    st.session_state["greg_subs"] = greg_subs
    st.session_state["greg_tracked_total"] = greg_tracked_expenses_total

# =========================================================
# TYLER’S SECTION (tab2)
# =========================================================
with tab2:
    st.header("💼 Tyler's Monthly Budget")

    col1, col2 = st.columns(2)
    with col1:
        tyler_income = st.number_input("Tyler's Monthly Income ($)", min_value=0, value=4788)
        tyler_fixed = st.number_input("Tyler's Fixed Costs", min_value=0, value=300)
    with col2:
        tyler_subs = st.number_input("Tyler's Subscriptions", min_value=0, value=100)

    # Pull Tyler's tracked expenses from sheet
    df_exp_all = load_expenses()
    tyler_tracked_expenses_total = float(df_exp_all[df_exp_all["Name"] == "Tyler"]["Amount"].sum())

    # Expenses dict now includes tracked expenses
    tyler_expenses = {
        'Rent (Shared)': rent / 2,
        'Utilities (Shared)': utilities / 2,
        'Fixed Costs': tyler_fixed,
        'Subscriptions': tyler_subs,
        'Tracked Expenses': tyler_tracked_expenses_total
    }
    tyler_total_expenses = sum(tyler_expenses.values())

    # Leftover
    tyler_leftover = tyler_income - tyler_total_expenses
    tyler_leftover = max(tyler_leftover, 0)
    tyler_savings_rate = (tyler_leftover / tyler_income * 100) if tyler_income else 0

    # Table — % of Income
    st.subheader("Breakdown — % of Income")
    tyler_percent_df = pd.DataFrame.from_dict(tyler_expenses, orient='index', columns=['Amount ($)'])
    tyler_percent_df['% of Income'] = (tyler_percent_df['Amount ($)'] / tyler_income * 100).round(2) if tyler_income else 0.0
    tyler_percent_df.loc['Total Expenses'] = [tyler_total_expenses, tyler_percent_df['% of Income'].sum()]
    leftover_percent_t = 100 - tyler_percent_df['% of Income'].sum() if tyler_income else 0.0
    tyler_percent_df.loc['Net Leftover'] = [tyler_leftover, leftover_percent_t]

    tyler_percent_df_display = tyler_percent_df.copy()
    tyler_percent_df_display['Amount ($)'] = tyler_percent_df_display['Amount ($)'].map(lambda x: f"{float(x):.2f}")
    tyler_percent_df_display['% of Income'] = tyler_percent_df_display['% of Income'].map(lambda x: f"{float(x):.2f}")
    st.table(tyler_percent_df_display)

    # Allocation
    st.subheader("Tyler's Allocations (from leftover)")
    tyler_allocations = {
        'Credit Card Payment (25%)': tyler_leftover * 0.25,
        'Savings (40%)': tyler_leftover * 0.40,
        'Spending Money (20%)': tyler_leftover * 0.20,
        'Investments (15%)': tyler_leftover * 0.15
    }
    tyler_alloc_df = pd.DataFrame.from_dict(tyler_allocations, orient='index', columns=['Amount ($)'])
    tyler_alloc_df_display = tyler_alloc_df.copy()
    tyler_alloc_df_display['Amount ($)'] = tyler_alloc_df_display['Amount ($)'].map(lambda x: f"{float(x):.2f}")
    st.table(tyler_alloc_df_display)

    # NEW: Allocations per paycheck
    st.subheader("Allocations per paycheck")
    tyler_allocations_per_paycheck = {k: v / 2 for k, v in tyler_allocations.items()}
    tyler_alloc_pp_df = pd.DataFrame.from_dict(tyler_allocations_per_paycheck, orient='index', columns=['Amount ($)'])
    tyler_alloc_pp_df_display = tyler_alloc_pp_df.copy()
    tyler_alloc_pp_df_display['Amount ($)'] = tyler_alloc_pp_df_display['Amount ($)'].map(lambda x: f"{float(x):.2f}")
    st.table(tyler_alloc_pp_df_display)

    # Charts
    st.plotly_chart(
        px.pie(
            pd.DataFrame(list(tyler_expenses.items()), columns=['Category', 'Amount']),
            names='Category', values='Amount', title="Tyler's Expenses"
        ),
        use_container_width=True
    )
    st.plotly_chart(
        px.bar(
            pd.DataFrame(list(tyler_expenses.items()), columns=['Category', 'Amount']),
            x='Category', y='Amount', title="Tyler's Expenses", color='Category'
        ),
        use_container_width=True
    )

    # PDF
    tyler_pdf_buffer = create_budget_pdf("Tyler", tyler_income, tyler_expenses, tyler_leftover, tyler_allocations, tyler_allocations_per_paycheck)
    st.download_button("Download Tyler's Budget PDF", data=tyler_pdf_buffer, file_name="tyler_budget.pdf", mime="application/pdf")

    # Save to session for combined tab use
    st.session_state["tyler_income_value"] = tyler_income
    st.session_state["tyler_fixed"] = tyler_fixed
    st.session_state["tyler_subs"] = tyler_subs
    st.session_state["tyler_tracked_total"] = tyler_tracked_expenses_total

# =========================================================
# COMBINED VIEW (tab3)
# =========================================================
with tab3:
    st.header("👥 Combined Budget View")

    # Pull values from session_state if available (so Combined reflects the inputs set in tabs)
    g_income = st.session_state.get("greg_income_value", 4788)
    g_fixed = st.session_state.get("greg_fixed", 400)
    g_subs = st.session_state.get("greg_subs", 80)
    g_tracked = st.session_state.get("greg_tracked_total", float(load_expenses()[lambda d: d["Name"] == "Greg"]["Amount"].sum()) if not load_expenses().empty else 0.0)

    t_income = st.session_state.get("tyler_income_value", 4788)
    t_fixed = st.session_state.get("tyler_fixed", 300)
    t_subs = st.session_state.get("tyler_subs", 100)
    t_tracked = st.session_state.get("tyler_tracked_total", float(load_expenses()[lambda d: d["Name"] == "Tyler"]["Amount"].sum()) if not load_expenses().empty else 0.0)

    combined_income = g_income + t_income
    combined_expenses = {
        'Rent': rent,
        'Utilities': utilities,
        'Greg Fixed': g_fixed,
        'Greg Subs': g_subs,
        'Greg Tracked Expenses': g_tracked,
        'Tyler Fixed': t_fixed,
        'Tyler Subs': t_subs,
        'Tyler Tracked Expenses': t_tracked
    }
    combined_total_expenses = sum(combined_expenses.values())
    combined_leftover = combined_income - combined_total_expenses
    combined_leftover = max(combined_leftover, 0)
    combined_savings_rate = (combined_leftover / combined_income * 100) if combined_income else 0.0

    st.subheader("Summary")
    combined_df = pd.DataFrame.from_dict(combined_expenses, orient='index', columns=['Amount ($)'])
    combined_df.loc['Total Expenses'] = combined_total_expenses
    combined_df.loc['Net Leftover'] = combined_leftover

    # Pretty formatting to two decimals
    combined_df_display = combined_df.copy()
    combined_df_display['Amount ($)'] = combined_df_display['Amount ($)'].map(lambda x: f"{float(x):.2f}")
    st.table(combined_df_display)

    st.metric("💸 Net Household Leftover", f"${combined_leftover:,.2f}")
    st.progress(min(max(combined_savings_rate / 100, 0), 1))

    st.subheader("Combined Expenses Breakdown")
    pie_df = pd.DataFrame(list(combined_expenses.items()), columns=['Category', 'Amount'])
    st.plotly_chart(px.pie(pie_df, names='Category', values='Amount', title="Combined Expenses"), use_container_width=True)
    st.plotly_chart(px.bar(pie_df, x='Category', y='Amount', title="Combined Expenses", color='Category'), use_container_width=True)
