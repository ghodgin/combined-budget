import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os
import shutil
from fpdf import FPDF
import io

# ------------------------- #
# Config
# ------------------------- #
st.set_page_config(page_title="Budget & Expense Tracker", layout="wide")

DATA_FILE = "expenses.csv"

# ------------------------- #
# Expense Tracker Helpers
# ------------------------- #
def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE, parse_dates=["Date"])
    else:
        return pd.DataFrame(columns=["Date", "Category", "Amount", "Notes"])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

def archive_data():
    if os.path.exists(DATA_FILE) and os.path.getsize(DATA_FILE) > 0:
        month_str = datetime.today().strftime("%Y_%m")
        archive_name = f"expenses_{month_str}.csv"
        shutil.move(DATA_FILE, archive_name)  # Move old file
        st.success(f"📦 Archived to {archive_name}")
    else:
        st.warning("⚠️ Nothing to archive.")

# ------------------------- #
# Budget PDF Helper
# ------------------------- #
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


# ------------------------- #
# Tabs
# ------------------------- #
tab_expense, tab_greg, tab_tyler, tab_combined = st.tabs(
    ["💸 Expense Tracker", "Greg's Budget", "Tyler's Budget", "Combined View"]
)

# ------------------------- #
# EXPENSE TRACKER TAB
# ------------------------- #
with tab_expense:
    st.title("💸 Expense Tracker")

    # Sidebar: Add new expense
    st.sidebar.header("Add New Expense")

    with st.sidebar.form("expense_form", clear_on_submit=True):
        name = st.selectbox("Name", ['Greg', 'Tyler'])   # 👈 Added
        date = st.date_input("Date", datetime.today())
        category = st.selectbox("Category", ["Food", "Transport", "Shopping", "Bills", "Entertainment", "Other"])
        amount = st.number_input("Amount", min_value=0.0, format="%.2f")
        notes = st.text_input("Notes (optional)")
        submitted = st.form_submit_button("Add Expense")

    # Load data
    df = load_data()

    # Add expense
    if submitted:
        new_expense = pd.DataFrame(
            [[name, date, category, amount, notes]],   # 👈 Inserted `name`
            columns=["Name", "Date", "Category", "Amount", "Notes"]  # 👈 Name is first column
        )
        df = pd.concat([df, new_expense], ignore_index=True)
        save_data(df)
        st.sidebar.success("✅ Expense added!")

    # Reset / Archive Buttons
    st.sidebar.subheader("Manage Data")

    if st.sidebar.button("🧹 Clear All Expenses"):
        df = pd.DataFrame(columns=["Name", "Date", "Category", "Amount", "Notes"])  # 👈 Reset includes Name
        save_data(df)
        st.sidebar.success("🧹 All expenses cleared!")

    if st.sidebar.button("📦 Archive & Clear"):
        archive_data()
        df = pd.DataFrame(columns=["Name", "Date", "Category", "Amount", "Notes"])  # 👈 Reset includes Name
        save_data(df)

    # Dashboard
    st.subheader("📊 Expense Dashboard")

    if df.empty:
        st.info("No expenses yet. Add some from the sidebar.")
    else:
        st.dataframe(df.sort_values("Date", ascending=False), use_container_width=True)

        total_spent = df["Amount"].sum()
        st.metric("Total Spent", f"${total_spent:,.2f}")

        category_sum = df.groupby("Category")["Amount"].sum().reset_index()
        fig1 = px.pie(category_sum, values="Amount", names="Category", title="Expenses by Category")
        st.plotly_chart(fig1, use_container_width=True)

        daily_sum = df.groupby("Date")["Amount"].sum().reset_index()
        fig2 = px.line(daily_sum, x="Date", y="Amount", title="Expenses Over Time", markers=True)
        st.plotly_chart(fig2, use_container_width=True)



# ------------------------- #
# SHARED COST INPUTS
# ------------------------- #
with st.sidebar:
    st.header("📌 Shared Household Costs")
    rent = st.number_input("Monthly Rent ($)", min_value=0, value=1440)
    utilities = st.number_input("Monthly Utilities ($)", min_value=0, value=300)


# ------------------------- #
# GREG'S BUDGET
# ------------------------- #
with tab_greg:
    st.header("💼 Greg's Monthly Budget")

    col1, col2 = st.columns(2)
    with col1:
        greg_income = st.number_input("Greg's Monthly Income ($)", min_value=0, value=4788)
        greg_fixed = st.number_input("Greg's Fixed Costs", min_value=0, value=400)
    with col2:
        greg_subs = st.number_input("Greg's Subscriptions", min_value=0, value=80)

    greg_expenses = {
        'Rent (Shared)': rent / 2,
        'Utilities (Shared)': utilities / 2,
        'Fixed Costs': greg_fixed,
        'Subscriptions': greg_subs
    }
    greg_total_expenses = sum(greg_expenses.values())
    greg_leftover = max(greg_income - greg_total_expenses, 0)

    st.subheader("Breakdown — % of Income")
    greg_percent_df = pd.DataFrame.from_dict(greg_expenses, orient='index', columns=['Amount ($)'])
    greg_percent_df['% of Income'] = (greg_percent_df['Amount ($)'] / greg_income * 100).round(2)
    greg_percent_df.loc['Total Expenses'] = [greg_total_expenses, greg_percent_df['% of Income'].sum()]
    greg_percent_df.loc['Net Leftover'] = [greg_leftover, 100 - greg_percent_df['% of Income'].sum()]
    st.table(greg_percent_df)

    st.subheader("Greg's Allocations (from leftover)")
    greg_allocations = {
        'Credit Card Payment (25%)': greg_leftover * 0.25,
        'Savings (40%)': greg_leftover * 0.40,
        'Spending Money (20%)': greg_leftover * 0.20,
        'Investments (15%)': greg_leftover * 0.15
    }
    st.table(pd.DataFrame.from_dict(greg_allocations, orient='index', columns=['Amount ($)']))

    st.subheader("Allocations per paycheck")
    greg_allocations_per_paycheck = {k: v / 2 for k, v in greg_allocations.items()}
    st.table(pd.DataFrame.from_dict(greg_allocations_per_paycheck, orient='index', columns=['Amount ($)']))

    st.plotly_chart(px.pie(pd.DataFrame(list(greg_expenses.items()), columns=['Category', 'Amount']),
                           names='Category', values='Amount', title="Greg's Expenses"))
    st.plotly_chart(px.bar(pd.DataFrame(list(greg_expenses.items()), columns=['Category', 'Amount']),
                           x='Category', y='Amount', title="Greg's Expenses", color='Category'))

    greg_pdf_buffer = create_budget_pdf("Greg", greg_income, greg_expenses, greg_leftover, greg_allocations, greg_allocations_per_paycheck)
    st.download_button("Download Greg's Budget PDF", data=greg_pdf_buffer, file_name="greg_budget.pdf", mime="application/pdf")


# ------------------------- #
# TYLER'S BUDGET
# ------------------------- #
with tab_tyler:
    st.header("💼 Tyler's Monthly Budget")

    col1, col2 = st.columns(2)
    with col1:
        tyler_income = st.number_input("Tyler's Monthly Income ($)", min_value=0, value=4788)
        tyler_fixed = st.number_input("Tyler's Fixed Costs", min_value=0, value=300)
    with col2:
        tyler_subs = st.number_input("Tyler's Subscriptions", min_value=0, value=100)

    tyler_expenses = {
        'Rent (Shared)': rent / 2,
        'Utilities (Shared)': utilities / 2,
        'Fixed Costs': tyler_fixed,
        'Subscriptions': tyler_subs
    }
    tyler_total_expenses = sum(tyler_expenses.values())
    tyler_leftover = max(tyler_income - tyler_total_expenses, 0)

    st.subheader("Breakdown — % of Income")
    tyler_percent_df = pd.DataFrame.from_dict(tyler_expenses, orient='index', columns=['Amount ($)'])
    tyler_percent_df['% of Income'] = (tyler_percent_df['Amount ($)'] / tyler_income * 100).round(2)
    tyler_percent_df.loc['Total Expenses'] = [tyler_total_expenses, tyler_percent_df['% of Income'].sum()]
    tyler_percent_df.loc['Net Leftover'] = [tyler_leftover, 100 - tyler_percent_df['% of Income'].sum()]
    st.table(tyler_percent_df)

    st.subheader("Tyler's Allocations (from leftover)")
    tyler_allocations = {
        'Credit Card Payment (25%)': tyler_leftover * 0.25,
        'Savings (40%)': tyler_leftover * 0.40,
        'Spending Money (20%)': tyler_leftover * 0.20,
        'Investments (15%)': tyler_leftover * 0.15
    }
    st.table(pd.DataFrame.from_dict(tyler_allocations, orient='index', columns=['Amount ($)']))

    st.subheader("Allocations per paycheck")
    tyler_allocations_per_paycheck = {k: v / 2 for k, v in tyler_allocations.items()}
    st.table(pd.DataFrame.from_dict(tyler_allocations_per_paycheck, orient='index', columns=['Amount ($)']))

    st.plotly_chart(px.pie(pd.DataFrame(list(tyler_expenses.items()), columns=['Category', 'Amount']),
                           names='Category', values='Amount', title="Tyler's Expenses"))
    st.plotly_chart(px.bar(pd.DataFrame(list(tyler_expenses.items()), columns=['Category', 'Amount']),
                           x='Category', y='Amount', title="Tyler's Expenses", color='Category'))

    tyler_pdf_buffer = create_budget_pdf("Tyler", tyler_income, tyler_expenses, tyler_leftover, tyler_allocations, tyler_allocations_per_paycheck)
    st.download_button("Download Tyler's Budget PDF", data=tyler_pdf_buffer, file_name="tyler_budget.pdf", mime="application/pdf")


# ------------------------- #
# COMBINED VIEW
# ------------------------- #
with tab_combined:
    st.header("👥 Combined Budget View")

    combined_income = greg_income + tyler_income
    combined_expenses = {
        'Rent': rent,
        'Utilities': utilities,
        'Greg Fixed': greg_fixed,
        'Greg Subs': greg_subs,
        'Tyler Fixed': tyler_fixed,
        'Tyler Subs': tyler_subs
    }
    combined_total_expenses = sum(combined_expenses.values())
    combined_leftover = max(combined_income - combined_total_expenses, 0)
    combined_savings_rate = (combined_leftover / combined_income * 100) if combined_income else 0

    st.subheader("Summary")
    combined_df = pd.DataFrame.from_dict(combined_expenses, orient='index', columns=['Amount ($)'])
    combined_df.loc['Total Expenses'] = combined_total_expenses
    combined_df.loc['Net Leftover'] = combined_leftover
    st.table(combined_df)

    st.metric("💸 Net Household Leftover", f"${combined_leftover:,.2f}")
    st.progress(min(max(combined_savings_rate / 100, 0), 1))

    st.subheader("Combined Expenses Breakdown")
    st.plotly_chart(px.pie(pd.DataFrame(list(combined_expenses.items()), columns=['Category', 'Amount']),
                           names='Category', values='Amount', title="Combined Expenses"))
    st.plotly_chart(px.bar(pd.DataFrame(list(combined_expenses.items()), columns=['Category', 'Amount']),
                           x='Category', y='Amount', title="Combined Expenses", color='Category'))
