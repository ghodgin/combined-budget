import streamlit as st
import pandas as pd
import plotly.express as px
from fpdf import FPDF
import io

def create_budget_pdf(name, expenses_dict, total, savings, allocations):
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
    pdf.cell(50, 10, f"${total:.2f}", 1)
    pdf.ln()

    pdf.cell(100, 10, "Net Savings", 1)
    pdf.cell(50, 10, f"${savings:.2f}", 1)
    pdf.ln(20)

    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="Savings Allocation", ln=True)
    pdf.set_font("Arial", '', 12)

    for k, v in allocations.items():
        pdf.cell(100, 10, k, 1)
        pdf.cell(50, 10, f"${v:.2f}", 1)
        pdf.ln()

    # Convert PDF to bytes and wrap in BytesIO
    pdf_bytes = pdf.output(dest='S').encode('latin1')
    return io.BytesIO(pdf_bytes)

### STREAMLIT APP ###

st.set_page_config(page_title="Greg & Tyler's Budget", layout="wide")
st.title("🏠 Monthly Budget Planner — Greg & Tyler")

tab1, tab2, tab3 = st.tabs(["Greg's Budget", "Tyler's Budget", "Combined View"])

# Constants
BAH = 2166  # Housing allowance per person
BAS = 465   # Food allowance per person

# Sidebar Inputs
with st.sidebar:
    st.header("📌 Shared Household Costs")
    rent = st.number_input("Monthly Rent ($)", min_value=0, value=2000)
    utilities = st.number_input("Monthly Utilities ($)", min_value=0, value=300)
    

# ------------------------- #
# GREG’S SECTION
# ------------------------- #
with tab1:
    st.header("💼 Greg's Monthly Budget")

    col1, col2 = st.columns(2)
    with col1:
        greg_income = st.number_input("Greg's Income ($)", min_value=0, value=2904 + BAH + BAS)
        greg_fixed = st.number_input("Greg's Other Fixed Costs (e.g. car, insurance)", min_value=0, value=400)
    with col2:
        greg_subs = st.number_input("Greg's Subscriptions", min_value=0, value=80)

    greg_expenses = {
        'Rent (Shared)': rent / 2,
        'Utilities (Shared)': utilities / 2,
        'Fixed Costs': greg_fixed,
        'Subscriptions': greg_subs
    }

    greg_total_expenses = sum(greg_expenses.values())
    greg_bah_surplus = max(0, BAH - greg_expenses['Rent (Shared)'])
    greg_savings = greg_income - greg_total_expenses + greg_bah_surplus
    greg_savings_rate = (greg_savings / greg_income) * 100 if greg_income else 0

    greg_expenses = {
        'Rent (Shared)': rent / 2,
        'Utilities (Shared)': utilities / 2,
        'Fixed Costs': greg_fixed,
        'Subscriptions': greg_subs,
        'Savings': greg_savings
    }

    st.subheader("Breakdown — % of Income")
    greg_percent_df = pd.DataFrame.from_dict(greg_expenses, orient='index', columns=['Amount ($)'])
    greg_percent_df['Amount ($) per Paycheck'] = (greg_percent_df['Amount ($)'] / 2).round(2)
    greg_percent_df['% of Income'] = (greg_percent_df['Amount ($)'] / greg_income * 100).round(2)
    greg_percent_df.loc['Total Expenses'] = [
        greg_total_expenses,
        greg_total_expenses / 2,
        greg_percent_df['% of Income'].sum()
    ]
    greg_percent_df.loc['Net Savings'] = [
        greg_savings,
        greg_savings / 2,
        100 - greg_percent_df['% of Income'].sum()
    ]
    st.table(greg_percent_df)

    st.subheader("Military Allowance Adjustments")
    st.markdown(f"- **BAH used:** ${greg_expenses['Rent (Shared)']:.2f} / Surplus: ${greg_bah_surplus:.2f}")

    st.metric("💸 Total after expenses", f"${greg_savings:,.2f}")
    st.progress(min(max(greg_savings_rate / 100, 0), 1))

    st.subheader("Greg's Spending Breakdown")
    pie_df = pd.DataFrame(list(greg_expenses.items()), columns=['Category', 'Amount'])
    st.plotly_chart(px.pie(pie_df, names='Category', values='Amount', title="Greg's Expense Breakdown"))
    st.plotly_chart(px.bar(pie_df, x='Category', y='Amount', title="Greg's Expense Comparison", color='Category'))

    st.subheader("Greg's Savings Allocation")
    greg_allocations = {
        'Credit Card Payment (25%)': greg_savings * 0.25,
        'Savings (40%)': greg_savings * 0.40,
        'Spending Money (20%)': greg_savings * 0.20,
        'Investments (15%)': greg_savings * 0.15
    }
    st.table(pd.DataFrame.from_dict(greg_allocations, orient='index', columns=['Amount ($)']))

    st.subheader("Greg's Savings Allocation Per Paycheck")
    st.table(pd.DataFrame.from_dict({k: v / 2 for k, v in greg_allocations.items()}, orient='index', columns=['Amount ($)']))

    # PDF EXPORT
    greg_pdf_buffer = create_budget_pdf(
        name="Greg",
        expenses_dict=greg_expenses,
        total=greg_total_expenses,
        savings=greg_savings,
        allocations=greg_allocations
    )

    st.download_button(
        label="Download Greg's Budget PDF",
        data=greg_pdf_buffer,
        file_name="greg_budget.pdf",
        mime="application/pdf"
    )



# ------------------------- #
# TYLER’S SECTION
# ------------------------- #
with tab2:
    st.header("💼 Tyler's Monthly Budget")

    col1, col2 = st.columns(2)
    with col1:
        tyler_income = st.number_input("Tyler's Income ($)", min_value=0, value=3354 + BAH + BAS)
        tyler_fixed = st.number_input("Tyler's Other Fixed Costs (e.g. car, insurance)", min_value=0, value=300)
    with col2:
        tyler_subs = st.number_input("Tyler's Subscriptions", min_value=0, value=100)

    tyler_expenses = {
        'Rent (Shared)': rent / 2,
        'Utilities (Shared)': utilities / 2,
        'Fixed Costs': tyler_fixed,
        'Subscriptions': tyler_subs
    }

    tyler_total_expenses = sum(tyler_expenses.values())
    tyler_bah_surplus = max(0, BAH - tyler_expenses['Rent (Shared)'])
    tyler_savings = tyler_income - tyler_total_expenses + tyler_bah_surplus
    tyler_savings_rate = (tyler_savings / tyler_income) * 100 if tyler_income else 0

    st.subheader("Breakdown — % of Income")
    tyler_percent_df = pd.DataFrame.from_dict(tyler_expenses, orient='index', columns=['Amount ($)'])
    tyler_percent_df['Amount ($) per Paycheck'] = (tyler_percent_df['Amount ($)'] / 2).round(2)
    tyler_percent_df['% of Income'] = (tyler_percent_df['Amount ($)'] / tyler_income * 100).round(2)
    tyler_percent_df.loc['Total Expenses'] = [
        tyler_total_expenses,
        tyler_total_expenses / 2,
        tyler_percent_df['% of Income'].sum()
    ]
    tyler_percent_df.loc['Net Savings'] = [
        tyler_savings,
        tyler_savings / 2,
        100 - tyler_percent_df['% of Income'].sum()
    ]
    st.table(tyler_percent_df)

    st.subheader("Military Allowance Adjustments")
    st.markdown(f"- **BAH used:** ${tyler_expenses['Rent (Shared)']:.2f} / Surplus: ${tyler_bah_surplus:.2f}")

    st.metric("💸 Total after expenses", f"${tyler_savings:,.2f}")
    st.progress(min(max(tyler_savings_rate / 100, 0), 1))

    st.subheader("Tyler's Spending Breakdown")
    pie_df = pd.DataFrame(list(tyler_expenses.items()), columns=['Category', 'Amount'])
    st.plotly_chart(px.pie(pie_df, names='Category', values='Amount', title="Tyler's Expense Breakdown"))
    st.plotly_chart(px.bar(pie_df, x='Category', y='Amount', title="Tyler's Expense Comparison", color='Category'))

    st.subheader("Tyler's Savings Allocation")
    tyler_allocations = {
        'Credit Card Payment (25%)': tyler_savings * 0.15,
        'Savings (40%)': tyler_savings * 0.55,
        'Spending Money (20%)': tyler_savings * 0.30
    }
    st.table(pd.DataFrame.from_dict(tyler_allocations, orient='index', columns=['Amount ($)']))

    st.subheader("Tyler's Savings Allocation Per Paycheck")
    st.table(pd.DataFrame.from_dict({k: v / 2 for k, v in tyler_allocations.items()}, orient='index', columns=['Amount ($)']))

    # PDF Export for Tyler
    st.subheader("📄 Export Tyler's Budget as PDF")
    tyler_pdf_buffer = create_budget_pdf(
        name="Tyler",
        expenses_dict=tyler_expenses,
        total=tyler_total_expenses,
        savings=tyler_savings,
        allocations=tyler_allocations
    )
    st.download_button(
        label="Download Tyler's Budget PDF",
        data=tyler_pdf_buffer,
        file_name="tyler_budget.pdf",
        mime="application/pdf"
    )


# ------------------------- #
# COMBINED VIEW
# ------------------------- #
with tab3:
    st.header("👥 Combined Budget View")

    combined_income = greg_income + tyler_income
    combined_expenses = {
        'Rent (Shared)': rent,
        'Utilities (Shared)': utilities,
        'Greg Fixed': greg_fixed,
        'Greg Subscriptions': greg_subs,
        'Tyler Fixed': tyler_fixed,
        'Tyler Subscriptions': tyler_subs
    }

    combined_total_expenses = sum(combined_expenses.values())
    combined_savings = combined_income - combined_total_expenses
    combined_savings_rate = (combined_savings / combined_income) * 100 if combined_income else 0

    st.subheader("Summary")
    combined_df = pd.DataFrame.from_dict(combined_expenses, orient='index', columns=['Amount ($)'])
    combined_df.loc['Total Expenses'] = combined_total_expenses
    combined_df.loc['Net Savings'] = combined_savings
    st.table(combined_df)

    st.metric("💸 Net Household Savings", f"${combined_savings:,.2f}")
    st.progress(min(max(combined_savings_rate / 100, 0), 1))

    st.subheader("Combined Expense Breakdown")
    pie_df = pd.DataFrame(list(combined_expenses.items()), columns=['Category', 'Amount'])
    st.plotly_chart(px.pie(pie_df, names='Category', values='Amount', title="Combined Expenses"))
    st.plotly_chart(px.bar(pie_df, x='Category', y='Amount', title="Combined Expense Comparison", color='Category'))
