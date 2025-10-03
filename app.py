import os
import calendar
import datetime
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename
from io import StringIO

# --- Initial Setup ---
app = Flask(__name__)
# The budget is set here. In a real app, this would be stored in a database.
BUDGET = 2000
EXPENSE_FILE_PATH = "expenses.csv"
EXPENSE_CATEGORIES = [
    "🍔 Food",
    "🏠 Home",
    "💼 Work",
    "🎉 Fun",
    "✨ Miscellaneous",
]

# Ensure the CSV file exists with headers if it's new
def initialize_csv():
    if not os.path.exists(EXPENSE_FILE_PATH):
        # Create a DataFrame with the structure we expect
        df = pd.DataFrame(columns=['Name', 'Amount', 'Category', 'Date'])
        df.to_csv(EXPENSE_FILE_PATH, index=False)
        print(f"Created new CSV file at: {EXPENSE_FILE_PATH}")

# Call initialization on startup
initialize_csv()


def get_summary():
    """Reads the CSV file, calculates totals, and prepares summary data."""
    try:
        # Load the CSV data
        df = pd.read_csv(EXPENSE_FILE_PATH)
        
        # Ensure 'Amount' column is numeric
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
        
        # Calculate summary
        total_spent = df['Amount'].sum()
        
        # Group expenses by category
        amount_by_category = df.groupby('Category')['Amount'].sum().round(2).to_dict()
        
        # Prepare for budget calculation
        remaining_budget = BUDGET - total_spent
        
        now = datetime.datetime.now()
        days_in_month = calendar.monthrange(now.year, now.month)[1]
        remaining_days = days_in_month - now.day
        
        # Handle division by zero if remaining_days is 0 or less
        daily_budget = remaining_budget / remaining_days if remaining_days > 0 else remaining_budget
        
        # Format for display
        summary = {
            'total_spent': f"${total_spent:.2f}",
            'remaining_budget': f"${remaining_budget:.2f}",
            'daily_budget': f"${daily_budget:.2f}",
            'category_summary': amount_by_category,
            'recent_expenses': df.tail(5).to_dict('records') # Get last 5 for display
        }
        
        return summary, total_spent
        
    except FileNotFoundError:
        print(f"Error: {EXPENSE_FILE_PATH} not found.")
        return {'total_spent': '$0.00', 'remaining_budget': f"${BUDGET:.2f}", 'daily_budget': f"${BUDGET/30:.2f}", 'category_summary': {}, 'recent_expenses': []}, 0
    except Exception as e:
        print(f"An error occurred during summarization: {e}")
        return {'total_spent': '$0.00', 'remaining_budget': f"${BUDGET:.2f}", 'daily_budget': f"${BUDGET/30:.2f}", 'category_summary': {}, 'recent_expenses': []}, 0


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
                # Append the new expense to the CSV file
                with open(EXPENSE_FILE_PATH, 'a') as f:
                    f.write(f"\n{name},{amount:.2f},{category},{date}")
                
                # Redirect to GET request to prevent form resubmission on refresh
                return redirect(url_for('index'))
            else:
                # In a production app, we would flash a warning message here
                print("Invalid input detected.")

        except ValueError:
            print("Invalid amount submitted.")
        except Exception as e:
            print(f"Error saving expense: {e}")

    # For GET request (or after POST redirect)
    summary, total_spent = get_summary()
    
    # Calculate chart data for categories
    chart_data = [
        {'name': cat, 'value': summary['category_summary'].get(cat, 0.00)}
        for cat in EXPENSE_CATEGORIES
    ]

    return render_template(
        'index.html',
        budget=BUDGET,
        summary=summary,
        categories=EXPENSE_CATEGORIES,
        total_spent=f"${total_spent:.2f}",
        chart_data=chart_data,
        message=request.args.get('message')
    )

# Required for Render deployment using Gunicorn
if __name__ == '__main__':
    # When running locally:
    app.run(debug=True)
