# Plotting Price vs Demand

import matplotlib.pyplot as plt

data = pd.read_csv(os.path.join(TRANSFORMED_DATA_DIR, 'market-data.csv'))
def filter_data(data, start_date, end_date):
    print(f'{len(data)} records before filtering')
    filtered_data = data.copy()

    filtered_data = filtered_data[filtered_data['SettlementDate'] >= pd.to_datetime(start_date)]
    filtered_data = filtered_data[filtered_data['SettlementDate'] <= pd.to_datetime(end_date)]
    print(f'{len(filtered_data)} records after date filtering')
    filtered_data = filtered_data[filtered_data[target_generation + '_perc'] >= minimum_usage]

    print(f'{len(filtered_data)} records after filtering by {NESO_GENERATION_TYPES[target_generation]} percentage >= {minimum_usage}%')

    return filtered_data