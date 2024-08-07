import pandas as pd
from faker import Faker
import random
import numpy as np
from datetime import datetime, timedelta


# Initialize faker and create a random seed for reproducibility
fake = Faker()
Faker.seed(0)
random.seed(0)

# Define number of records
num_customers = 1000
num_accounts = 1200
num_kyc = 1000

# Helper functions
def generate_dob(start_year=1920, min_age=18, skew_factor=5):
    """Generates a positively skewed date of birth."""
    current_date = datetime.now()
    min_dob = current_date - timedelta(days=min_age*365)
    max_dob = datetime(start_year, 1, 1)
    max_days = (min_dob - max_dob).days
    while True:
        skewed_days = int(np.random.gamma(shape=skew_factor, scale=max_days/skew_factor))
        dob = max_dob + timedelta(days=skewed_days)
        if dob <= min_dob:
            return dob.date()

def generate_recent_dates(dob):
    """Generates a CreatedDate at least 18 years after DOB and a ModifiedDate between CreatedDate and now, with CreatedDate at least 1 month before the present."""
    min_created_date = datetime(dob.year, dob.month, dob.day) + timedelta(days=18*365)  # At least 18 years after DOB
    now = datetime.utcnow()
    one_month_ago = now - timedelta(days=30)  # 1 month ago from now

    # Ensure min_created_date is at least one month ago
    if min_created_date > one_month_ago:
        min_created_date = one_month_ago

    created_date = min_created_date + timedelta(days=random.randint(0, (one_month_ago - min_created_date).days))
    modified_date = created_date + timedelta(days=random.randint(0, (now - created_date).days))  # ModifiedDate between CreatedDate and now
    return created_date, modified_date

# Generate Customer Data
customers = []
for _ in range(num_customers):
    dob = generate_dob()
    created_date, modified_date = generate_recent_dates(dob)
    address = fake.address().replace('\n', ' ').replace('\r', '')  # Replace newlines with spaces
    customers.append({
        'CustomerID': _ + 1,
        'FirstName': fake.first_name(),
        'LastName': fake.last_name(),
        'DateOfBirth': dob,
        'Email': fake.unique.email(),
        'PhoneNumber': fake.unique.phone_number(),
        'Address': address,
        'CreatedDate': created_date,
        'ModifiedDate': modified_date
    })
customer_df = pd.DataFrame(customers)

# Generate Account Data
account_types = ['Savings', 'Checking']
account_statuses = ['Active', 'Inactive', 'Closed']
account_type_weights = [0.6, 0.4]  # 60% Savings, 40% Checking
account_status_weights = [0.6, 0.3, 0.1]  # 60% Active, 30% Inactive, 10% Closed

accounts = []
customer_latest_account_date = {}
for i, customer in customer_df.iterrows():
    customer_id = customer['CustomerID']
    customer_created_date = customer['CreatedDate']
    account_created_date = customer_created_date
    account_modified_date = account_created_date + timedelta(days=random.randint(0, (datetime.utcnow() - account_created_date).days))

    accounts.append({
        'AccountID': len(accounts) + 1,
        'CustomerID': customer_id,
        'AccountNumber': fake.unique.bban(),
        'AccountType': random.choices(account_types, weights=account_type_weights, k=1)[0],
        'AccountStatus': random.choices(account_statuses, weights=account_status_weights, k=1)[0],
        'CreatedDate': account_created_date,
        'ModifiedDate': account_modified_date
    })
    customer_latest_account_date[customer_id] = account_created_date

# Generate additional accounts
for _ in range(num_accounts - num_customers):
    customer = customer_df.sample().iloc[0]
    customer_id = customer['CustomerID']
    customer_created_date = customer['CreatedDate']

    if customer_id in customer_latest_account_date:
        previous_account_date = customer_latest_account_date[customer_id]
        if (datetime.utcnow() - previous_account_date).days > 0:
            account_created_date = previous_account_date + timedelta(days=random.randint(1, (datetime.utcnow() - previous_account_date).days))
        else:
            account_created_date = previous_account_date
    else:
        account_created_date = customer_created_date

    account_modified_date = account_created_date + timedelta(days=random.randint(0, (datetime.utcnow() - account_created_date).days))

    accounts.append({
        'AccountID': len(accounts) + 1,
        'CustomerID': customer_id,
        'AccountNumber': fake.unique.bban(),
        'AccountType': random.choices(account_types, weights=account_type_weights, k=1)[0],
        'AccountStatus': random.choices(account_statuses, weights=account_status_weights, k=1)[0],
        'CreatedDate': account_created_date,
        'ModifiedDate': account_modified_date
    })
    customer_latest_account_date[customer_id] = account_created_date

# Create Account DataFrame
account_df = pd.DataFrame(accounts)

def generate_skewed_last_updated(created_date, skew_factor=5):
    """Generates a LastUpdated date between CreatedDate and now, skewed towards the present."""
    now = datetime.utcnow()
    max_days = (now - created_date).days
    if max_days <= 0:
        return now
    scale = max(max_days / skew_factor, 1)
    skewed_days = min(int(np.random.gamma(shape=skew_factor, scale=scale)), max_days)
    last_updated = created_date + timedelta(days=skewed_days)
    return last_updated

# Generate Balance Data
balances = []
for i, account in account_df.iterrows():
    account_id = account['AccountID']
    account_status = account['AccountStatus']
    account_created_date = account['CreatedDate']
    if account_status == 'Closed':
        balance_amount = 0
    else:
        balance_amount = round(random.uniform(100, 10000), 2)
    last_updated = generate_skewed_last_updated(account_created_date)
    balances.append({
        'BalanceID': len(balances) + 1,
        'AccountID': account_id,
        'Balance': balance_amount,
        'Currency': 'USD',
        'LastUpdated': last_updated
    })

# Create Balance DataFrame
balance_df = pd.DataFrame(balances)

# Get Expiry Date
def generate_valid_issue_expiry_dates(dob, customer_created_date):
    customer_dob_datetime = datetime(dob.year, dob.month, dob.day)
    max_possible_issue_date = min(datetime.utcnow(), customer_created_date) - timedelta(days=365)

    if max_possible_issue_date <= customer_dob_datetime + timedelta(days=18*365):
        issue_date = customer_dob_datetime + timedelta(days=18*365)
    else:
        issue_date = customer_dob_datetime + timedelta(days=random.randint(18*365, (max_possible_issue_date - customer_dob_datetime).days))

    expiry_date = issue_date + timedelta(days=random.randint(3650, 365*20))

    return issue_date, expiry_date

# Generate KYC Data
document_types = ['Passport', 'Driver License', 'Citizenship Certificate']
kyc_statuses = ['Verified', 'Pending', 'Rejected']
kyc_status_weights = [0.7, 0.2, 0.1]

kyc_data = []
for i, customer in customer_df.iterrows():
    customer_id = customer['CustomerID']
    customer_dob = customer['DateOfBirth']
    customer_created_date = customer['CreatedDate']

    issue_date, expiry_date = generate_valid_issue_expiry_dates(customer_dob, customer_created_date)

    if expiry_date < datetime.utcnow():
        status = 'Rejected'
    else:
        status = random.choices(kyc_statuses, weights=kyc_status_weights, k=1)[0]

    latest_start_date = max(issue_date,  customer_created_date)  # Modified date must be after the later of issue_date and created_date
    range_days = (expiry_date - latest_start_date).days  # Calculate days between the latest_start_date and expiry_date

    if range_days > 0:
    # Generate a random number of days between 0 and range_days
      random_days = random.randint(1, range_days)  # Ensure at least 1 day after latest_start_date
      modified_date = latest_start_date + timedelta(days=random_days)
    else:
    # Handle the case where the range is zero or negative, i.e., no valid date range
      modified_date = latest_start_date  # or handle as needed


    kyc_data.append({
        'KYCID': len(kyc_data) + 1,
        'CustomerID': customer_id,
        'DocumentType': random.choice(document_types),
        'DocumentNumber': fake.unique.ssn(),
        'IssueDate': issue_date,
        'ExpiryDate': expiry_date,
        'Status': status,
        'CreatedDate': customer_created_date,
        'ModifiedDate': modified_date
    })
for _ in range(num_kyc - num_customers):
    customer_id = customer['CustomerID']
    customer_dob = customer['DateOfBirth']
    customer_created_date = customer['CreatedDate']

    issue_date, expiry_date = generate_valid_issue_expiry_dates(customer_dob, customer_created_date)

    if expiry_date < datetime.utcnow():
        status = 'Rejected'
    else:
        status = random.choices(kyc_statuses, weights=kyc_status_weights, k=1)[0]

    latest_start_date = max(issue_date,  customer_created_date)  # Modified date must be after the later of issue_date and created_date
    range_days = (expiry_date - latest_start_date).days  # Calculate days between the latest_start_date and expiry_date

    if range_days > 0:
    # Generate a random number of days between 0 and range_days
      random_days = random.randint(1, range_days)  # Ensure at least 1 day after latest_start_date
      modified_date = latest_start_date + timedelta(days=random_days)
    else:
    # Handle the case where the range is zero or negative, i.e., no valid date range
      modified_date = latest_start_date  # or handle as needed


    kyc_data.append({
        'KYCID': len(kyc_data) + 1,
        'CustomerID': customer_id,
        'DocumentType': random.choice(document_types),
        'DocumentNumber': fake.unique.ssn(),
        'IssueDate': issue_date,
        'ExpiryDate': expiry_date,
        'Status': status,
        'CreatedDate': customer_created_date,
        'ModifiedDate': modified_date
    })

# Create KYC DataFrame
kyc_df = pd.DataFrame(kyc_data)

# Update account status based on KYC expiry
expired_kyc_customers = kyc_df[kyc_df['ExpiryDate'] < datetime.utcnow()]['CustomerID'].unique()
account_df.loc[account_df['CustomerID'].isin(expired_kyc_customers) & (account_df['AccountStatus'] != 'Closed'), 'AccountStatus'] = 'Inactive'

def LoanStatusFunction(customer_id,loan_amount,interest_rate):
  customer_accounts =account_df[account_df["CustomerID"] == customer_id]
  if all(customer_accounts["AccountStatus"] == 'Inactive'):
        return 'Rejected'
  active_accounts = customer_accounts[customer_accounts["AccountStatus"] == 'Active']
  if active_accounts.empty:
        return 'Rejected'
  active_account_ids = active_accounts["AccountID"]
  total_balance = balance_df[balance_df['AccountID'].isin(active_account_ids)]['Balance'].sum()
  #print(total_balance)
  first_3_months_interest = (loan_amount * (interest_rate / 100)) * (3 / 12)
  #print(first_3_months_interest)
  if total_balance >= first_3_months_interest:
        return 'Approved'
  else:
        return 'Rejected'

loan_types = ['Personal', 'Mortgage', 'Auto', 'Student']
num_loans = 100
loan_data = []
loan_types = {
    'Personal': {'rate': (11.0, 15.0), 'amount': (10000, 20000)},
    'Mortgage': {'rate': (6.0, 8.0), 'amount': (50000, 500000)},
    'Auto': {'rate': (6.0, 14.0), 'amount': (10000, 40000)},
    'Student': {'rate': (6.0, 9.0), 'amount': (20000, 300000)}
}
for i in range(num_loans):
    loan_id = i + 1
    customer_id = random.choice(customer_df['CustomerID'])
    loan_type = random.choice(list(loan_types.keys()))
    amount_range = loan_types[loan_type]['amount']
    loan_amount = round(random.uniform(*amount_range), 2)
    interest_rate_range = loan_types[loan_type]['rate']
    interest_rate = round(random.uniform(*interest_rate_range), 2)
    status = LoanStatusFunction(customer_id,loan_amount,interest_rate)

    loan_data.append({
        'LoanID': loan_id,
        'CustomerID': customer_id,
        'Type': loan_type,
        'Amount': loan_amount,
        'InterestRate': interest_rate,
        'LoanStatus':status
    })

# Create the loans DataFrame
loans_df = pd.DataFrame(loan_data)

print("Customer data:")
print(customer_df.head())

print("Account data:")
print(account_df.head())


print("Balance data:")
print(balance_df.head())

print("KYC data:")
print(kyc_df.head())

print("Loan data:")
print(loans_df.head())


# Export the dataframes to CSV files
customer_df.to_csv('/home/gret/pyhton//Data/customer_data.csv', index=False)
account_df.to_csv('/home/gret/pyhton//Data/account_data.csv', index=False)
balance_df.to_csv('/home/gret/pyhton/Data/balance_data.csv', index=False)
kyc_df.to_csv('/home/gret/pyhton//Data/kyc_data.csv', index=False)
loans_df.to_csv('/home/gret/pyhton//Data/loans_data.csv', index=False)

# Confirm the files have been saved
print("CSV files have been saved successfully.")