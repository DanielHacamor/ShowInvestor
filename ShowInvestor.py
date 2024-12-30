# --- Existing Imports ---
import streamlit as st
import mysql.connector  # Add this for MySQL connectivity
import pandas as pd
import plotly.express as px
from io import BytesIO
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, PageBreak, Image
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from matplotlib import pyplot as plt  # Add this for generating charts
import hashlib  # Add this for password hashing

# --- 1. MySQL Connection ---
def create_connection():
    """
    Establish a connection to the MySQL database.
    Returns the connection object if successful, otherwise None.
    """
    try:
        conn = mysql.connector.connect(
            host="localhost",
            database="ShowInvestorDB",
            user="root",
            password="Tohseen23#"
        )
        if conn.is_connected():
            return conn
    except mysql.connector.Error as e:
        st.error(f"Error: {e}")
        return None

# --- 2. Hash Password ---
def hash_password(password):
    """Hash a password using SHA-256 for secure storage."""
    return hashlib.sha256(password.encode()).hexdigest()

# --- 3. Validate User ---
def validate_user(username, password):
    """
    Validate user credentials against the database.
    Returns the user's role if valid, otherwise None.
    """
    conn = create_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and hash_password(password) == user["password"]:
            return user["role"]
    return None

# --- 4. Analyze Data ---
def analyze_data(df):
    """
    Preprocess and classify financial data.
    Adds 'Type' (Sales or Expense) and 'Month' columns to the DataFrame.
    Ensures months are arranged in proper monthly order.
    """
    # Ensure 'Amount' column is numeric (converting any non-numeric values to NaN)
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
    
    # Remove rows with NaN values in the 'Amount' column
    df = df.dropna(subset=["Amount"])
    
    # Convert 'Date' to datetime format
    df["Date"] = pd.to_datetime(df["Date"])
    
    # Classify transactions as either 'Sales' (positive) or 'Expense' (negative)
    df["Type"] = df["Amount"].apply(lambda x: "Sales" if x > 0 else "Expense")
    
    # Create a 'Month' column from the 'Date' column (using month names)
    df["Month"] = df["Date"].dt.strftime("%B")  # 'Month' as full name (e.g., 'January', 'February')
    
    # Ensure months are ordered chronologically, not alphabetically
    month_order = ['January', 'February', 'March', 'April', 'May', 'June', 
                   'July', 'August', 'September', 'October', 'November', 'December']
    df["Month"] = pd.Categorical(df["Month"], categories=month_order, ordered=True)
    
    return df.sort_values("Month")

# --- 5. Generate Insights ---
def generate_insights(df):
    """
    Generate key business metrics and insights.
    Outputs:
        - Total sales, total expenses, net profit
        - Monthly summary (grouped by 'Month' and 'Type')
        - Product performance analysis
    """
    # Calculate total sales (positive values in 'Amount' column)
    total_sales = df[df["Type"] == "Sales"]["Amount"].sum()

    # Calculate total expenses (negative values in 'Amount' column)
    total_expenses = df[df["Type"] == "Expense"]["Amount"].sum()

    # Calculate net profit (sales + expenses)
    net_profit = total_sales + total_expenses

    # Generate monthly summary (grouped by 'Month' and 'Type')
    monthly_summary = df.groupby(["Month", "Type"])["Amount"].sum().reset_index()

    # Generate monthly profit (Sales - Expenses)
    monthly_reviews = []
    for month in monthly_summary["Month"].unique():
        sales = monthly_summary[(monthly_summary["Month"] == month) & (monthly_summary["Type"] == "Sales")]["Amount"].sum()
        expenses = monthly_summary[(monthly_summary["Month"] == month) & (monthly_summary["Type"] == "Expense")]["Amount"].sum()
        profit = sales + expenses  # Profit = Sales - Expenses

        # Add a brief review
        if profit > 0:
            review = "The business performed well this month with a positive profit margin."
        elif profit < 0:
            review = "Expenses were higher than sales, resulting in a loss this month. Consider reducing expenses."
        else:
            review = "Sales and expenses were balanced this month."

        monthly_reviews.append({
            "Month": month,
            "Sales": sales,
            "Expenses": expenses,
            "Profit": profit,
            "Review": review
        })

    # Product performance
    product_performance = df[df["Type"] == "Sales"].groupby("Description")["Amount"].sum().reset_index()
    product_performance = product_performance.sort_values(by="Amount", ascending=False)

    # Top-performing products
    top_products = product_performance.head(5)

    # Underperforming products
    underperforming_products = product_performance.tail(5)

    insights = {
        "total_sales": total_sales,
        "total_expenses": total_expenses,
        "net_profit": net_profit,
        "monthly_summary": monthly_summary,  # Monthly summary
        "monthly_reviews": monthly_reviews,  # New monthly reviews with profit and reviews
        "product_performance": product_performance,  # All product performance
        "top_products": top_products,  # Top 5 products
        "underperforming_products": underperforming_products,  # Bottom 5 products
    }

    return insights

# --- Helper Function: Generate Aggregate Chart ---
def generate_aggregate_chart(monthly_reviews):
    """
    Generate a bar chart for aggregate performance across all months.
    """
    months = [review["Month"] for review in monthly_reviews]
    sales = [review["Sales"] for review in monthly_reviews]
    expenses = [abs(review["Expenses"]) for review in monthly_reviews]
    profit = [review["Profit"] for review in monthly_reviews]

    plt.figure(figsize=(8, 5))
    plt.bar(months, sales, label="Sales", color="green", alpha=0.7)
    plt.bar(months, expenses, label="Expenses", color="red", alpha=0.7)
    plt.plot(months, profit, label="Profit", color="blue", marker="o", linestyle="--")
    plt.title("Overall Performance - Sales, Expenses, and Profit")
    plt.xlabel("Months")
    plt.ylabel("Amount (₦)")
    plt.legend()
    plt.xticks(rotation=45)

    chart = BytesIO()
    plt.savefig(chart, format="png")
    chart.seek(0)
    plt.close()
    return chart

# --- Helper Function: Generate Monthly Chart ---
def generate_monthly_chart(month, sales, expenses):
    """
    Generate a bar chart for monthly sales and expenses.
    """
    labels = ["Sales", "Expenses"]
    values = [sales, abs(expenses)]
    colors = ["green", "red"]

    plt.figure(figsize=(6, 4))
    plt.bar(labels, values, color=colors)
    plt.title(f"Performance for {month}")
    plt.ylabel("Amount (₦)")

    chart = BytesIO()
    plt.savefig(chart, format="png")
    chart.seek(0)
    plt.close()
    return chart

# --- 6. Updated Generate PDF Report ---
def generate_pdf(data, file_name, title, business_logo=None, business_name=None, insights=None):
    """
    Generate a detailed PDF report with tables, charts, and insightful reviews.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    # Add Business Logo
    if business_logo:
        logo = Image(business_logo, width=100, height=100)
        elements.append(logo)

    # Add Business Name and Title
    elements.append(Paragraph(f"<b>{business_name or 'Business Name'}</b>", styles["Title"]))
    elements.append(Paragraph(title, styles["Heading2"]))
    elements.append(Paragraph(f"Report Date: {datetime.now().strftime('%Y-%m-%d')}", styles["Normal"]))
    elements.append(Spacer(1, 12))

    # --- Annual Summary Table ---
    elements.append(Paragraph("Annual Performance Summary (Detailed)", styles["Heading2"]))
    table_data = [["Month", "Sales", "Expenses", "Profit"]]

    # Add monthly performance to the table
    for review in insights["monthly_reviews"]:
        table_data.append([
            review["Month"],
            f"₦{review['Sales']:,.2f}",
            f"₦{abs(review['Expenses']):,.2f}",
            f"₦{review['Profit']:,.2f}"
        ])

    # Define column widths to make sure the table fits the page
    col_widths = [100, 100, 100, 100]  # Adjust this if needed to fit the page

    # Create the table with appropriate widths and styles
    table = Table(table_data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BOX", (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 12))

    # --- 2. Overall Performance Chart ---
    aggregate_chart = generate_aggregate_chart(insights["monthly_reviews"])
    elements.append(Paragraph("Overall Performance Chart", styles["Heading2"]))
    elements.append(Image(aggregate_chart, width=400, height=250))
    elements.append(PageBreak())

    # --- 3. Monthly Charts and Reviews ---
    for review in insights["monthly_reviews"]:
        elements.append(Paragraph(f"Monthly Performance - {review['Month']}", styles["Heading2"]))
        table_data = [
            ["Sales", f"₦{review['Sales']:,.2f}"],
            ["Expenses", f"₦{abs(review['Expenses']):,.2f}"],
            ["Profit", f"₦{review['Profit']:,.2f}"]
        ]
        table = Table(table_data, colWidths=[200, 200])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(table)

        # Add Monthly Performance Chart
        monthly_chart = generate_monthly_chart(review["Month"], review["Sales"], review["Expenses"])
        elements.append(Image(monthly_chart, width=400, height=250))
        elements.append(Spacer(1, 12))

        # Add detailed review summary
        elements.append(Paragraph(f"**Summary**: {review['Review']}", styles["Normal"]))
        elements.append(PageBreak())

    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

# --- 7. Updated Dashboard Function ---
# --- Updated Dashboard Function ---
def dashboard():
    """
    Dashboard for uploading sales and expenses separately, analyzing data,
    and generating detailed monthly tables, charts, and insightful narrations.
    """
    st.title("📊 ShowInvestor Dashboard")
    st.markdown("### Upload Your Financial Data")

    # Business details
    business_name = st.text_input("Enter your business name:")
    business_logo = st.file_uploader("Upload your business logo (optional):", type=["png", "jpg", "jpeg"])

    # File upload for Sales and Expenses
    st.subheader("Upload Sales File")
    sales_file = st.file_uploader("Sales File (CSV, Excel)", type=["csv", "xlsx"], key="sales_file")

    st.subheader("Upload Expenses File")
    expenses_file = st.file_uploader("Expenses File (CSV, Excel)", type=["csv", "xlsx"], key="expenses_file")

    # Process Sales and Expense Files
    if sales_file and expenses_file:
        # Load Sales Data
        if sales_file.name.endswith(".csv"):
            sales_df = pd.read_csv(sales_file)
        else:
            sales_df = pd.read_excel(sales_file)

        # Load Expenses Data
        if expenses_file.name.endswith(".csv"):
            expenses_df = pd.read_csv(expenses_file)
        else:
            expenses_df = pd.read_excel(expenses_file)

        # Validate Required Columns
        required_columns = {"Date", "Description", "Amount"}
        if not required_columns.issubset(sales_df.columns) or not required_columns.issubset(expenses_df.columns):
            st.error(f"Both files must contain the following columns: {required_columns}")
            return

        # Add 'Type' column
        sales_df["Type"] = "Sales"
        expenses_df["Type"] = "Expense"

        # Combine Data
        df = pd.concat([sales_df, expenses_df], ignore_index=True)
        df = analyze_data(df)

        # Check for 'Type' column
        if 'Type' not in df.columns:
            st.error("The 'Type' column is missing. Please ensure the data is processed correctly.")
            return

        # Filter by Type
        sales_data = df[df['Type'] == 'Sales']
        expense_data = df[df['Type'] == 'Expense']

        # Generate Insights
        insights = generate_insights(df)

        # Display Business Metrics
        st.subheader("📈 Key Business Metrics")
        col1, col2, col3 = st.columns(3)
        col1.metric("💰 Total Sales", f"₦{insights['total_sales']:,.2f}")
        col2.metric("💸 Total Expenses", f"₦{abs(insights['total_expenses']):,.2f}")
        col3.metric("📊 Net Profit", f"₦{insights['net_profit']:,.2f}")

        # Display Product Performance
        st.subheader("📦 Product Performance Analysis")

        # Display top-performing products
        st.markdown("### 🏆 Top 5 Best-Selling Products")
        st.dataframe(insights["top_products"])

        # Display underperforming products
        st.markdown("### 🚩 Bottom 5 Underperforming Products")
        st.dataframe(insights["underperforming_products"])

        # Visualize product performance
        st.markdown("### 📊 Product Sales Visualization")
        fig = px.bar(
            insights["product_performance"],
            x="Description",
            y="Amount",
            title="Sales Performance by Product",
            labels={"Description": "Product", "Amount": "Sales (₦)"},
            color="Amount",
        )
        st.plotly_chart(fig)

        # Display Table and Narration
        st.subheader("📝 Insights and Recommendations")
        for review in insights["monthly_reviews"]:
            st.markdown(f"### **{review['Month']}**")
            st.write(f"- **Sales**: ₦{review['Sales']:,.2f}")
            st.write(f"- **Expenses**: ₦{abs(review['Expenses']):,.2f}")
            st.write(f"- **Profit**: ₦{review['Profit']:,.2f}")
            st.write(f"**Summary**: {review['Review']}")
        st.write(
            "📌 *Overall, reducing unnecessary expenses and improving sales of underperforming products "
            "could lead to significant profit growth.*"
        )

        # Generate and Download PDF Report
        st.subheader("📄 Generate Investor-Ready Report")
        pdf = generate_pdf(
            data=insights["monthly_summary"],
            file_name="Investor_Report.pdf",
            title="Business Performance Report",
            business_logo=business_logo,
            business_name=business_name,
            insights=insights,
        )
        st.download_button(
            label="Download Investor Report",
            data=pdf,
            file_name="Investor_Report.pdf",
            mime="application/pdf",
        )

# --- 8. Main Application ---
def main():
    """
    Entry point for the app.
    Handles navigation between Login and Dashboard.
    """
    # Initialize session state
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False


    if not st.session_state.logged_in:
        st.title("Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            role = validate_user(username, password)
            if role:
                st.session_state.logged_in = True
                st.success(f"Welcome, {username.capitalize()} ({role.capitalize()})!")
                st.experimental_rerun()
            else:
                st.error("Invalid username or password.")
    else:
        st.sidebar.title("Navigation")
        menu_option = st.sidebar.selectbox("Menu", ["Dashboard", "Logout"])
        if menu_option == "Dashboard":
            dashboard()
        elif menu_option == "Logout":
            st.session_state.logged_in = False
            st.experimental_rerun()

# --- 9. Run the App ---
if __name__ == "__main__":
    st.set_page_config(page_title="ShowInvestor", page_icon="💼", layout="wide")
    main()