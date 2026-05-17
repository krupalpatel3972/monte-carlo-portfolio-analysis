# =============================================================================
# Risk-Adjusted Return Analysis: Monte Carlo Study of Portfolio Efficiency
# Author: Krupal Patel
# Description: Downloads 25 years of historical stock data, calculates log
#              returns, stores in SQLite, runs 10,000 Monte Carlo simulations,
#              plots the Efficient Frontier, and identifies the optimal
#              Max Sharpe Ratio and Min Volatility portfolios.
# =============================================================================

# --- IMPORTS -----------------------------------------------------------------
import numpy as np
import pandas as pd
import yfinance as yf
import sqlite3
import matplotlib.pyplot as plt
from datetime import datetime

# =============================================================================
# STEP 1: DOWNLOAD HISTORICAL STOCK DATA & CALCULATE LOG RETURNS
# =============================================================================

tickers = ['MSFT', 'JNJ', 'CVX', 'WMT', 'MA']
start_date = '2000-01-01'
end_date = datetime.today().strftime('%Y-%m-%d')  # FIX: convert to string for yfinance

database_name = 'portfolio_project.db'
table_name = 'daily_returns'

print(f"Starting data download for tickers: {tickers}")
print(f"Date range: {start_date} to {end_date}")

try:
    data = yf.download(tickers, start=start_date, end=end_date, auto_adjust=False)['Adj Close']
    print("\n✅ Data download complete.")
    print("First few rows of Price Data:")
    print(data.head())
except Exception as e:
    print(f"\n❌ ERROR during data download: {e}")
    exit()

# Calculate log returns and drop NaN rows
log_returns = np.log(data / data.shift(1))
log_returns = log_returns.dropna()

print(f"\n✅ Log Returns calculated and cleaned.")
print(f"Total trading days in dataset: {len(log_returns)}")
print(log_returns.head())

# =============================================================================
# STEP 2: STORE LOG RETURNS IN SQLITE DATABASE
# =============================================================================

conn = sqlite3.connect(database_name)
log_returns.to_sql(table_name, conn, if_exists='replace')
print(f"\n✅ Data saved to '{database_name}' → table: '{table_name}'")

# Verify data was saved correctly
test_query = pd.read_sql(f"SELECT * FROM {table_name} LIMIT 5", conn)
conn.close()
print("\nSQL Verification (First 5 rows from database):")
print(test_query)

# =============================================================================
# STEP 3: MONTE CARLO SIMULATION — 10,000 RANDOM PORTFOLIOS
# =============================================================================

trading_days = 252        # Standard annual trading days
risk_free_rate = 0.02     # 2% annual risk-free rate (US Treasury benchmark)
num_portfolios = 10000

# Annualized statistics
mean_returns = log_returns.mean() * trading_days
cov_matrix = log_returns.cov() * trading_days
num_assets = len(log_returns.columns)

# Pre-allocate result arrays for performance
results_array = np.zeros((3, num_portfolios))           # Return, Volatility, Sharpe
weights_array = np.zeros((num_assets, num_portfolios))  # FIX: separate line

print(f"\nRunning {num_portfolios:,} Monte Carlo simulations...")

for i in range(num_portfolios):
    # Generate random weights that sum to 1
    weights = np.random.random(num_assets)
    weights /= np.sum(weights)

    # Portfolio metrics
    portfolio_return = np.sum(mean_returns * weights)
    portfolio_std_dev = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
    sharpe_ratio = (portfolio_return - risk_free_rate) / portfolio_std_dev

    # Store results
    results_array[0, i] = portfolio_return
    results_array[1, i] = portfolio_std_dev
    results_array[2, i] = sharpe_ratio
    weights_array[:, i] = weights

print("✅ Simulation complete.")

# =============================================================================
# STEP 4: BUILD RESULTS DATAFRAME
# =============================================================================

# Stack results and weights into one array, then create DataFrame
final_results_array = np.vstack([results_array, weights_array])
columns = ['Return', 'Volatility', 'Sharpe_Ratio'] + [f'Wt_{t}' for t in log_returns.columns]
results_df = pd.DataFrame(final_results_array.T, columns=columns)

# =============================================================================
# STEP 5: IDENTIFY OPTIMAL PORTFOLIOS
# =============================================================================

# --- Maximum Sharpe Ratio Portfolio (Best Risk-Adjusted Return) ---
max_sharpe_idx = results_df['Sharpe_Ratio'].idxmax()
max_sharpe_portfolio = results_df.iloc[max_sharpe_idx]

print("\n--- A. Maximum Sharpe Ratio Portfolio (Best Risk-Adjusted Return) ---")
print(f"  Return:       {max_sharpe_portfolio['Return']:.2%}")
print(f"  Volatility:   {max_sharpe_portfolio['Volatility']:.2%}")
print(f"  Sharpe Ratio: {max_sharpe_portfolio['Sharpe_Ratio']:.4f}")
print("\n  Asset Weights:")
for ticker in log_returns.columns:
    print(f"    {ticker}: {max_sharpe_portfolio[f'Wt_{ticker}']:.2%}")

# --- Minimum Volatility Portfolio (Lowest Risk) ---
min_volatility_idx = results_df['Volatility'].idxmin()
min_volatility_portfolio = results_df.iloc[min_volatility_idx]

print("\n--- B. Minimum Volatility Portfolio (Lowest Risk) ---")
print(f"  Return:       {min_volatility_portfolio['Return']:.2%}")
print(f"  Volatility:   {min_volatility_portfolio['Volatility']:.2%}")
print(f"  Sharpe Ratio: {min_volatility_portfolio['Sharpe_Ratio']:.4f}")
print("\n  Asset Weights:")
for ticker in log_returns.columns:
    print(f"    {ticker}: {min_volatility_portfolio[f'Wt_{ticker}']:.2%}")

# =============================================================================
# STEP 6: PLOT THE EFFICIENT FRONTIER
# =============================================================================

plt.figure(figsize=(12, 8))

# Scatter all 10,000 portfolios, colored by Sharpe Ratio
scatter = plt.scatter(
    results_df['Volatility'],
    results_df['Return'],
    c=results_df['Sharpe_Ratio'],
    cmap='viridis',
    alpha=0.6,
    s=10
)
plt.colorbar(scatter, label='Sharpe Ratio')
plt.grid(True, linestyle='--', alpha=0.5)

# Highlight Max Sharpe portfolio
plt.scatter(
    max_sharpe_portfolio['Volatility'],
    max_sharpe_portfolio['Return'],
    marker='*',
    color='red',
    s=400,
    zorder=5,
    label=f"Max Sharpe Ratio  (Return: {max_sharpe_portfolio['Return']:.1%}, Sharpe: {max_sharpe_portfolio['Sharpe_Ratio']:.2f})"
)

# Highlight Min Volatility portfolio
plt.scatter(
    min_volatility_portfolio['Volatility'],
    min_volatility_portfolio['Return'],
    marker='*',
    color='blue',
    s=400,
    zorder=5,
    label=f"Min Volatility  (Return: {min_volatility_portfolio['Return']:.1%}, Vol: {min_volatility_portfolio['Volatility']:.1%})"
)

plt.title('Monte Carlo Simulation: The Efficient Frontier\n'
          f'10,000 Random Portfolios — {", ".join(tickers)}', fontsize=14)
plt.xlabel('Annualized Volatility (Risk)', fontsize=12)
plt.ylabel('Annualized Return', fontsize=12)
plt.legend(labelspacing=0.8, fontsize=10)

# Format axes as percentages
plt.gca().xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0%}"))
plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0%}"))

plt.tight_layout()
plt.savefig('visualizations/efficient_frontier.png', dpi=150, bbox_inches='tight')
plt.show()
print("\n✅ Efficient Frontier plot saved to visualizations/efficient_frontier.png")
