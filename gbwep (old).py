# requires: pandas
# requires: matplotlib

from matplotlib.ticker import ScalarFormatter
import matplotlib.pyplot as plt
import pandas as pd
import argparse

GENERATION_TYPES = ['GAS', 'COAL', 'NUCLEAR', 'WIND', 'WIND_EMB', 'HYDRO', 'IMPORTS', 'BIOMASS', 'OTHER', 'SOLAR', 'STORAGE']

def refresh_data() :
    generation = pd.read_csv('https://api.neso.energy/dataset/88313ae5-94e4-4ddc-a790-593554d8c6b9/resource/f93d1835-75bc-43e5-84ad-12472b180a98/download/df_fuel_ckan.csv')
    prices = pd.read_csv('https://dp.lowcarboncontracts.uk/dataset/19f1ebee-93b7-4ef4-9465-bba50fa4ad06/resource/866e6a4e-86c7-411e-9464-2ac3ad56ae35/download/imrp_actuals.csv')
    generation.to_csv('data/generation.csv', index=False)
    prices.to_csv('data/prices.csv', index=False)

def load_data(start_date=None, end_date=None) :
    generation = pd.read_csv('data/generation.csv')
    prices = pd.read_csv('data/prices.csv')

    print(f'[DEBUG] Loaded {len(generation)} generation records and {len(prices)} price records')
    prices['DATETIME'] = pd.to_datetime(prices['IMRP_Date']) + (prices['Settlement_Period'] - 1) * pd.Timedelta(minutes=30)
    prices = prices.drop(columns=['IMRP_Date', 'Settlement_Period'])
    generation['DATETIME'] = pd.to_datetime(generation['DATETIME'])
    #generation = generation.drop([type + '_perc' for type in GENERATION_TYPES], axis=1)
    merged = pd.merge(prices, generation, on='DATETIME', how='inner')
    if start_date:
        merged = merged[merged['DATETIME'] >= start_date]
    if end_date:
        merged = merged[merged['DATETIME'] <= end_date]
    return merged

# Group data by price and generation type, then calculate average generation for each price group
def group_by_price_and_generation(data) :
    low_price_threshold = -55
    high_price_threshold = 500
    bins = [val for val in range(low_price_threshold, high_price_threshold + 1, 5)]
    data['PRICE_GROUP'] = pd.cut(data['IMRP_Amount'], 
                                 bins=bins + [float('inf')], 
                                 labels=[f'{bins[i]} to {bins[i+1]}' for i in range(len(bins)-1)] + [f'> {high_price_threshold}'])
    data['LOW_CARBON_perc'] = data['LOW_CARBON_perc'] - data['RENEWABLE_perc']
    grouped = data.groupby(['PRICE_GROUP'],  observed=True).mean().filter(['PRICE_GROUP', 'FOSSIL_perc', 'LOW_CARBON_perc', 'RENEWABLE_perc'])
    return grouped

# Group data by renewable percentage and calculate average price for each group
def group_by_renewable_and_price(data, generation='LOW_CARBON') :
    bins = [x for x in range(0, 101, 1)]
    data[f'{generation}_GROUP'] = pd.cut(data[f'{generation}_perc'], 
                                      bins=bins + [float('inf')], 
                                      labels=[f'{bins[i]} to {bins[i+1]}' for i in range(len(bins)-1)] + [f'> {bins[-1]}'])
    grouped = data.groupby([f'{generation}_GROUP'], observed=True).agg({'IMRP_Amount': 'mean', 'Total': 'sum'}).filter([f'{generation}_GROUP', 'IMRP_Amount', 'Total'])
    return grouped

def apply_filters(data, args) :
    print(f'{len(data)} records before filtering')
    if args.start_date:
        data = data[data['DATETIME'] >= pd.to_datetime(args.start_date)]
    if args.end_date:
        data = data[data['DATETIME'] <= pd.to_datetime(args.end_date)]
    print(f'{len(data)} records after date filtering')
    if args.max_mw is not None:
        data = data[data['Total'] <= args.max_mw]
    if args.min_mw is not None:
        data = data[data['Total'] >= args.min_mw]
    print(f'{len(data)} records after MW filtering')
    if args.exclude_peak:
        data = data[~data['DATETIME'].dt.hour.isin([7, 8, 9, 16, 17, 18])]
    print(f'{len(data)} records after peak hour filtering')
    if args.min_fossil_perc is not None:
        data = data[data['FOSSIL_perc'] >= args.min_fossil_perc]
    print(f'{len(data)} records after fossil percentage filtering')
    if args.max_fossil_perc is not None:
        data = data[data['FOSSIL_perc'] <= args.max_fossil_perc]
    print(f'{len(data)} records after fossil percentage filtering')

    return data

def show_chart(grouped_data, generation='LOW_CARBON') :
    ax = grouped_data['Total'].plot.bar(label='Total Generation (MWh)', legend=True)
    ax2 = grouped_data['IMRP_Amount'].plot.line(label='Average Price (£/MWh)', legend=True, color='red', marker='o', secondary_y=True, ax=ax)
    plt.xticks(
        [tick for tick in range(len(grouped_data.index) + 5) if tick % 5 == 0], 
        [f'{tick}' for tick in range(len(grouped_data.index) + 5) if tick % 5 == 0], 
        rotation=45)
    ax.set_xlabel(generation + ' (%)')
    plt.title('Average Price by ' + generation + ' Percentage')
    # Force plain notation on the secondary y-axis (generation)
    ax.yaxis.set_major_formatter(ScalarFormatter(useOffset=False, useMathText=False))
    ax.ticklabel_format(style='plain', axis='y')
    plt.show()

# Display scatter plot of price vs date, with points coloured by percentage of renewable generation
def show_scatter(data) :
    # First group the data by date and calculate the average price and renewable percentage for each day
    daily_data = data.groupby(data['DATETIME'].dt.date).agg({'IMRP_Amount': 'mean', 'RENEWABLE_perc': 'mean'}).reset_index()
    plt.scatter(daily_data['DATETIME'], daily_data['IMRP_Amount'], c=daily_data['RENEWABLE_perc'], cmap='viridis', alpha=0.5)
    plt.colorbar(label='Renewable Generation (%)')
    plt.xlabel('Date')
    plt.ylabel('Price (£/MWh)')
    plt.title('Price vs Date, coloured by Renewable Generation (%)')
    plt.show()

def weighted_percentile(df, val, weight, percentile=0.5):
    df_sorted = df.sort_values(val)
    cumsum = df_sorted[weight].cumsum()
    cutoff = df_sorted[weight].sum() * percentile
    return df_sorted[cumsum >= cutoff][val].iloc[0]


# Main function to load data, filter by date range, and print results
def main() :
    argparser = argparse.ArgumentParser(description='GB Generation data')
    argparser.add_argument('--start-date', type=str, help='Start date (inclusive) in YYYY-MM-DD format')
    argparser.add_argument('--end-date', type=str, help='End date (inclusive) in YYYY-MM-DD format')
    argparser.add_argument('--max-mw', type=float, help='Maximum generation in MW to include in the analysis')
    argparser.add_argument('--min-mw', type=float, help='Minimum generation in MW to include in the analysis')
    argparser.add_argument('--exclude-peak', action='store_true', help='Exclude morning and evening peak hours (7-10am and 4-7pm)')
    argparser.add_argument('--refresh-data', action='store_true', help='Refresh data by downloading the latest generation and price data from the APIs')
    argparser.add_argument('--show-chart', action='store_true', help='Show chart of generation and price data')
    argparser.add_argument('--min-fossil-perc', type=float, help='Minimum percentage of fossil generation to include in the analysis')
    argparser.add_argument('--max-fossil-perc', type=float, help='Maximum percentage of fossil generation to include in the analysis')
    args = argparser.parse_args()

    if args.refresh_data or not (pd.io.common.file_exists('data/generation.csv') and pd.io.common.file_exists('data/prices.csv')):
        refresh_data()

    generation = 'Fossil'

    data = apply_filters(load_data(), args)
    # Rename columns to match expected format
    data = data.rename(columns={'GENERATION': 'Total'})
    
    grouped_data = group_by_renewable_and_price(data, generation.upper())

    # Show weighted average price of each generation group over the selected date range
    labels = [ "Generation Group", "Total Generation (MWh)", "Total Generation (%)","Weighted Average Price (£/MWh)", "Median Price (£/MWh)", "25% Price (£/MWh)", "75% Price (£/MWh)" ]
    print('| '+ ' | '.join(labels) + ' |')
    print('|' + "|".join(['-' * (len(label) + 2) for label in labels]) + '|')
    for group in GENERATION_TYPES + [ 'Total' ]:
        if data[group].sum() < data['Total'].sum() * 0.001:  # Skip groups that contribute less than 0.1% of total generation
            continue
        values = [ 
            group,
            f'{data[group].sum():,.0f}', 
            f'{data[group].sum() / data["Total"].sum() * 100:.1f}%',
            f'{(data['IMRP_Amount'] * data[group]).sum() / data[group].sum()}', 
            f'{weighted_percentile(data, 'IMRP_Amount', group)}',
            f'{weighted_percentile(data, 'IMRP_Amount', group, 0.25)}',
            f'{weighted_percentile(data, 'IMRP_Amount', group, 0.75)}'
        ]
        s = ' '
        print(f'| {" | ".join([f"{item:{s}<{len(labels[i])}}" for i, item in enumerate(values)])} |')

    # Create a line plot of average generation percentage by renewable group
    if args.show_chart:
        #show_chart(grouped_data, generation.upper())
        show_scatter(data)
    # print("\n[DEBUG] grouped_data columns:", grouped_data.columns.tolist())
    # print("[DEBUG] grouped_data head:\n", grouped_data.head())
    # print("\n[DEBUG] RENEWABLE_GROUP values:", grouped_data.index.tolist())
    # try:
    #     plt.figure(figsize=(12, 6))
    #     plt.plot(grouped_data.index, grouped_data['FOSSIL_perc'], label='FOSSIL', marker='o')
    #     #plt.plot(grouped_data.index, grouped_data['LOW_CARBON_perc'], label='LOW_CARBON', marker='o')
    #     plt.plot(grouped_data.index, grouped_data['RENEWABLE_perc'], label='RENEWABLE', marker='o')
    #     plt.xlabel('Renewable Group (%)')
    #     plt.xticks(range(0, len(grouped_data.index), 5), [grouped_data.index[i] for i in range(0, len(grouped_data.index), 5)], rotation=45, fontsize=8, ha='right', va='top', rotation_mode='anchor')
    #     plt.ylabel('Average Generation Percentage (%)')
    #     plt.title('Average Generation Percentage by Renewable Group')
    #     plt.legend()
    #     plt.show()
    # except Exception as e:
    #     print("[ERROR] Exception during plotting:", e)
    #     import traceback; traceback.print_exc()
main()