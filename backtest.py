# PredictNow.ai Backtesting Inverse Volatility Method Assignment

# Importing required libraries
import warnings
import pandas as pd
import matplotlib.pyplot as plt

# Filter warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

# Assigning 0 to the risk-free rate constant
RISK_FREE_RATE = 0
# Setting initial portfolio value to $100.00
INITIAL_PORTFOLIO_VALUE = 100.00
# Setting start date
START_DATE = '2020-01-01'
# Setting end date
END_DATE = '2022-12-31'


def fetch_etf_data(start_date, end_date):
    """
        Fetches historical daily price data for a given ETF from provided .csv file data,
        between the specified start and end dates.

        Parameters:
        - start_date (str): The start date (inclusive) of the date range to fetch data for, in the format 'YYYY-MM-DD'
        - end_date (str): The end date (inclusive) of the date range to fetch data for, in the format 'YYYY-MM-DD'

        Returns:
        - etf_data_df (DataFrame): A pandas DataFrame with historical adjusted closing daily price data for each ETF,
          between the specified start and end dates.
    """

    # define a list of CSV file names to fetch ETF data from
    etf_files = ['EEM.csv', 'GLD.csv', 'SPY.csv', 'TLT.csv', 'VGK.csv']
    # define an empty dictionary to hold the ETF data
    etf_data_dict = {}
    # loop through the CSV files to fetch OHLC data for each etf,
    # and add the 'Adj Close' column to the etf_data dictionary with the file name as the etf symbol
    for file in etf_files:
        etf = pd.read_csv('data/' + file)
        etf_data_dict[file[:-4]] = etf['Adj Close']

    # create a new pandas dataframe from the etf_data dictionary
    etf_data_df = pd.DataFrame(etf_data_dict)
    # convert the 'Date' column to a pandas datetime object and set as index
    etf_data_df['Date'] = pd.to_datetime(etf['Date'])
    etf_data_df = etf_data_df.set_index('Date')
    # filter the dataframe to only include data between 2020-01-01 and 2022-12-31 as defined by start_date and end_date
    etf_data_df = etf_data_df.loc[start_date:end_date]
    # return the filtered dataframe
    return etf_data_df


def calculate_allocation_weights(lookback_data):
    """
        Calculates the allocation weights for a given set of target weights and historical prices.

        Parameters:
        - lookback_data (DataFrame): The values for the past trading days within the month

        Returns:
        - allocation_weights (DataFrame): A pandas DataFrame containing the allocation weights for each asset in the portfolio.
    """

    # Calculate daily returns of the given data
    returns = lookback_data.pct_change()
    # Calculate volatility over a rolling window of specified lookback
    vol = returns.rolling(len(returns.index), min_periods=1).std(ddof=0)
    # Calculate inverse volatility
    inv_vol = 1 / vol
    # Calculate allocation weights by dividing last row of inv_vol by its sum
    allocation_weights = inv_vol.iloc[-1] / inv_vol.iloc[-1].sum()
    # return the allocation weights dataframe
    return allocation_weights


def rebalance_portfolio(data):
    """
       Rebalances the portfolio based on the current allocation weights and current prices.

       Parameters:
       - data (DataFrame): A pandas DataFrame with historical adjusted closing daily price data for each ETF,
          between the specified start date and end of month iteration

       Returns:
       - rebalancing_date (timestamp): A timestamp date of the rebalancing.
       - target_allocations (pd.Series): A Series containing the allocation weights for each ETF.
    """

    # Created as a filter for past 30 days of data extending a month
    lookback_days = 30
    # Create dataframe of data from trading days in the past month
    lookback_data = data.iloc[-lookback_days:][data.iloc[-lookback_days:].index.month == data.iloc[-lookback_days:].index[-1].month]
    # Calculate allocation weights based on past data
    target_allocations = calculate_allocation_weights(lookback_data)
    # Get the date of the rebalancing
    rebalancing_date = data.index[-1]
    # return rebalancing_date, target_allocations
    return rebalancing_date, target_allocations


if __name__ == '__main__':

    # Fetch ETF data
    etf_data = fetch_etf_data(START_DATE, END_DATE)

    # Initialize portfolio allocations and shares to trade dataframes
    portfolio_allocations = pd.DataFrame(index=[etf_data.index[0]], columns=etf_data.columns)
    shares_to_trade = pd.DataFrame(index=[etf_data.index[0]], columns=etf_data.columns)
    # Create initial empty list for rebalancing dates
    rebalancing_dates = []

    # Iterate through ETF data
    for i in range(1, len(etf_data)):

        # Get list of ETF dates
        etf_date_list = etf_data.index.tolist()

        # Check if it's time to rebalance the portfolio
        if (etf_date_list[i] == etf_date_list[len(etf_data)-1]) or (etf_date_list[i].month != etf_date_list[i + 1].month):
            # Get lookback data
            lookback_data = etf_data.iloc[:i]
            # Rebalance portfolio
            rebalancing_date, new_allocations = rebalance_portfolio(lookback_data)
            # Append new allocations and rebalancing dates to dataframes
            portfolio_allocations = portfolio_allocations.append(new_allocations, ignore_index=True)
            rebalancing_dates.append(rebalancing_date)

        # Calculate daily returns
        daily_returns = etf_data / etf_data.shift(1) - 1
        daily_returns = daily_returns.reindex(columns=portfolio_allocations.columns)

    # Calculate portfolio value over time
    portfolio_value = pd.DataFrame(columns=['value'])
    portfolio_value.loc[daily_returns.index[0], 'value'] = INITIAL_PORTFOLIO_VALUE
    for i in range(1, len(daily_returns)):
        daily_portfolio_value = portfolio_value.iloc[-1]['value'] * (
                1 + daily_returns.iloc[i].dot(portfolio_allocations.iloc[-1]))
        portfolio_value.loc[daily_returns.index[i], 'value'] = daily_portfolio_value

    # Plot portfolio value over time
    plt.figure(figsize=(13, 8))
    plt.plot(portfolio_value.index, portfolio_value)
    plt.title('Portfolio Value Over Time')
    plt.xlabel('Date')
    plt.ylabel('Value ($)')
    plt.savefig('output/portfolio_value.png')

    # Find statistics regarding portfolio value
    print('Starting Portfolio Value $', round(portfolio_value['value'][0], 2))
    print('Ending Portfolio Value $', round(portfolio_value['value'][-1], 2))
    print('Max Portfolio Value $', round(max(portfolio_value['value'].tolist()), 2))
    print('Min Portfolio Value $', round(min(portfolio_value['value'].tolist()), 2))

    # Write portfolio allocations to CSV file
    rebalancing_dates.insert(0, '')
    portfolio_allocations['Rebalancing Dates'] = pd.Series(rebalancing_dates)
    portfolio_allocations = portfolio_allocations.iloc[1:]
    first_column = portfolio_allocations.pop('Rebalancing Dates')
    portfolio_allocations.insert(0, 'Rebalancing Dates', first_column)
    portfolio_allocations = portfolio_allocations.set_index('Rebalancing Dates')
    portfolio_allocations.to_csv('output/portfolio_allocations.csv')

    # Calculate the returns of the portfolio using the 'pct_change' method, then drop any NaN values
    portfolio_returns = portfolio_value.pct_change().dropna()
    # Calculate the Sharpe Ratio using the formula:
    # (mean portfolio return - risk-free rate) / portfolio standard deviation
    sharpe_ratio = (portfolio_returns.mean() - RISK_FREE_RATE) / portfolio_returns.std()
    # Extract the value of the Sharpe Ratio from the resulting Pandas series
    sharpe_ratio = sharpe_ratio['value']

    # Extract the starting and ending values of the portfolio, as well as the start and end dates
    start_value = portfolio_value.iloc[0]['value']
    start_date = portfolio_value.index[0]
    end_value = portfolio_value.iloc[-1]['value']
    end_date = portfolio_value.index[-1]
    # Calculate the number of years between the start and end dates
    n_years = (end_date - start_date).days / 365.25
    # Calculate the Compound Annual Growth Rate (CAGR) using the formula:
    # ((end value / start value) ^ (1 / n_years) - 1)
    cagr = ((end_value / start_value) ** (1 / n_years) - 1)

    # Print the Sharpe Ratio and CAGR
    print(f"Sharpe Ratio: {sharpe_ratio}")
    print(f"Compound Annual Growth Rate (CAGR): {cagr}")
