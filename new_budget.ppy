import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os

# ------------------------- #
# Config
# ------------------------- #
st.set_page_config(page_title="Expense Tracker", layout="wide")

DATA_FILE = "expenses.csv"

# ------------------------- #
# Helper Functions
# ------------------------- #
def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE, parse_dates=["Date"])
    else:
        return pd.DataFrame(columns=["Date", "Category", "Amount", "Notes"])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# ------------------------- #
# App Layout
# ------------------------- #
st.title("💸 Expense Tracker")

# Sidebar for adding expenses
st.sidebar.header("Add New Expense")

with st.sidebar.form("expense_form", clear_on_submit=True):
    date = st.date_input("Date", datetime.today())
    category = st.selectbox("Category", ["Food", "Transport", "Shopping", "Bills", "Entertainment", "Other"])
    amount = st.number_input("Amount", min_value=0.0, format="%.2f")
    notes = st.text_input("Notes (optional)")
    submitted = st.form_submit_button("Add Expense")

# Load existing data
df = load_data()

# Add new expense if submitted
if submitted:
    new_expense = pd.DataFrame(
        [[date, category, amount, notes]],
        columns=["Date", "Category", "Amount", "Notes"]
    )
    df = pd.concat([df, new_expense], ignore_index=True)
    save_data(df)
    st.sidebar.success("✅ Expense added!")

# ------------------------- #
# Main Dashboard
# ------------------------- #
st.subheader("📊 Expense Dashboard")

if df.empty:
    st.info("No expenses yet. Add some from the sidebar.")
else:
    # Show table
    st.dataframe(df.sort_values("Date", ascending=False), use_container_width=True)

    # Total spent
    total_spent = df["Amount"].sum()
    st.metric("Total Spent", f"${total_spent:,.2f}")

    # Spending by category
    category_sum = df.groupby("Category")["Amount"].sum().reset_index()
    fig1 = px.pie(category_sum, values="Amount", names="Category", title="Expenses by Category")
    st.plotly_chart(fig1, use_container_width=True)

    # Spending over time
    daily_sum = df.groupby("Date")["Amount"].sum().reset_index()
    fig2 = px.line(daily_sum, x="Date", y="Amount", title="Expenses Over Time", markers=True)
    st.plotly_chart(fig2, use_container_width=True)
