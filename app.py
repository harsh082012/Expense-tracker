import os
import csv
import calendar
import datetime
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, make_response
import time

# --- Initial Configuration ---
app = Flask(__name__)
BUDGET = 2000

# Use absolute path for CSV file
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
EXPENSE_FILE_PATH = os.path.join(BASE_DIR, "expenses.csv")

EXPENSE_CATEGORIES = [
    "🍔 Food",
    "🏠 Home",
    "💼 Work",
    "🎉 Fun",
    "✨ Miscellaneous",
]

# --- Core Functions ---

def initialize_csv():
    """Ensures the expenses.csv file exists with the correct 4-column header."""
    if not os.path.exists(EXPENSE_FILE_PATH) or os.path.getsize(EXPENSE_FILE_PATH) == 0:
        print(f"Initializing new CSV file at: {EXPENSE_FILE_PATH}")
        with open(EXPENSE_FILE_PATH, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Name', 'Amount', 'Category', 'Date'])
    else:
        clean_csv()  # Clean existing CSV if it exists

def clean_csv():
    """Clean the CSV file by keeping only valid 4-column rows."""
    try:
        with open(EXPENSE_FILE_PATH, 'r') as f:
            lines = f.readlines()
        
        # Keep header and valid rows
        valid_lines = [lines[0]]  # Keep header
        for line in lines[1:]:
            if len(line.strip().split(',')) == 4:  # Ensure exactly 4 columns
                valid_lines.append(line)
        
        # Write back cleaned content
        with open(EXPENSE_FILE_PATH, 'w') as f:
            f.writelines(valid_lines)
        print(f"Cleaned CSV file at: {EXPENSE_FILE_PATH}")
    except Exception as e:
        print(f"Error cleaning CSV: {e}")

# Call initialization on startup
initialize_csv()

def get_summary():
    """
    Reads the CSV file, calculates totals, and prepares summary data.
    Includes debugging to inspect file content and dataframe.
    """
    try:
        # Debug: Read and print raw CSV content
        with open(EXPENSE_FILE_PATH, 'r') as f:
            raw_content = f.read()
            print(f"Raw CSV content:\n{raw_content}")

        # Read CSV with pandas, enforce column names
        df = pd.read_csv(
            EXPENSE_FILE_PATH,
            header=0,
            names=['Name', 'Amount', 'Category', 'Date'],
            on_bad_lines='skip',
            skipinitialspace=True,
            sep=','
        )

        # Debug: Print the parsed dataframe
        print(f"Parsed DataFrame:\n{df.to_string()}")

        # Ensure 'Amount' column is numeric
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)

        # --- Calculations ---
        total_spent = df['Amount'].sum()
        remaining_budget = BUDGET - total_spent

        # Calculate daily budget
        now = datetime.datetime.now()
        days_in_month = calendar.monthrange(now.year, now.month)[1]
        remaining_days = max(1, days_in_month - now.day + 1)
        daily_budget = remaining_budget / remaining_days

        # Group expenses by category
        amount_by_category = df.groupby('Category')['Amount'].sum().round(2).to_dict()

        # Prepare recent expenses (last 5, sorted by index descending)
        recent_expenses = df.tail(5).sort_index(ascending=False).to_dict('records')

        # --- Prepare Summary Output ---
        summary = {
            'total_spent': f"${total_spent:.2f}",
            'remaining_budget': f"${remaining_budget:.2f}",
            'daily_budget': f"${daily_budget:.2f}",
            'category_summary': amount_by_category,
            'recent_expenses': recent_expenses
        }

        return summary, total_spent

    except pd.errors.EmptyDataError:
        print("CSV file is empty or only contains a header.")
        return {
            'total_spent': '$0.00',
            'remaining_budget': f"${BUDGET:.2f}",
            'daily_budget': f"${BUDGET/30:.2f}",
            'category_summary': {},
            'recent_expenses': []
        }, 0

    except Exception as e:
        print(f"An error occurred during summarization: {type(e).__name__}: {e}")
        return {
            'total_spent': '$0.00',
            'remaining_budget': f"${BUDGET:.2f}",
            'daily_budget': f"${BUDGET/30:.2f}",
            'category_summary': {},
            'recent_expenses': []
        }, 0

# --- Flask Routes ---

@app.route('/', methods=['GET', 'POST'])
def index():
    """Handles the main page display and expense submission."""
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            amount = float(request.form.get('amount'))
            category = request.form.get('category')
            date = datetime.date.today().isoformat()

            if name and amount > 0 and category in EXPENSE_CATEGORIES:
                new_row = [name, f"{amount:.2f}", category, date]
                with open(EXPENSE_FILE_PATH, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(new_row)

                # Increase delay to ensure file write completes
                time.sleep(0.5)

                # Cache-busting redirect
                timestamp = int(datetime.datetime.now().timestamp())
                return redirect(url_for('index', _t=timestamp))
            else:
                print("Invalid input detected in POST request.")
                return redirect(url_for('index', message="Invalid input. Please check your entries."))

        except ValueError:
            print("Invalid amount submitted (not a number).")
            return redirect(url_for('index', message="Invalid amount. Please enter a valid number."))
        except Exception as e:
            print(f"Error saving expense: {e}")
            return redirect(url_for('index', message="Error saving expense. Please try again."))

    # For GET request
    summary, total_spent = get_summary()

    # Format data for the HTML chart
    chart_data = [
        {'name': cat, 'value': summary['category_summary'].get(cat, 0.00)}
        for cat in EXPENSE_CATEGORIES
    ]

    # Add no-cache headers to response
    response = make_response(
        render_template(
            'index.html',
            budget=BUDGET,
            summary=summary,
            categories=EXPENSE_CATEGORIES,
            total_spent=f"${total_spent:.2f}",
            chart_data=chart_data,
            message=request.args.get('message')
        )
    )
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'

    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)