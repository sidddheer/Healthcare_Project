import pandas as pd
import random
from faker import Faker
from datetime import datetime, timedelta

fake = Faker()
Faker.seed(42)
random.seed(42)

# Configuration
NUM_PROVIDERS = 20
NUM_ENCOUNTERS = 2500 # Generating 2500 encounters to show significant volume
START_DATE = datetime(2023, 1, 1)
END_DATE = datetime(2023, 6, 30)

departments = ['Orthopedics', 'Emergency', 'Cardiology', 'Internal Medicine']
payers = ['Medicare', 'Blue Cross', 'UHC', 'Aetna', 'Medicaid']
carc_codes = ['CO-16', 'CO-22', 'CO-27', 'CO-50', 'CO-97']

# 1. Generate Providers
providers = []
for _ in range(NUM_PROVIDERS):
    providers.append({
        'Provider_NPI': str(fake.unique.random_number(digits=10, fix_len=True)),
        'Provider_Name': f"Dr. {fake.last_name()}",
        'Department': random.choice(departments)
    })
df_providers = pd.DataFrame(providers)

# 2. Generate Encounters & 3. Generate Claims
encounters = []
claims = []

for i in range(1, NUM_ENCOUNTERS + 1):
    encounter_id = f"ENC{i:05d}"
    patient_mrn = f"MRN{fake.random_number(digits=6, fix_len=True)}"
    admit_date = fake.date_between(start_date=START_DATE, end_date=END_DATE)
    provider = random.choice(providers)
    
    encounters.append({
        'Encounter_ID': encounter_id,
        'Patient_MRN': patient_mrn,
        'Admit_Date': admit_date,
        'Provider_NPI': provider['Provider_NPI']
    })
    
    # Clinical Logic: Assign ICD-10 and CPT based on Department
    dept = provider['Department']
    if dept == 'Orthopedics':
        icd10 = random.choice(['M16.9', 'M54.5', 'S82.009A']) # Osteoarthritis, Low back pain, Knee fracture
        cpt = random.choice(['27130', '29881', '99214']) # Hip replacement, Knee arthroscopy, Office visit
        billed = round(random.uniform(500, 15000), 2)
    elif dept == 'Emergency':
        icd10 = random.choice(['S06.0X0A', 'R07.9', 'J18.9']) # Concussion, Chest pain, Pneumonia
        cpt = random.choice(['99284', '99285', '70450']) # ER visits, CT Head
        billed = round(random.uniform(800, 5000), 2)
    elif dept == 'Cardiology':
        icd10 = random.choice(['I10', 'I48.91', 'I25.10']) # Hypertension, A-Fib, CAD
        cpt = random.choice(['93000', '93306', '92920']) # ECG, Echo, Angioplasty
        billed = round(random.uniform(150, 8000), 2)
    else: # Internal Medicine
        icd10 = random.choice(['E11.9', 'J01.90', 'E78.5']) # Type 2 Diabetes, Sinusitis, Hyperlipidemia
        cpt = random.choice(['99213', '99214', '36415']) # Standard office visits, Blood draw
        billed = round(random.uniform(100, 400), 2)

    claim_id = f"CLM{i:05d}"
    payer = random.choice(payers)
    
    claims.append({
        'Claim_ID': claim_id,
        'Encounter_ID': encounter_id,
        'Payer_Name': payer,
        'ICD10_Primary': icd10,
        'CPT_Code': cpt,
        'Total_Billed_Amount': billed
    })

df_encounters = pd.DataFrame(encounters)
df_claims = pd.DataFrame(claims)

# 4. Generate Payer Responses (The 835 Remit Data)
remits = []
for index, claim in df_claims.iterrows():
    # Find associated encounter and provider to apply business logic
    enc = df_encounters[df_encounters['Encounter_ID'] == claim['Encounter_ID']].iloc[0]
    prov = df_providers[df_providers['Provider_NPI'] == enc['Provider_NPI']].iloc[0]
    
    adjudication_date = enc['Admit_Date'] + timedelta(days=random.randint(14, 45))
    
    # --- RCM BUSINESS LOGIC INJECTION ---
    # 1. Orthopedics + Medicare = High chance of Medical Necessity Denial (CO-50)
    if prov['Department'] == 'Orthopedics' and claim['Payer_Name'] == 'Medicare' and random.random() < 0.40:
        status = 'Denied'
        carc = 'CO-50'
        paid = 0.00
    # 2. Emergency Dept = High chance of Coordination of Benefits Denial (CO-22)
    elif prov['Department'] == 'Emergency' and random.random() < 0.15:
        status = 'Denied'
        carc = 'CO-22'
        paid = 0.00
    # 3. Standard processing (85% Clean Claim Rate otherwise)
    else:
        if random.random() < 0.85:
            status = 'Paid'
            carc = None
            # Contractual adjustment: Payers usually pay 30-60% of the billed charge
            paid = round(claim['Total_Billed_Amount'] * random.uniform(0.3, 0.6), 2)
        else:
            status = 'Denied'
            carc = random.choice(['CO-16', 'CO-27', 'CO-97'])
            paid = 0.00

    remits.append({
        'Response_ID': f"RMT{index+1:05d}",
        'Claim_ID': claim['Claim_ID'],
        'Adjudication_Date': adjudication_date,
        'Status': status,
        'CARC_Code': carc,
        'Total_Paid_Amount': paid
    })

df_remits = pd.DataFrame(remits)

# Export to CSV
df_providers.to_csv('Providers.csv', index=False)
df_encounters.to_csv('Encounters.csv', index=False)
df_claims.to_csv('Claims.csv', index=False)
df_remits.to_csv('Remittances.csv', index=False)

print("Enterprise RCM Dataset successfully generated and exported to CSV.")
print(f"Total Claims Analyzed: {len(df_claims)}")
print(f"Total Denials Flagged: {len(df_remits[df_remits['Status'] == 'Denied'])}")